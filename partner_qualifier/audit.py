"""Partner audits: how visible each partner is online, how much they likely need
our jobs, and whether their custom email follows the outreach rules.

The best partners do great work but are hard to find online — strong reviews,
weak search presence. Quality (the qualification score) says whether we can
trust them with our customers; Need says how much our jobs would matter to
them. Both come from sourced data, never guesses.
"""
import json
import re
import statistics

from .normalize import domain_of

OPT_OUT = "If you'd rather not hear from me, just reply 'no thanks' and I won't email again."
MAX_EMAIL_WORDS = 120  # whole email, signature and opt-out included
MAX_READING_GRADE = 8.5

# Claims the outreach rules forbid: promised volume or income, exclusivity,
# size we don't have, and fake urgency.
RISKY_PATTERNS = {
    "guarantee": r"\bguarantee",
    "exclusivity": r"\bexclusiv",
    "income promise": r"\bincome\b|\bearnings?\b|\$\s?\d",
    "job-volume promise": r"\b\d+\s*\+?\s*(new )?(jobs|leads)\b|\b(steady|constant|lots of|plenty of|a lot of) (jobs|work|leads)\b",
    "size claim": r"\bhundreds\b|\bthousands\b|\blargest\b|\bleading\b|#1|\bnationwide\b",
    "fake urgency": r"\blimited time\b|\bact now\b|\burgent|\blast chance\b|\bspots? (are )?(filling|left)\b",
    "jargon": r"\bseo\b|\bkeywords?\b|\brankings?\b|\bsearch traffic\b|\bbacklinks?\b",
}


def has_ref(item):
    """A sourced item: a URL, or a data-tool reference like "openrush:inspect_domain@2026-10-01"."""
    source = str((item or {}).get("source") or "") if isinstance(item, dict) else ""
    return source.startswith(("http://", "https://", "openrush:", "tool:"))


def _norm(name):
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _int(value):
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


# --- Market -----------------------------------------------------------------

def load_markets(market_dir):
    markets = {}
    for path in sorted(market_dir.glob("*.json")) if market_dir.exists() else []:
        data = json.loads(path.read_text())
        markets[(data.get("niche") or path.stem).lower()] = data
    return markets


def market_for(niche, markets):
    niche = (niche or "").lower()
    if niche in markets:
        return markets[niche]
    return next((m for key, m in markets.items() if key in niche or niche in key), None) if niche else None


def _is_ad(biz):
    """Paid placements in the map pack link through google.com/aclk."""
    return domain_of(biz.get("url") or biz.get("domain") or "").endswith("google.com")


def local_leaders(market):
    """Businesses in Google's map pack across the market's money keywords."""
    leaders = {}
    for serp in (market or {}).get("serps", []):
        for biz in serp.get("local_pack", []):
            if _is_ad(biz):
                continue
            key = domain_of(biz.get("url") or biz.get("domain") or "") or _norm(biz.get("name"))
            entry = leaders.setdefault(key, {"name": biz.get("name"), "domain": domain_of(biz.get("url") or biz.get("domain") or ""),
                                             "rating": biz.get("rating"), "reviews": _int(biz.get("reviews")),
                                             "appearances": 0, "keywords": []})
            entry["appearances"] += 1
            entry["keywords"].append(serp.get("keyword"))
    return sorted(leaders.values(), key=lambda b: (-b["appearances"], -(b["reviews"] or 0)))


def local_pack_hits(partner_domain, partner_name, market):
    """Money keywords where the partner shows up in Google's map pack (top 3)."""
    hits, name = [], _norm(partner_name)
    for serp in (market or {}).get("serps", []):
        for biz in serp.get("local_pack", []):
            if _is_ad(biz):
                continue
            biz_domain = domain_of(biz.get("url") or biz.get("domain") or "")
            biz_name = _norm(biz.get("name"))
            same_domain = partner_domain and biz_domain == partner_domain
            same_name = len(name) >= 6 and len(biz_name) >= 6 and (name in biz_name or biz_name in name)
            if same_domain or same_name:
                hits.append({"keyword": serp.get("keyword"), "rating": biz.get("rating"),
                             "reviews": _int(biz.get("reviews")), "source": serp.get("source", "")})
                break
    return hits


def money_keywords(market):
    return sorted((market or {}).get("keywords", []), key=lambda k: -(_int(k.get("volume")) or 0))


def missing_keywords(audit, market, limit=8):
    """High-demand searches in this market where the partner isn't on page 1 or 2."""
    ranked = {(k.get("keyword") or "").lower(): k.get("position") for k in (audit.get("keywords") or {}).get("ranking") or []}
    missing = []
    for k in money_keywords(market):
        position = ranked.get((k.get("keyword") or "").lower())
        if position is None or position > 20:
            missing.append({"keyword": k.get("keyword"), "volume": _int(k.get("volume"))})
    return missing[:limit]


