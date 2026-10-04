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

def pack_weakness(serp, own_markers=(), own_names=()):
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
        votes = rating.get("votes_count")
        if votes is None:
            votes = item.get("reviews")
        # A blank rating is unknown, not zero: the data feed sometimes omits ratings for listings that have reviews.
        if votes is not None:
            reviews.append(votes)
        title = item.get("title") or item.get("name") or ""
        rows.append({
            "name": title,
            "domain": item.get("domain") or "",
            "rating": rating.get("value") if rating else item.get("rating"),
            "reviews": votes,
            "ours": title.strip().lower() in {n.lower() for n in own_names},
            "possibly_ours": (title.strip().lower() not in {n.lower() for n in own_names}
                              and any(re.search(rf"\b{re.escape(m)}\b", title) for m in own_markers)),
        })
    if not reviews:
        return {"weakness": None, "median_reviews": None, "pack": rows, "directories": 0,
                "reason": "Review counts weren't returned for this pack; check it by hand before trusting it."}
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


# ------------------------------------------------- verification, Google risk, season

# How a real business verifies its Google profile, and how much of it 6 Central owns.
VERIFY_EASE = {"own": 1.0, "own-licensed": 0.7, "office": 0.4, "partner": 0.25, "no": 0.0}
VERIFY_GRADE = {"own": "A", "own-licensed": "B", "office": "C", "partner": "D", "no": "F"}
VERIFY_TEXT = {"own": "We verify and own it", "own-licensed": "We own it; licensed staff do the work",
               "office": "Needs a real staffed office", "partner": "Partner's profile; we own the site",
               "no": "Can't be verified"}
RISK_PENALTY = {"high": 15.0, "medium": 7.0, "low": 2.0}
RISK_RANK = {"high": 3, "medium": 2, "low": 1}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def google_risk(niche_name, niche, register=(), flags=None):
    """The strongest Google risk that applies to a niche, from the dated register and the daily watch.

    A register entry applies when it names the niche, or when one of its telltale search terms appears
    in one of the niche's keywords. Returns None when nothing applies.
    """
    name = niche_name.lower()
    keywords = [k.lower() for k in niche.get("keywords", [])]
    hits = []
    for entry in list(register) + list((flags or {}).values()):
        names = [n.lower() for n in entry.get("niches", [])]
        terms = [t.lower() for t in entry.get("keywords", [])]
        if name in names or any(t and any(t in k for k in keywords) for t in terms):
            hits.append(entry)
    if not hits:
        return None
    top = max(hits, key=lambda e: RISK_RANK.get(e.get("level"), 0))
    return {"level": top.get("level"), "what": top.get("what") or top.get("summary"), "plan": top.get("plan"),
            "id": top.get("id"), "since": top.get("since"),
            "source": (top.get("sources") or [{}])[0].get("url") if top.get("sources") else top.get("source")}


def season_ahead(trend, today):
    """Is the season about to turn up? Uses last year's months from an OpenRush 24-month trend.

    Compares last year's next three months (after today's month) with today's month last year.
    Returns {"ratio", "peak_month", "peak_volume"} or None when the history doesn't cover it.
    """
    points = {(p["year"], p["month"]): p.get("search_volume") or 0 for p in trend or []}
    year, month = int(today[:4]), int(today[5:7])
    base = points.get((year - 1, month))
    ahead = []
    y, m = year - 1, month
    for _ in range(3):
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
        if (y, m) not in points:
            return None
        ahead.append(((y, m), points[(y, m)]))
    if not base:
        return None
    peak = max(ahead, key=lambda kv: kv[1])
    return {"ratio": round(sum(v for _, v in ahead) / 3 / base, 2), "peak_month": MONTHS[peak[0][1] - 1],
            "peak_volume": peak[1]}


def big_fish(volume, weakness, verify):
    """A small, open pond we can own: modest demand, a weak map pack, and a profile we can verify ourselves."""
    return bool(volume and volume <= 15000 and weakness is not None and weakness >= 0.75
                and verify in ("own", "own-licensed"))


# --------------------------------------------------------------- final scoring

