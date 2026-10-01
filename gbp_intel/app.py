"""The web app. Run with:  python3 -m gbp_intel  (then open http://localhost:8000)."""
import base64
import secrets
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, db
from .places import PlacesClient, PlacesError
from .urls import normalize_website, parse_maps_url, parse_upload, search_text_for

HERE = Path(__file__).resolve().parent


def create_app(conn=None, places=None):
    app = FastAPI(title="6 Central Local Intel", docs_url=None, redoc_url=None)
    app.state.conn = conn or db.connect()
    app.state.places = places or PlacesClient()
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
        context.update(projects=config.PROJECTS, places_ready=app.state.places.configured)
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
        return page(request, "asset.html", asset=asset, place=place, candidates=candidates,
                    query=query, error=error, msg=msg)

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

    @app.post("/assets/{asset_id}/delete")
    def delete(asset_id: int):
        db.delete_asset(app.state.conn, asset_id)
        return back("/assets", msg="Asset deleted.")

    return app
