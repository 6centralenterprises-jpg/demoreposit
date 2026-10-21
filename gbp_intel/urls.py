"""Cleaning up the URLs and lists people paste in."""
import csv
import io
import re
from urllib.parse import parse_qs, unquote_plus, urlparse

from . import config

MAPS_HOSTS = ("google.com/maps", "maps.google.", "maps.app.goo.gl", "goo.gl/maps", "g.page")


def normalize_website(url):
    """'Example.com/' -> 'https://example.com'. Empty stays empty."""
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    parts = urlparse(url)
    path = parts.path.rstrip("/")
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{path}"


def is_maps_url(url):
    return any(h in (url or "").lower() for h in MAPS_HOSTS)


def parse_maps_url(url):
    """What a Google Maps link tells us without fetching it: a Place ID, a CID and/or a business name."""
    out = {"place_id": None, "cid": None, "name": None}
    if not url:
        return out
    parts = urlparse(url.strip())
    query = parse_qs(parts.query)
    if query.get("query_place_id"):
        out["place_id"] = query["query_place_id"][0]
    for q in query.get("q", []):
        if q.startswith("place_id:"):
            out["place_id"] = q.split(":", 1)[1]
    if query.get("cid"):
        out["cid"] = query["cid"][0]
    m = re.search(r"/maps/place/([^/@]+)", parts.path)
    if m:
        out["name"] = unquote_plus(m.group(1)).strip()
    return out


def search_text_for(asset):
    """The text query used to find an asset on Google: name plus city."""
    name = asset["name"] or parse_maps_url(asset["maps_url"])["name"] or ""
    return " ".join(p for p in (name, asset["city"]) if p).strip()


HEADER_ALIASES = {
    "name": ["name", "business", "business name", "company"],
    "project": ["project", "service", "niche"],
    "city": ["city", "market", "location"],
    "website": ["website", "url", "site", "web"],
    "maps_url": ["maps_url", "maps", "google maps", "gbp", "gmb", "maps link", "profile"],
    "notes": ["notes", "note"],
}


def parse_upload(text, default_project="Other", default_city=""):
    """Rows of assets from pasted lines or a CSV with headers.

    Without a header row, each line is one URL (website or Maps link)."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return []
    first = [c.strip().lower() for c in next(csv.reader([lines[0]]))]
    columns = {}
    for field, aliases in HEADER_ALIASES.items():
        for i, cell in enumerate(first):
            if cell in aliases and field not in columns:
                columns[field] = i
    rows = []
    if columns:
        for record in csv.reader(io.StringIO("\n".join(lines[1:]))):
            row = {f: (record[i].strip() if i < len(record) else "") for f, i in columns.items()}
            rows.append(row)
    else:
        for line in lines:
            url = line.strip().split(",")[0].strip()
            rows.append({("maps_url" if is_maps_url(url) else "website"): url})
    cleaned = []
    for row in rows:
        website, maps_url = row.get("website", ""), row.get("maps_url", "")
        if is_maps_url(website) and not maps_url:
            website, maps_url = "", website
        if not (row.get("name") or website or maps_url):
            continue
        project = row.get("project") or default_project
        match = next((p for p in config.PROJECTS if p.lower() == project.strip().lower()), None)
        cleaned.append({
            "name": row.get("name") or parse_maps_url(maps_url)["name"] or "",
            "project": match or "Other",
            "city": row.get("city") or default_city,
            "website": normalize_website(website),
            "maps_url": maps_url.strip(),
            "notes": row.get("notes", ""),
        })
    return cleaned
