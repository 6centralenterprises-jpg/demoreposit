"""SQLite storage. Our own assets live here; Google Places content is kept
in places_cache and deleted after PLACES_CACHE_DAYS."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    project TEXT NOT NULL,
    city TEXT NOT NULL DEFAULT '',
    website TEXT NOT NULL DEFAULT '',
    maps_url TEXT NOT NULL DEFAULT '',
    place_id TEXT,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY,
    service TEXT NOT NULL,
    city TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS search_results (
    search_id INTEGER NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    place_id TEXT NOT NULL,
    PRIMARY KEY (search_id, rank)
);
CREATE TABLE IF NOT EXISTS keyword_searches (
    id INTEGER PRIMARY KEY,
    seeds TEXT NOT NULL,
    location TEXT NOT NULL,
    results TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS places_cache (
    place_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
"""

ASSET_FIELDS = ["name", "project", "city", "website", "maps_url", "notes"]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path=None):
    path = path or config.DB_PATH
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    purge_expired_places(conn)
    return conn


def add_asset(conn, **fields):
    values = {f: (fields.get(f) or "").strip() for f in ASSET_FIELDS}
    cur = conn.execute(
        f"INSERT INTO assets ({', '.join(ASSET_FIELDS)}, place_id, created_at) VALUES "
        f"({', '.join('?' * len(ASSET_FIELDS))}, ?, ?)",
        [*values.values(), fields.get("place_id") or None, now()])
    conn.commit()
    return cur.lastrowid


def list_assets(conn, project=None):
    sql, args = "SELECT * FROM assets", []
    if project:
        sql, args = sql + " WHERE project = ?", [project]
    return conn.execute(sql + " ORDER BY project, name", args).fetchall()


def get_asset(conn, asset_id):
    return conn.execute("SELECT * FROM assets WHERE id = ?", [asset_id]).fetchone()


def find_duplicate(conn, website, maps_url):
    """An existing asset with the same website or Maps link, if any."""
    for column, value in (("website", website), ("maps_url", maps_url)):
        if value:
            row = conn.execute(f"SELECT * FROM assets WHERE {column} = ?", [value]).fetchone()
            if row:
                return row
    return None


def set_place_id(conn, asset_id, place_id):
    conn.execute("UPDATE assets SET place_id = ? WHERE id = ?", [place_id, asset_id])
    conn.commit()


def delete_asset(conn, asset_id):
    conn.execute("DELETE FROM assets WHERE id = ?", [asset_id])
    conn.commit()


def cache_place(conn, place):
    conn.execute("INSERT OR REPLACE INTO places_cache (place_id, data, fetched_at) VALUES (?, ?, ?)",
                 [place["id"], json.dumps(place), now()])
    conn.commit()


def cached_place(conn, place_id):
    row = conn.execute("SELECT data, fetched_at FROM places_cache WHERE place_id = ?", [place_id]).fetchone()
    if not row:
        return None
    return {**json.loads(row["data"]), "fetched_at": row["fetched_at"]}


def save_search(conn, service, city, places):
    """Keeps the ranked Place IDs for good; the place data goes to places_cache."""
    cur = conn.execute("INSERT INTO searches (service, city, created_at) VALUES (?, ?, ?)",
                       [service.strip(), city.strip(), now()])
    for rank, place in enumerate(places, 1):
        conn.execute("INSERT INTO search_results (search_id, rank, place_id) VALUES (?, ?, ?)",
                     [cur.lastrowid, rank, place["id"]])
        cache_place(conn, place)
    conn.commit()
    return cur.lastrowid


def get_search(conn, search_id):
    return conn.execute("SELECT * FROM searches WHERE id = ?", [search_id]).fetchone()


def recent_searches(conn, limit=20):
    return conn.execute("SELECT s.*, COUNT(r.rank) AS results FROM searches s "
                        "LEFT JOIN search_results r ON r.search_id = s.id "
                        "GROUP BY s.id ORDER BY s.id DESC LIMIT ?", [limit]).fetchall()


def search_results(conn, search_id):
    """Ranked results with their cached place data (None once Google's 30-day limit has passed)."""
    rows = conn.execute("SELECT rank, place_id FROM search_results WHERE search_id = ? ORDER BY rank",
                        [search_id]).fetchall()
    return [{"rank": r["rank"], "place_id": r["place_id"], "place": cached_place(conn, r["place_id"])}
            for r in rows]


def save_keyword_search(conn, seeds, location, results):
    cur = conn.execute("INSERT INTO keyword_searches (seeds, location, results, created_at) VALUES (?, ?, ?, ?)",
                       [seeds, location, json.dumps(results), now()])
    conn.commit()
    return cur.lastrowid


def get_keyword_search(conn, search_id):
    row = conn.execute("SELECT * FROM keyword_searches WHERE id = ?", [search_id]).fetchone()
    return {**dict(row), "results": json.loads(row["results"])} if row else None


def recent_keyword_searches(conn, limit=20):
    return conn.execute("SELECT id, seeds, location, created_at, json_array_length(results) AS results "
                        "FROM keyword_searches ORDER BY id DESC LIMIT ?", [limit]).fetchall()


def our_place_ids(conn):
    return {r["place_id"] for r in conn.execute("SELECT place_id FROM assets WHERE place_id IS NOT NULL")}


def purge_expired_places(conn):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=config.PLACES_CACHE_DAYS)).isoformat(timespec="seconds")
    conn.execute("DELETE FROM places_cache WHERE fetched_at < ?", [cutoff])
    conn.commit()
