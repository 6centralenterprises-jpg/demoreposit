"""The web app. Run with:  python3 -m gbp_intel  (then open http://localhost:8000)."""
import base64
import csv
import io
import secrets
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import competitors as comp
from . import config, db, gaps
from .keywords import KeywordClient, KeywordError, sparkline
from .places import PlacesClient, PlacesError
from .urls import normalize_website, parse_maps_url, parse_upload, search_text_for

HERE = Path(__file__).resolve().parent


def create_app(conn=None, places=None, keywords=None):
    app = FastAPI(title="6 Central Local Intel", docs_url=None, redoc_url=None)
    app.state.conn = conn or db.connect()
    app.state.places = places or PlacesClient()
    app.state.keywords = keywords or KeywordClient()
    templates = Jinja2Templates(directory=HERE / "templates")
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    @app.middleware("http")
    async def password_gate(request, call_next):
        if not config.APP_PASSWORD or request.url.path.startswith("/static"):
            return await call_next(request)
        try:
            scheme, encoded = request.headers.get("authorization", "").split(" ", 1)
            password = base64.b64decode(encoded).decode().split(":", 1)[1]
            ok = scheme.lower() == "basic" and secrets.compare_digest(password, config.APP_PASSWORD)
        except Exception:
            ok = False
        if not ok:
            return Response("Password required", 401, {"WWW-Authenticate": 'Basic realm="Local Intel"'})
        return await call_next(request)

    def page(request, name, **context):
        context.update(projects=config.PROJECTS, places_ready=app.state.places.configured,
                       keywords_ready=app.state.keywords.configured)
        return templates.TemplateResponse(request, name, context)

    def back(url, **params):
        query = urlencode({k: v for k, v in params.items() if v})
        return RedirectResponse(f"{url}?{query}" if query else url, status_code=303)

    @app.get("/")
    def home():
        return RedirectResponse("/assets")

    @app.get("/assets", response_class=HTMLResponse)
    def assets(request: Request, project: str = "", msg: str = ""):
        rows = db.list_assets(app.state.conn, project or None)
        return page(request, "assets.html", assets=rows, project=project, msg=msg)

    @app.post("/assets")
    def add_asset(name: str = Form(""), project: str = Form("Other"), city: str = Form(""),
                  website: str = Form(""), maps_url: str = Form(""), notes: str = Form("")):
        website = normalize_website(website)
        if not (name.strip() or website or maps_url.strip()):
            return back("/assets", msg="Add at least a name, a website or a Maps link.")
        dupe = db.find_duplicate(app.state.conn, website, maps_url.strip())
        if dupe:
            return back(f"/assets/{dupe['id']}", msg="That asset is already saved.")
        parsed = parse_maps_url(maps_url)
        asset_id = db.add_asset(app.state.conn, name=name or parsed["name"] or "", project=project, city=city,
                                website=website, maps_url=maps_url, notes=notes, place_id=parsed["place_id"])
        return back(f"/assets/{asset_id}")

    @app.post("/assets/upload")
    async def upload(text: str = Form(""), file: UploadFile | None = File(None),
                     project: str = Form("Other"), city: str = Form("")):
        if file is not None and file.filename:
            text = (await file.read()).decode("utf-8-sig", errors="replace")
        added = skipped = 0
        for row in parse_upload(text, project, city):
            if db.find_duplicate(app.state.conn, row["website"], row["maps_url"]):
                skipped += 1
                continue
            db.add_asset(app.state.conn, **row, place_id=parse_maps_url(row["maps_url"])["place_id"])
            added += 1
        msg = f"Added {added} asset{'s' * (added != 1)}."
        if skipped:
            msg += f" Skipped {skipped} already saved."
        return back("/assets", msg=msg)

    @app.get("/assets/{asset_id}", response_class=HTMLResponse)
    def asset_page(request: Request, asset_id: int, msg: str = ""):
        conn, places = app.state.conn, app.state.places
        asset = db.get_asset(conn, asset_id)
        if not asset:
            return back("/assets", msg="That asset no longer exists.")
        place, candidates, error = None, [], ""
        query = search_text_for(asset)
        if asset["place_id"]:
            place = db.cached_place(conn, asset["place_id"])
        elif places.configured and query:
            try:
                candidates = places.search(query)
            except PlacesError as e:
                error = str(e)
        searches = [s for s in db.recent_searches(conn, 50) if s["city"].lower() == asset["city"].lower()]
        return page(request, "asset.html", asset=asset, place=place, candidates=candidates,
                    query=query, error=error, msg=msg, searches=searches)

    @app.post("/assets/{asset_id}/match")
    def match(asset_id: int, place_id: str = Form(...)):
        db.set_place_id(app.state.conn, asset_id, place_id)
        return refresh(asset_id)

    @app.post("/assets/{asset_id}/refresh")
    def refresh(asset_id: int):
        asset = db.get_asset(app.state.conn, asset_id)
        if not asset or not asset["place_id"]:
            return back(f"/assets/{asset_id}")
        try:
            db.cache_place(app.state.conn, app.state.places.details(asset["place_id"]))
        except PlacesError as e:
            return back(f"/assets/{asset_id}", msg=str(e))
        return back(f"/assets/{asset_id}", msg="Profile data refreshed from Google.")

    @app.post("/assets/{asset_id}/unmatch")
    def unmatch(asset_id: int):
        db.set_place_id(app.state.conn, asset_id, None)
        return back(f"/assets/{asset_id}")

    @app.get("/competitors", response_class=HTMLResponse)
    def competitors_home(request: Request, msg: str = ""):
        return page(request, "competitors.html", searches=db.recent_searches(app.state.conn), msg=msg)

    @app.post("/competitors")
    def run_search(service: str = Form(""), city: str = Form("")):
        if not (service.strip() and city.strip()):
            return back("/competitors", msg="Enter both a service and a city.")
        try:
            found = app.state.places.competitors(service, city)
        except PlacesError as e:
            return back("/competitors", msg=str(e))
        search_id = db.save_search(app.state.conn, service, city, found)
        return back(f"/competitors/{search_id}")

    def search_table(search_id):
        return comp.rows(db.search_results(app.state.conn, search_id), db.our_place_ids(app.state.conn))

    @app.get("/competitors/{search_id}", response_class=HTMLResponse)
    def search_page(request: Request, search_id: int):
        search = db.get_search(app.state.conn, search_id)
        if not search:
            return back("/competitors", msg="That search no longer exists.")
        table = search_table(search_id)
        return page(request, "competitor_results.html", search=search, table=table,
                    summary=comp.summary(table), expired=any(r["expired"] for r in table))

    @app.get("/competitors/{search_id}/csv")
    def search_csv(search_id: int):
        search = db.get_search(app.state.conn, search_id)
        if not search:
            return Response("Not found", 404)
        name = f"competitors-{search['service']}-{search['city']}".lower()
        name = "".join(c if c.isalnum() else "-" for c in name)
        return Response(comp.to_csv(search_table(search_id)), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{name}.csv"'})

    @app.post("/assets/{asset_id}/gaps")
    def run_gaps(asset_id: int, search_id: int = Form(0), service: str = Form("")):
        """Compare against an existing search, or run a new one for this asset's city."""
        asset = db.get_asset(app.state.conn, asset_id)
        if not asset or not asset["place_id"]:
            return back(f"/assets/{asset_id}", msg="Match this asset to its Google profile first.")
        if not search_id:
            if not (service.strip() and asset["city"]):
                return back(f"/assets/{asset_id}", msg="Gap analysis needs a service and the asset's city.")
            try:
                found = app.state.places.competitors(service, asset["city"])
            except PlacesError as e:
                return back(f"/assets/{asset_id}", msg=str(e))
            search_id = db.save_search(app.state.conn, service, asset["city"], found)
        return back(f"/assets/{asset_id}/gaps/{search_id}")

    @app.get("/assets/{asset_id}/gaps/{search_id}", response_class=HTMLResponse)
    def gaps_page(request: Request, asset_id: int, search_id: int):
        conn = app.state.conn
        asset, search = db.get_asset(conn, asset_id), db.get_search(conn, search_id)
        if not asset or not search or not asset["place_id"]:
            return back(f"/assets/{asset_id}")
        ours = db.cached_place(conn, asset["place_id"])
        if ours is None:
            try:
                ours = app.state.places.details(asset["place_id"])
                db.cache_place(conn, ours)
            except PlacesError as e:
                return back(f"/assets/{asset_id}", msg=str(e))
        results = db.search_results(conn, search_id)
        rivals = [r["place"] for r in results if r["place"] and r["place_id"] != asset["place_id"]]
        our_rank = next((r["rank"] for r in results if r["place_id"] == asset["place_id"]), None)
        return page(request, "gaps.html", asset=asset, search=search, ours=ours, our_rank=our_rank,
                    checks=gaps.analyze(ours, rivals), rivals=rivals[:3], later=gaps.LATER,
                    expired=len(rivals) < sum(1 for r in results if r["place_id"] != asset["place_id"]))

    @app.get("/keywords", response_class=HTMLResponse)
    def keywords_home(request: Request, msg: str = ""):
        return page(request, "keywords.html", searches=db.recent_keyword_searches(app.state.conn), msg=msg)

    @app.post("/keywords")
    def run_keywords(seeds: str = Form(""), location: str = Form("United States")):
        terms = [t.strip() for t in seeds.replace("\n", ",").split(",") if t.strip()]
        if not terms:
            return back("/keywords", msg="Enter at least one keyword.")
        location = location.strip() or "United States"
        try:
            results = app.state.keywords.ideas(terms, location)
        except KeywordError as e:
            return back("/keywords", msg=str(e))
        return back(f"/keywords/{db.save_keyword_search(app.state.conn, ', '.join(terms), location, results)}")

    @app.get("/keywords/{search_id}", response_class=HTMLResponse)
    def keyword_page(request: Request, search_id: int, sort: str = "volume", min_volume: int = 0):
        search = db.get_keyword_search(app.state.conn, search_id)
        if not search:
            return back("/keywords", msg="That search no longer exists.")
        if sort not in ("volume", "trend", "cpc", "competition_index", "keyword"):
            sort = "volume"
        rows = [r for r in search["results"] if (r["volume"] or 0) >= min_volume]
        reverse = sort != "keyword"
        rows.sort(key=lambda r: (r.get(sort) is not None, r.get(sort) or 0) if sort != "keyword" else r["keyword"],
                  reverse=reverse)
        for r in rows:
            r["spark"] = sparkline(r["monthly"])
        return page(request, "keyword_results.html", search=search, rows=rows, sort=sort, min_volume=min_volume)

    @app.get("/keywords/{search_id}/csv")
    def keyword_csv(search_id: int):
        search = db.get_keyword_search(app.state.conn, search_id)
        if not search:
            return Response("Not found", 404)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["keyword", "monthly_volume", "trend_pct", "cpc", "competition", "competition_index",
                         "bid_low", "bid_high"])
        for r in search["results"]:
            writer.writerow([r["keyword"], r["volume"], r["trend"], r["cpc"], r["competition"],
                             r["competition_index"], r["bid_low"], r["bid_high"]])
        return Response(buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="keywords-{search_id}.csv"'})

    @app.post("/assets/{asset_id}/delete")
    def delete(asset_id: int):
        db.delete_asset(app.state.conn, asset_id)
        return back("/assets", msg="Asset deleted.")

    return app