def opportunity(kw, niche, deep=None, serp=None, risk=None, season=None):
    """0–100 opportunity score with its parts, so every point can be traced.

    Demand 20, job value 15, momentum or season ahead 15, map-pack openness 25, ease of verification 15,
    home-based fit 10, minus a Google-risk penalty (high 15, medium 7, low 2).
    """
    volume = (deep or {}).get("volume") or kw["volume"]
    cpc = (deep or {}).get("cpc") if (deep or {}).get("cpc") is not None else kw["cpc"]
    change = (deep or {}).get("yoy")
    trend_source = "openrush yoy"
    if change is None and kw.get("momentum") is not None:
        change = kw["momentum"] - 1
        trend_source = "semrush 3-vs-9 month (seasonal)"
    trend_part = clamp(((change or 0) + 0.1) / 0.6)
    season_part = clamp(((season or {}).get("ratio", 1.0) - 1.0) / 0.6)
    parts = {
        "demand": round(20 * clamp((math.log10(max(volume, 1)) - 2) / 3), 1),
        "job_value": round(15 * math.sqrt(clamp(cpc / 40)), 1),
        "momentum": round(15 * max(trend_part, season_part), 1),
        "competition": round(25 * (serp["weakness"] if serp and serp.get("weakness") is not None else 0.5), 1),
        "verify": round(15 * VERIFY_EASE.get(niche.get("verify", "partner"), 0.25), 1),
        "home_fit": float(niche["home_based_fit"]),
        "google_risk": -RISK_PENALTY.get((risk or {}).get("level"), 0.0),
    }
    return round(max(0.0, sum(parts.values())), 1), parts, change, trend_source


PLAY_ORDER = {"Own it": 0, "Partner & manage": 1, "Validate": 2, "Watch": 3, "Avoid": 4}


def play_for(score, niche, weakness, change, risk=None, season=None):
    """Which legitimate GBP play fits. Never a profile for a business that doesn't exist."""
    if risk and risk.get("level") == "high":
        plan = f" Plan: {risk['plan']}" if risk.get("plan") else ""
        return "Avoid", f"Google is flagging this niche now: {risk.get('what')}{plan}"
    rising_season = season and season.get("ratio", 0) >= 1.3
    if change is not None and change <= -0.15 and not rising_season:
        return "Watch", "Demand is cooling. Don't build here yet."
    if weakness is not None and weakness <= 0.25:
        return "Watch", "Map pack is locked up: the top businesses have hundreds of reviews."
    licensed = niche.get("licensed")
    caution = f" Google watch: {risk['what']}" if risk and risk.get("level") == "medium" else ""
    open_pack = weakness is not None and weakness >= 0.6
    if score >= 60 and open_pack and niche["home_based_fit"] >= 8 and not licensed and niche.get("verify", "own") == "own":
        timing = (f" Season turns up next: last year the next 3 months ran {season['ratio']:.1f}x this month "
                  f"(peak {season['peak_month']}). Launch now to have reviews before the peak.") if rising_season else ""
        return ("Own it", f"Launch or extend a real service under {niche['portfolio']}: a service-area "
                          "profile from a real home base, run by people who do the work." + timing + caution)
    if weakness is not None and weakness >= 0.75:
        note = " Partner must hold the required license." if licensed else ""
        return ("Partner & manage", "Weak map pack. Find real local operators with thin profiles (run "
                                    "qualify-partners) and set up or manage their profile. They stay the "
                                    "owner." + note + caution)
    if score >= 55 and weakness is None:
        return "Validate", "Strong numbers. Check the map pack in your market before committing." + caution
    if score >= 55:
        return ("Watch", "Good numbers, but the map pack here is contested. Look for a smaller pond: a suburb "
                         "where the top 3 have under 50 reviews, or a narrower version of the service." + caution)
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


def listing_health(listing, check, other_cities):
    """Where a confirmed listing of ours sits in its tracked map pack, plus anything that risks a suspension."""
    pack = (check or {}).get("pack") or []
    spot = next((i for i, p in enumerate(pack, 1) if p.get("ours")), None)
    me = pack[spot - 1] if spot else {}
    issues = []
    name = listing["name"]
    home_city = listing["market"].split(",")[0].strip().lower()
    if home_city in name.lower():
        issues.append(f"The profile name includes the city (\"{listing['market'].split(',')[0]}\"). Google only allows "
                      "that if it is part of the real business name on your signage and paperwork; otherwise it "
                      "counts as keyword stuffing, a common suspension trigger.")
    domain = (me.get("domain") or "").lower()
    clash = [c for c in other_cities if c.lower().replace(" ", "") in domain.replace("-", "")]
    if clash:
        issues.append(f"The website ({domain}) is named for {clash[0]}, not {listing['market']}. A site that "
                      "names a different city than the profile is a mismatch Google's checks look for.")
    if domain.endswith((".lovable.app", ".vercel.app", ".netlify.app", ".weebly.com", ".wixsite.com")):
        issues.append("The website is on a free builder subdomain. A domain 6 Central owns is a durable asset "
                      "and reads as a real business.")
    return {"name": name, "market": listing["market"], "query": listing["track_query"],
            "checked": check is not None, "position": spot, "rating": me.get("rating"),
            "reviews": me.get("reviews"), "domain": me.get("domain"), "issues": issues}
