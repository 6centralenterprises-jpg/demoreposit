import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from gbp_intel import db
from gbp_intel.app import create_app
from gbp_intel.places import PlacesClient
from gbp_intel.urls import normalize_website, parse_maps_url, parse_upload

PLACE = {"id": "ChIJtest123", "displayName": {"text": "Sparkle Decks"}, "formattedAddress": "1 Main St, Chicago, IL",
         "primaryType": "deck_contractor", "primaryTypeDisplayName": {"text": "Deck contractor"},
         "rating": 4.8, "userRatingCount": 52, "regularOpeningHours": {"weekdayDescriptions": ["Monday: 8 AM–5 PM"]}}


def fake_google(request):
    assert request.headers["X-Goog-Api-Key"] == "test-key"
    if request.url.path.endswith(":searchText"):
        assert json.loads(request.content)["textQuery"] == "Sparkle Decks Chicago, IL"
        return httpx.Response(200, json={"places": [PLACE]})
    if request.url.path == "/v1/places/ChIJtest123":
        assert "rating" in request.headers["X-Goog-FieldMask"]
        return httpx.Response(200, json=PLACE)
    return httpx.Response(404, json={"error": {"message": "Not found"}})


@pytest.fixture
def client():
    conn = db.connect(":memory:")
    places = PlacesClient(api_key="test-key", transport=httpx.MockTransport(fake_google))
    return TestClient(create_app(conn, places))


def test_normalize_website():
    assert normalize_website("Example.com/") == "https://example.com"
    assert normalize_website("http://Example.com/about/") == "http://example.com/about"
    assert normalize_website("  ") == ""


def test_parse_maps_url():
    parsed = parse_maps_url("https://www.google.com/maps/place/Sparkle+Decks/@41.8,-87.6,15z")
    assert parsed["name"] == "Sparkle Decks"
    assert parse_maps_url("https://www.google.com/maps/search/?api=1&query=x&query_place_id=ChIJabc")["place_id"] == "ChIJabc"
    assert parse_maps_url("https://maps.google.com/?cid=12345")["cid"] == "12345"


def test_parse_upload_plain_lines_and_csv():
    rows = parse_upload("example.com\nhttps://maps.google.com/?cid=1\n\n", "Concrete", "Chicago, IL")
    assert [r["website"] for r in rows] == ["https://example.com", ""]
    assert rows[1]["maps_url"] == "https://maps.google.com/?cid=1"
    assert all(r["project"] == "Concrete" and r["city"] == "Chicago, IL" for r in rows)

    csv_rows = parse_upload("Business Name,Service,City,URL\nSparkle Decks,deck repair,Austin TX,sparkle.test\n,,,\n")
    assert csv_rows == [{"name": "Sparkle Decks", "project": "Deck repair", "city": "Austin TX",
                         "website": "https://sparkle.test", "maps_url": "", "notes": ""}]


def test_add_match_and_refresh(client):
    resp = client.post("/assets", data={"name": "Sparkle Decks", "project": "Deck repair", "city": "Chicago, IL",
                                        "website": "sparkle.test"})
    assert resp.status_code == 200 and "This is ours" in resp.text  # redirected to the asset page with candidates

    resp = client.post("/assets/1/match", data={"place_id": "ChIJtest123"})
    assert "4.8 from 52 reviews" in resp.text
    assert "Monday: 8 AM–5 PM" in resp.text

    resp = client.post("/assets", data={"website": "https://sparkle.test/"})
    assert "already saved" in resp.text


def test_upload_skips_duplicates(client):
    client.post("/assets/upload", data={"text": "one.test\ntwo.test", "project": "Concrete"})
    resp = client.post("/assets/upload", data={"text": "two.test\nthree.test", "project": "Concrete"})
    assert "Added 1 asset. Skipped 1 already saved." in resp.text
    assert resp.text.count("Not matched") == 3


def test_places_cache_expires_after_30_days():
    conn = db.connect(":memory:")
    db.cache_place(conn, {"id": "old"})
    old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(timespec="seconds")
    conn.execute("UPDATE places_cache SET fetched_at = ?", [old])
    db.purge_expired_places(conn)
    assert db.cached_place(conn, "old") is None


def test_password_gate(monkeypatch, client):
    monkeypatch.setattr("gbp_intel.config.APP_PASSWORD", "s3cret")
    assert client.get("/assets").status_code == 401
    assert client.get("/assets", auth=("any", "s3cret")).status_code == 200
