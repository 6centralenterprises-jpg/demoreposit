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


def purge_expired_places(conn):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=config.PLACES_CACHE_DAYS)).isoformat(timespec="seconds")
    conn.execute("DELETE FROM places_cache WHERE fetched_at < ?", [cutoff])
    conn.commit()
