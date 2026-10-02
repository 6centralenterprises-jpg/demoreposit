import json
from argparse import Namespace

import scout
from gbp_scout import scoring
from gbp_scout.brief import render_html


def trend(newest_first, year=2026, month=8):
    out = []
    for v in newest_first:
        out.append({"year": year, "month": month, "search_volume": v})
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return out


def test_yoy_compares_same_months_last_year():
    # Jun-Aug 2026 = 90,500 x3; Jun-Aug 2025 = 110,000 + 90,500 + 90,500 -> -6.7%
    data = trend([90500, 90500, 90500] + [1] * 9 + [90500, 90500, 110000] + [1] * 9)
    result = scoring.yoy(data)
    assert result["latest_month"] == "2026-08"
    assert result["yoy"] == round(271500 / 291000 - 1, 3)
    assert scoring.label(result["yoy"]) == scoring.STEADY


def test_yoy_needs_a_full_prior_year():
    assert scoring.yoy(trend([100] * 12)) is None
    assert scoring.yoy([]) is None


def test_labels():
    assert scoring.label(0.30) == scoring.SURGING
    assert scoring.label(0.12) == scoring.RISING
    assert scoring.label(-0.20) == scoring.COOLING
    assert scoring.label(None) == scoring.STEADY


def test_semrush_parse_and_momentum():
    text = ("Keyword;Search Volume;CPC;Competition;Trends;Intent;Keyword Difficulty Index\n"
            "pet grooming;60500;1.32;0.21;0.07,0.11,0.11,0.11,0.13,0.16,0.16,0.54,0.30,0.82,1.00,0.82;0;37\n")
    row = scoring.parse_semrush(text)[0]
    assert row["keyword"] == "pet grooming" and row["volume"] == 60500 and row["kd"] == 37
    assert scoring.semrush_momentum(row["trend"]) > 4  # the curve that the YoY check later disproved


def test_pack_weakness_and_own_brand_flag():
    serp = {"local_pack": [
        {"title": "TJ 24 Hour Mobile Tire Repair", "domain": "x.example", "rating": {"value": 4.6, "votes_count": 10}},
        {"title": "Other Tire", "domain": "y.example", "rating": {"value": 5, "votes_count": 2}},
        {"title": "Big Tire", "domain": "z.example", "rating": {"value": 3.9, "votes_count": 15}}],
        "organic": [{"domain": "www.yelp.com"}]}
    result = scoring.pack_weakness(serp, ["TJ"])
    assert result["weakness"] == 1.0 and result["median_reviews"] == 10
    assert result["pack"][0]["possibly_ours"] and not result["pack"][1]["possibly_ours"]
    locked = {"local_pack": [{"title": "A", "rating": {"votes_count": 2100}},
                             {"title": "B", "rating": {"votes_count": 833}},
                             {"title": "C", "rating": {"votes_count": 932}}]}
    assert scoring.pack_weakness(locked)["weakness"] == 0.1
    assert scoring.pack_weakness({"local_pack": []})["weakness"] is None


def test_plays_never_skip_the_guardrails():
    niche = {"home_based_fit": 9, "licensed": False, "portfolio": "TJ's Nationwide Roadside"}
    assert scoring.play_for(70, niche, 1.0, 0.3)[0] == "Own it"
    assert scoring.play_for(70, niche, 0.1, 0.3)[0] == "Watch"          # locked map pack
    assert scoring.play_for(70, niche, 1.0, -0.2)[0] == "Watch"         # cooling demand
    licensed = dict(niche, licensed=True)
    play, why = scoring.play_for(70, licensed, 1.0, 0.3)
    assert play == "Partner & manage" and "license" in why


def test_discovery_filters_brands_junk_and_known(tmp_path, monkeypatch):
    monkeypatch.setattr(scout, "RUNS", tmp_path)
    day = "2026-10-02"
    (tmp_path / day / "discovery").mkdir(parents=True)
    (tmp_path / day / "discovery" / "seed.json").write_text(json.dumps({"seed": "junk removal", "keywords": [
        {"keyword": "junk removal services", "volume": 49500, "intent": "commercial"},
        {"keyword": "petsmart grooming", "volume": 301000, "intent": "commercial"},
        {"keyword": "dog grooming supplies", "volume": 40500, "intent": "transactional"},
        {"keyword": "junk removal near me", "volume": 74000, "intent": "commercial"},
        {"keyword": "same day junk removal", "volume": 900, "intent": "commercial"},
        {"keyword": "tiny", "volume": 20, "intent": "commercial"}]}))
    cfg = scout.load_config()
    plan = {"keywords": ["junk removal near me"]}
    kept = [r["keyword"] for r in scout.discovered(day, cfg, plan)]
    assert kept == ["junk removal services", "same day junk removal"]


def test_brief_escapes_text_and_round_trips_state(tmp_path, monkeypatch):
    monkeypatch.setattr(scout, "RUNS", tmp_path)
    state = {"version": 1, "updated": "2026-10-02", "briefs": [{"date": "2026-10-02", "label": "x", "top": []}],
             "watchlist": {"a </script> b": {"score": 50, "label": "Steady", "play": "Watch"}}}
    brief = {"date": "2026-10-02", "weekday": "Friday", "label": "<b>Home</b>", "recap": False,
             "markets": ["Chicago, IL"], "opportunities": [], "serps": {}, "signals": {}, "own_sightings": [],
             "tactic": "t", "spend": {}, "state": state}
    html = render_html(brief)
    assert "<b>Home</b>" not in html and "&lt;b&gt;Home&lt;/b&gt;" in html
    page = tmp_path / "page.html"
    page.write_text(html)
    scout.cmd_restore(Namespace(date="2026-10-03", html=str(page)))
    restored = json.loads((tmp_path / "2026-10-03" / "prev_state.json").read_text())
    assert restored == state