# --- Scores -----------------------------------------------------------------

def partner_reviews(audit, evidence):
    rep = audit.get("google_reputation") or {}
    counts = [_int(rep.get("google_review_count"))]
    counts += [_int(p.get("count")) for p in rep.get("other_platforms") or []]
    counts += [_int(r.get("count")) for r in (evidence or {}).get("reviews") or []]
    return max([c for c in counts if c is not None], default=None)


def visibility(audit, evidence, market, pack_hits):
    """0-10: how easily customers find this partner today. Unknown parts count 1 of 2."""
    seo = audit.get("seo") or {}
    kind = seo.get("website_type")
    no_site = kind in ("none", "social_only", "link_page")
    parts = []

    def add(name, points, note):
        known = points is not None
        parts.append({"part": name, "points": points if known else 1, "known": known, "note": note})

    add("Website", {"own_site": 2, "booking_page": 1, "link_page": 1, "social_only": 0, "none": 0}.get(kind),
        kind or "not checked")

    top10 = [k for k in (audit.get("keywords") or {}).get("ranking") or [] if (k.get("position") or 99) <= 10]
    if no_site:
        add("Page-1 Google rankings", 0, "no website")
    elif seo.get("organic_keywords") is not None:
        add("Page-1 Google rankings", 0 if not top10 else 1 if len(top10) <= 2 else 2,
            f"{len(top10)} money keyword(s) on page 1")
    else:
        add("Page-1 Google rankings", None, "not checked")

    if market and market.get("serps"):
        add("Google map pack", 0 if not pack_hits else 1 if len(pack_hits) == 1 else 2,
            f"in map pack for {len(pack_hits)} of {len(market['serps'])} searches checked")
    else:
        add("Google map pack", None, "market not checked")

    traffic = _int(seo.get("est_monthly_traffic"))
    if no_site:
        add("Website visitors", 0, "no website")
    elif traffic is not None:
        add("Website visitors", 0 if traffic < 100 else 1 if traffic < 1000 else 2, f"~{traffic:,}/month (estimate)")
    else:
        add("Website visitors", None, "not checked")

    reviews = partner_reviews(audit, evidence)
    leader_counts = [b["reviews"] for b in local_leaders(market) if b["reviews"]]
    if reviews is not None and leader_counts:
        benchmark = statistics.median(leader_counts)
        ratio = reviews / benchmark
        add("Reviews vs. local leaders", 0 if ratio < 0.25 else 1 if ratio < 0.75 else 2,
            f"{reviews:,} vs. leader median {benchmark:,.0f}")
    else:
        add("Reviews vs. local leaders", None, "no benchmark")

    return sum(p["points"] for p in parts), parts


SMALL_SIZES = ("owner-run", "1-5", "2-5", "6-15")
LARGE_SIZES = ("50+", "51-200", "200+")


def shop_size(evidence, reviews_total):
    """small / mid / large / unknown. Small owner-run shops are the partners most likely to want our jobs.
    A sourced team-size band wins over the review count; how visible they are is scored separately."""
    size = (evidence or {}).get("size") or {}
    band = (size.get("value") or "").lower()
    reviews = reviews_total or 0
    if size.get("is_franchise_or_national") or band in LARGE_SIZES or reviews >= 500:
        return "large"
    if band in SMALL_SIZES:
        return "small"
    if band == "16-50" or reviews >= 150:
        return "mid"
    return "small" if reviews_total is not None else "unknown"


SIZE_NEED = {"small": 1, "mid": 0, "large": -2, "unknown": 0}
SIZE_ORDER = ["small", "unknown", "mid", "large"]


def need_score(visibility_score, audit, size="unknown"):
    signals = [s for s in audit.get("capacity_signals") or [] if has_ref(s)]
    return max(0, min(10, 10 - visibility_score + min(2, len(signals)) + SIZE_NEED[size]))


def quadrant(quality, need):
    if quality is None or quality < 7:
        return "Vet first"
    if need >= 6:
        return "Ideal partner: great work, under-marketed"
    if need >= 4:
        return "Good partner"
    return "Strong and visible: may not need our jobs"


QUADRANT_ORDER = ["Ideal partner: great work, under-marketed", "Good partner",
                  "Strong and visible: may not need our jobs", "Vet first"]


# --- Email ------------------------------------------------------------------

def signature(sender):
    return "\n".join([sender["name"], f"{sender['title']}, {sender['company']}", sender["phone"],
                      sender["mailing_address"]])


def assemble_email(body, sender):
    return f"{body.strip()}\n\n{signature(sender)}\n\n{OPT_OUT}"


def _syllables(word):
    word = word.lower()
    groups = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and not word.endswith(("le", "ee")) and groups > 1:
        groups -= 1
    return max(1, groups)


