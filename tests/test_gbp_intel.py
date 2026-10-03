import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from gbp_intel import db
from gbp_intel.app import create_app
from gbp_intel.keywords import KeywordClient, trend
from gbp_intel.places import PlacesClient
from gbp_intel.urls import normalize_website, parse_maps_url, parse_upload

PLACE = {"id": "ChIJtest123", "displayName": {"text": "Sparkle Decks"}, "formattedAddress": "1 Main St, Chicago, IL",
         "primaryType": "deck_contractor", "primaryTypeDisplayName": {"text": "Deck contractor"},
         "rating": 4.8, "userRatingCount": 52, "regularOpeningHours": {"weekdayDescriptions": ["Monday: 8 AM–5 PM"]}}


RIVAL = {"id": "ChIJrival", "displayName": {"text": "Rival Decks"}, "primaryTypeDisplayName": {"text": "Deck contractor"},
         "primaryType": "deck_contractor", "types": ["deck_contractor", "carpenter"],
         "rating": 4.9, "userRatingCount": 210, "websiteUri": "https://www.rivaldecks.test/", "businessStatus": "OPERATIONAL"}
NO_SITE = {"id": "ChIJnosite", "displayName": {"text": "Bob's Decks"}, "primaryType": "contractor", "types": ["contractor", "carpenter"],
           "rating": 4.1, "userRatingCount": 8, "businessStatus": "CLOSED_TEMPORARILY"}


def fake_google(request):
    assert request.headers["X-Goog-Api-Key"] == "test-key"
    if request.url.path.endswith(":searchText") and json.loads(request.content)["textQuery"].endswith(" in Chicago, IL"):
        assert json.loads(request.content) == {"textQuery": "Deck repair in Chicago, IL", "pageSize": 20}
        assert "places.websiteUri" in request.headers["X-Goog-FieldMask"]
        return httpx.Response(200, json={"places": [RIVAL, PLACE, NO_SITE]})
    if request.url.path.endswith(":searchText"):
        assert json.loads(request.content)["textQuery"] == "Sparkle Decks Chicago, IL"
        return httpx.Response(200, json={"places": [PLACE]})
    if request.url.path == "/v1/places/ChIJtest123":
        assert "rating" in request.headers["X-Goog-FieldMask"]
        return httpx.Response(200, json=PLACE)
    return httpx.Response(404, json={"error": {"message": "Not found"}})


def months(*volumes):
    return [{"year": 2026, "month": i + 1, "search_volume": v} for i, v in enumerate(volumes)]


KEYWORD_RESULTS = [
    {"keyword": "deck repair", "search_volume": 9900, "cpc": 8.12, "competition": "HIGH", "competition_index": 88,
     "low_top_of_page_bid": 3.1, "high_top_of_page_bid": 12.4,
     "monthly_searches": list(reversed(months(100, 100, 100, 150, 150, 150)))},  # API sends newest first
    {"keyword": "deck staining near me", "search_volume": 2400, "cpc": None, "competition": "LOW",
     "competition_index": 12, "monthly_searches": months(50, 50, 50, 25, 25, 25)},
]


def fake_dataforseo(request):
    assert request.headers["authorization"].startswith("Basic ")
    assert request.url.path == "/v3/keywords_data/google_ads/keywords_for_keywords/live"
    task = json.loads(request.content)[0]
    if task["keywords"] == ["bad"]:
        return httpx.Response(200, json={"tasks": [{"status_code": 40501, "status_message": "Invalid location"}]})
    assert task == {"keywords": ["deck repair", "deck staining"], "location_name": "Illinois,United States",
                    "language_code": "en"}
    return httpx.Response(200, json={"tasks": [{"status_code": 20000, "result": KEYWORD_RESULTS}]})


@pytest.fixture
def client():
    conn = db.connect(":memory:")
    places = PlacesClient(api_key="test-key", transport=httpx.MockTransport(fake_google))
    keywords = KeywordClient("login", "pw", transport=httpx.MockTransport(fake_dataforseo))
    return TestClient(create_app(conn, places, keywords))


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


