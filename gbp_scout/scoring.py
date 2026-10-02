"""Scoring for the daily GBP Opportunity Scout.

Every number here comes from a tool result the agent saved to disk. Nothing is
estimated. Semrush and OpenRush report different volumes for the same keyword,
so the two sources are never mixed in one comparison.
"""
import csv
import io
import math
import re
from statistics import median

SURGING, RISING, STEADY, COOLING = "Surging", "Rising", "Steady", "Cooling"
DIRECTORIES = ("yelp.", "thumbtack.", "angi.", "homeadvisor.", "bbb.", "nextdoor.", "facebook.",
               "reddit.", "instagram.", "yellowpages.", "porch.", "houzz.", "networx.", "taskrabbit.")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def local_query(keyword):
    """The map-pack check runs in a set city, so drop 'near me'."""
    return re.sub(r"\s+near me\b", "", keyword).strip()


# ---------------------------------------------------------------- Semrush screen

def parse_semrush(text):
    """Parse a Semrush phrase_these CSV (semicolon separated) into rows.

    Trends are 12 normalized values, oldest month first; the last value is the
    latest month.
    """
    reader = csv.DictReader(io.StringIO(text.strip()), delimiter=";")
    rows = []
    for raw in reader:
        trend = [float(x) for x in (raw.get("Trends") or "").split(",") if x.strip()]
        kd = raw.get("Keyword Difficulty Index") or raw.get("Keyword Difficulty")
        rows.append({
            "keyword": raw["Keyword"].strip().lower(),
            "volume": int(float(raw.get("Search Volume") or 0)),
            "cpc": float(raw.get("CPC") or 0),
            "competition": float(raw.get("Competition") or 0),
            "kd": int(float(kd)) if kd not in (None, "") else None,
            "trend": trend,
        })
    return rows


def semrush_momentum(trend):
    """Latest 3 months vs the 9 before them. 1.0 = flat. Seasonal, not year over year."""
    if len(trend) < 12:
        return None
    base = sum(trend[:9]) / 9
    if base <= 0:
        return None
    return round((sum(trend[9:]) / 3) / base, 2)


def screen_score(row, fit):
    """Rank keywords for a deep dive: demand, job value, momentum and home-based fit."""
    demand = clamp((math.log10(max(row["volume"], 1)) - 2) / 3)
    value = math.sqrt(clamp(row["cpc"] / 40))
    momentum = row.get("momentum")
    lift = clamp(((momentum or 1.0) - 0.8) / 0.8)
    return round(30 * demand + 25 * value + 30 * lift + 15 * fit / 10, 1)


# --------------------------------------------------------- OpenRush year over year

def yoy(trend):
    """Year-over-year change from an OpenRush 24-month trend list.

    Compares the latest 3 months with the same 3 months a year earlier, which
    removes normal seasonality. Returns None when the history is too short.
    """
    points = {(p["year"], p["month"]): p.get("search_volume") or 0 for p in trend or []}
    if not points:
        return None
    latest = max(points)
    months = []
    y, m = latest
    for _ in range(3):
        months.append((y, m))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    prior = [(y - 1, m) for y, m in months]
    if not all(k in points for k in months + prior):
        return None
    now, before = sum(points[k] for k in months), sum(points[k] for k in prior)
    prev_month = months[1]
    return {
        "latest_month": f"{latest[0]}-{latest[1]:02d}",
        "latest": points[latest],
        "last3": now,
        "prior_year3": before,
        "yoy": round(now / before - 1, 3) if before else None,
        "mom": round(points[latest] / points[prev_month] - 1, 3) if points[prev_month] else None,
    }


def label(change):
    if change is None:
        return STEADY
    if change >= 0.25:
        return SURGING
    if change >= 0.10:
        return RISING
    if change <= -0.15:
        return COOLING
    return STEADY


# ------------------------------------------------------------- map-pack weakness