def reading_grade(text):
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", text)
    sentences = max(1, len(re.findall(r"[.!?]+(\s|$)", text)))
    if not words:
        return 0.0
    syllables = sum(_syllables(w) for w in words)
    return round(0.39 * len(words) / sentences + 11.8 * syllables / len(words) - 15.59, 1)


def check_email(email, sender):
    body = (email or {}).get("body") or ""
    subject = (email or {}).get("subject") or ""
    facts = (email or {}).get("facts_used") or []
    full = assemble_email(body, sender)
    words = len(re.findall(r"\b[\w'’-]+\b", full))
    risky = [name for name, pattern in RISKY_PATTERNS.items() if re.search(pattern, body + " " + subject, re.I)]
    checks = {
        f"Under {MAX_EMAIL_WORDS} words ({words})": words < MAX_EMAIL_WORDS,
        "Says who we are": sender["company"].lower() in body.lower(),
        "Says we send paid jobs": bool(re.search(r"\bjobs?\b", body, re.I) and re.search(r"\bpaid\b|\bpay", body, re.I)),
        "Price agreed up front": bool(re.search(r"\bprice", body, re.I)
                                      and re.search(r"up ?front|ahead of|before (each|the|every|any) job|in advance", body, re.I)),
        "Exactly one question": body.count("?") == 1,
        "Uses a true, sourced fact": bool(facts) and all(has_ref(f) for f in facts),
        "No risky claims" + (f" ({', '.join(risky)})" if risky else ""): not risky,
        "Short subject line": 0 < len(subject) <= 60,
    }
    grade = reading_grade(body)
    failed = [name for name, ok in checks.items() if not ok]
    warnings = [f"Reading level ~grade {grade}; aim for 8 or lower"] if grade > MAX_READING_GRADE else []
    status = "Needs rewrite" if failed or not body else "Draft: needs Terell's approval"
    return {"full_text": full, "words": words, "grade": grade, "checks": checks, "failed": failed,
            "warnings": warnings, "status": status}


# --- Assemble one partner ----------------------------------------------------

def audit_partner(lead, evidence, result, audit, market, sender):
    seo = audit.get("seo") or {}
    website = seo.get("website") or result.get("website") or lead.get("website") or ""
    domain = domain_of(website) if seo.get("website_type") in (None, "own_site", "booking_page") else ""
    name = audit.get("business_name") or result.get("business_name")
    hits = local_pack_hits(domain, name, market)
    vis, parts = visibility(audit, evidence, market, hits)
    size = shop_size(evidence, partner_reviews(audit, evidence))
    need = need_score(vis, audit, size)
    quality = result.get("score")
    rep = audit.get("google_reputation") or {}
    google = None
    if rep.get("google_rating") is not None and has_ref({"source": rep.get("google_source")}):
        google = {"rating": rep["google_rating"], "reviews": _int(rep.get("google_review_count")),
                  "source": rep.get("google_source"), "via": "search"}
    pack_ratings = [h for h in hits if h.get("rating") is not None]
    if pack_ratings:  # a live Google map-pack reading beats a third-party mirror
        best = max(pack_ratings, key=lambda h: h.get("reviews") or 0)
        google = {"rating": best["rating"], "reviews": best["reviews"], "source": best.get("source", ""),
                  "via": "Google map pack (live)"}
    searches = len((market or {}).get("serps", []))
    # In the map pack for half or more of the money searches: they compete with
    # our brands for the same customers, and customers we send could book them
    # directly next time.
    competes = bool(searches) and len(hits) * 2 >= searches
    right = [p for p in audit.get("doing_right") or [] if has_ref(p)]
    wrong = [p for p in audit.get("doing_wrong") or [] if has_ref(p)]
    return {
        "lead_id": lead["lead_id"],
        "business_name": name,
        "niche": audit.get("niche") or result.get("niche"),
        "quality": quality,
        "verdict": result.get("verdict"),
        "visibility": vis,
        "visibility_parts": parts,
        "visibility_estimated": any(not p["known"] for p in parts),
        "need": need,
        "shop_size": size,
        "quadrant": quadrant(quality, need),
        "google": google,
        "reviews_total": partner_reviews(audit, evidence),
        "pack_hits": hits,
        "competes_on_google": competes,
        "missing_keywords": missing_keywords(audit, market),
        "doing_right": right,
        "doing_wrong": wrong,
        "unsourced_points": len(audit.get("doing_right") or []) + len(audit.get("doing_wrong") or []) - len(right) - len(wrong),
        "email": {**(audit.get("email") or {}), **check_email(audit.get("email"), sender)},
        "website": website,
        "domain": domain,
        "contact": result.get("contact") or {},
        "audit": audit,
    }


def rank_partners(rows):
    return sorted(rows, key=lambda r: (QUADRANT_ORDER.index(r["quadrant"]), SIZE_ORDER.index(r["shop_size"]),
                                       -r["need"], -(r["quality"] or 0),
                                       -(r["reviews_total"] or 0)))