def test_competitor_search(client):
    client.post("/assets", data={"name": "Sparkle Decks", "project": "Deck repair", "city": "Chicago, IL"})
    client.post("/assets/1/match", data={"place_id": "ChIJtest123"})

    resp = client.post("/competitors", data={"service": "Deck repair", "city": "Chicago, IL"})
    assert resp.url.path == "/competitors/1"
    html = resp.text
    assert html.index("Rival Decks") < html.index("Sparkle Decks") < html.index("Bob&#39;s Decks")
    assert "rivaldecks.test" in html and "closed temporarily" in html
    assert "#2" in html  # where we show up
    assert ">52<" in html  # median reviews of the top 3 (210, 52, 8)

    csv_text = client.get("/competitors/1/csv").text
    lines = csv_text.splitlines()
    assert lines[0].startswith("rank,name,ours,primary_type,rating,reviews,website")
    assert lines[2].startswith("2,Sparkle Decks,yes,Deck contractor,4.8,52")
    assert "Deck repair" in client.get("/competitors").text


def test_competitor_details_expire_but_ranking_stays(client):
    client.post("/competitors", data={"service": "Deck repair", "city": "Chicago, IL"})
    conn = client.app.state.conn
    conn.execute("UPDATE places_cache SET fetched_at = '2000-01-01T00:00:00+00:00'")
    db.purge_expired_places(conn)
    html = client.get("/competitors/1").text
    assert html.count("Details cleared after 30 days") == 3
    assert "Run the search again" in html


def test_competitor_search_needs_service_and_city(client):
    assert "Enter both a service and a city." in client.post("/competitors", data={"service": "Decks"}).text


def test_gap_analysis_checks():
    from gbp_intel.gaps import analyze
    ours = {"primaryType": "deck_contractor", "types": ["deck_contractor"], "rating": 4.8, "userRatingCount": 52,
            "regularOpeningHours": ["Monday: 8 AM–5 PM"], "businessStatus": "OPERATIONAL"}
    checks = {c["check"]: c for c in analyze(ours, [RIVAL, NO_SITE])}
    assert checks["Primary category"]["status"] == "ok"
    assert checks["Secondary categories"]["status"] == "gap" and "Carpenter" in checks["Secondary categories"]["benchmark"]
    assert checks["Review count"]["status"] == "gap" and "57 more reviews" in checks["Review count"]["step"]
    assert checks["Rating"]["status"] == "ok"
    assert checks["Website on profile"]["status"] == "gap" and checks["Website on profile"]["benchmark"] == "1 of top 2 have it"
    assert checks["Hours on profile"]["status"] == "ok"
    assert list(checks)[0] != "Primary category"  # gaps listed first


def test_gap_analysis_page(client):
    client.post("/assets", data={"name": "Sparkle Decks", "project": "Deck repair", "city": "Chicago, IL"})
    client.post("/assets/1/match", data={"place_id": "ChIJtest123"})
    resp = client.post("/assets/1/gaps", data={"service": "Deck repair"})
    assert resp.url.path == "/assets/1/gaps/1"
    assert "we rank #2" in resp.text
    assert "4 gaps" in resp.text  # secondary categories, reviews, website, phone
    assert "Rival Decks" in resp.text
    assert "Deck repair in Chicago, IL" in client.get("/assets/1").text  # saved search offered next time


def test_keyword_trend():
    assert trend(months(100, 100, 100, 150, 150, 150)) == 50
    assert trend(months(1, 2, 3)) is None
    assert trend(months(0, 0, 0, 5, 5, 5)) is None


def test_keyword_research(client):
    resp = client.post("/keywords", data={"seeds": "deck repair,\n deck staining", "location": "Illinois,United States"})
    assert resp.url.path == "/keywords/1"
    html = resp.text
    assert html.index("deck repair") < html.index("deck staining near me")  # by volume
    assert "9,900" in html and "$8.12" in html and "+50%" in html and "-50%" in html and "High" in html
    assert "<polyline" in html

    html = client.get("/keywords/1?sort=trend&min_volume=3000").text
    assert "deck staining near me" not in html

    lines = client.get("/keywords/1/csv").text.splitlines()
    assert lines[1] == "deck repair,9900,50,8.12,High,88,3.1,12.4"
    assert "deck repair, deck staining" in client.get("/keywords").text


def test_keyword_errors(client):
    assert "Invalid location" in client.post("/keywords", data={"seeds": "bad"}).text
    assert "Enter at least one keyword." in client.post("/keywords", data={"seeds": " , "}).text