def pack_weakness(serp, own_markers=()):
    """How easy the local map pack looks for a newcomer: 0 (locked) to 1 (wide open).

    Based on the review counts of the businesses Google shows in the pack, plus
    how many directories and forum threads fill page 1 (a sign few real local
    businesses have built strong pages).
    """
    pack = serp.get("local_pack") or []
    organic = serp.get("organic") or []
    if not pack:
        return {"weakness": None, "reason": "No map pack on this search.", "pack": [], "directories": 0}
    reviews = []
    rows = []
    for item in pack:
        rating = item.get("rating") or {}
        votes = rating.get("votes_count") or item.get("reviews") or 0
        reviews.append(votes)
        title = item.get("title") or item.get("name") or ""
        rows.append({
            "name": title,
            "domain": item.get("domain") or "",
            "rating": rating.get("value") if rating else item.get("rating"),
            "reviews": votes,
            "possibly_ours": any(re.search(rf"\b{re.escape(m)}\b", title) for m in own_markers),
        })
    mid = median(reviews)
    if mid < 20:
        weakness = 1.0
    elif mid < 50:
        weakness = 0.75
    elif mid < 150:
        weakness = 0.5
    elif mid < 400:
        weakness = 0.25
    else:
        weakness = 0.1
    directories = sum(1 for o in organic[:10] if any(d in (o.get("domain") or "") for d in DIRECTORIES))
    if directories >= 4:
        weakness = min(1.0, weakness + 0.1)
    return {"weakness": round(weakness, 2), "median_reviews": mid, "pack": rows,
            "directories": directories,
            "reason": f"Map-pack median {mid:g} reviews; {directories} directory/forum results in the top 10."}


# --------------------------------------------------------------- final scoring

def opportunity(kw, niche, deep=None, serp=None):
    """0–100 opportunity score with its parts, so every point can be traced."""
    volume = (deep or {}).get("volume") or kw["volume"]
    cpc = (deep or {}).get("cpc") if (deep or {}).get("cpc") is not None else kw["cpc"]
    change = (deep or {}).get("yoy")
    trend_source = "openrush yoy"
    if change is None and kw.get("momentum") is not None:
        change = kw["momentum"] - 1
        trend_source = "semrush 3-vs-9 month (seasonal)"
    parts = {
        "demand": round(25 * clamp((math.log10(max(volume, 1)) - 2) / 3), 1),
        "job_value": round(20 * math.sqrt(clamp(cpc / 40)), 1),
        "momentum": round(20 * clamp(((change or 0) + 0.1) / 0.6), 1),
        "competition": round(25 * (serp["weakness"] if serp and serp.get("weakness") is not None else 0.5), 1),
        "home_fit": float(niche["home_based_fit"]),
    }
    return round(sum(parts.values()), 1), parts, change, trend_source


PLAY_ORDER = {"Own it": 0, "Partner & manage": 1, "Validate": 2, "Watch": 3}


def play_for(score, niche, weakness, change):
    """Which legitimate GBP play fits. Never a profile for a business that doesn't exist."""
    if change is not None and change <= -0.15:
        return "Watch", "Demand is cooling. Don't build here yet."
    if weakness is not None and weakness <= 0.25:
        return "Watch", "Map pack is locked up: the top businesses have hundreds of reviews."
    licensed = niche.get("licensed")
    if score >= 60 and niche["home_based_fit"] >= 8 and not licensed:
        return ("Own it", f"Launch or extend a real service under {niche['portfolio']}: a service-area "
                          "profile from a real home base, run by people who do the work.")
    if weakness is not None and weakness >= 0.75:
        note = " Partner must hold the required license." if licensed else ""
        return ("Partner & manage", "Weak map pack. Find real local operators with thin profiles (run "
                                    "qualify-partners) and set up or manage their profile. They stay the "
                                    "owner." + note)
    if score >= 55:
        return "Validate", "Strong numbers. Check the map pack in your market before committing."
    return "Watch", "Keep on the watchlist."


def leaderboard(board):
    """Rank markets by how open their map packs have been across every reading so far."""
    rows = []
    for market, readings in board.items():
        if not readings:
            continue
        best = max(readings, key=lambda r: (r["weakness"], -r["median"]))
        rows.append({"market": market, "openness": round(sum(r["weakness"] for r in readings) / len(readings), 2),
                     "readings": len(readings), "last": max(r["date"] for r in readings),
                     "best_query": best["query"], "best_median": best["median"]})
    rows.sort(key=lambda r: (-r["openness"], -r["readings"]))
    return rows
