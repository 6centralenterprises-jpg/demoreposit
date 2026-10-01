"""The 10-point partner rubric: research evidence in, score and verdict out.

"Never guess" is enforced here, not just requested of the researcher: a
finding only counts when it carries a source URL. Anything without one is
"not confirmed" and earns 0 points, but still counts toward the maximum the
business could reach — that's what separates VERIFY from SKIP.
"""
from datetime import date

from .normalize import FREE_MAIL_DOMAINS

MESSAGE_THRESHOLD = 7

# Niches that need a state license in Illinois. A business in one of these
# niches without a verified active license is never contacted.
LICENSE_REQUIRED = {
    "pest control": "Illinois Dept. of Public Health structural pest control license",
    "plumbing": "Illinois Dept. of Public Health plumbing license",
    "roofing": "Illinois Dept. of Financial & Professional Regulation roofing license",
}

# (key, area, max points, label, short name used in "to verify" lists)
CRITERIA = [
    ("rating", "Reputation", 2, "Rating 4.3+ with 15+ reviews", "reviews"),
    ("complaints", "Reputation", 1, "No unresolved complaints", "complaint history"),
    ("presence", "Legitimacy", 1, "Confirmed real, active business", "identity"),
    ("established", "Legitimacy", 1, "2+ years in business or registered entity", "years in business"),
    ("size", "Fit", 1, "Owner-run or 1-15 workers, not a chain", "team size"),
    ("serves_target", "Fit", 1, "Serves the target market", "service area"),
    ("insured", "Trust", 1, "Publicly states it is insured", "insurance"),
    ("other_trust", "Trust", 1, "Bonded, background checks, certified or accredited", "bonding/background checks"),
    ("activity", "Responsiveness", 1, "Active in last 90 days or replies to reviews", "recent activity"),
]

SMALL_SIZES = {"owner-run", "1-5", "6-15"}
LARGE_SIZES = {"16-50", "50+"}


def has_source(item):
    return isinstance(item, dict) and str(item.get("source") or "").startswith(("http://", "https://"))


def _int(value):
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(text):
    """Parse YYYY-MM-DD or YYYY-MM (month-only dates count as the 28th)."""
    parts = [int(p) for p in str(text or "")[:10].split("-") if p.isdigit()]
    if len(parts) < 2 or parts[0] < 1900:
        return None
    year, month, day = (parts + [28])[:3]
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _rating(ev, _today):
    rows = [r for r in ev.get("reviews") or [] if has_source(r) and _int(r.get("count")) is not None]
    if not rows:
        return 0, "unknown", "No review profile found", ""
    summary = "; ".join(f"{r.get('platform') or 'Reviews'} {r.get('rating', '?')}★ ({_int(r['count'])})" for r in rows)
    rated = [r for r in rows if _float(r.get("rating")) is not None and _int(r["count"]) > 0]
    total = sum(_int(r["count"]) for r in rows)
    weight = sum(_int(r["count"]) for r in rated)
    average = sum(_float(r["rating"]) * _int(r["count"]) for r in rated) / weight if weight else None
    source = max(rows, key=lambda r: _int(r["count"]))["source"]
    if average is not None and average >= 4.3 and total >= 15:
        return 2, "met", summary, source
    if average is not None and average >= 4.0 and total >= 5:
        return 1, "partial", summary, source
    return 0, "not_met", summary, source


def _complaints(ev, _today):
    c = ev.get("complaints") or {}
    items = [i for i in c.get("items") or [] if has_source(i)]
    unresolved = [i for i in items if i.get("resolved") is not True]
    checked = [u for u in c.get("checked_sources") or [] if str(u).startswith("http")]
    if unresolved:
        return 0, "not_met", f"{len(unresolved)} unresolved: {unresolved[0].get('summary', '')}", unresolved[0]["source"]
    if items:
        return 1, "met", f"{len(items)} complaint(s), all resolved", items[0]["source"]
    if c.get("status") == "none_found" and checked:
        return 1, "met", f"None found ({len(checked)} source(s) checked)", checked[0]
    return 0, "unknown", "Complaint history not checked", ""


def _presence(ev, _today):
    identity = ev.get("identity") or {}
    if identity.get("status") == "confirmed" and has_source(identity):
        return 1, "met", identity.get("note") or "Confirmed", identity["source"]
    return 0, "unknown", "Identity not fully confirmed", ""


def _established(ev, today):
    e = ev.get("established") or {}
    year = _int(e.get("year_started"))
    registration = e.get("registration")
    if year and has_source(e) and today.year - year >= 2:
        return 1, "met", f"In business since {year}", e["source"]
    if has_source(registration):
        return 1, "met", f"Registered: {registration.get('type') or 'yes'}", registration["source"]
    if year and has_source(e):
        return 0, "not_met", f"Started {year} (under 2 years)", e["source"]
    return 0, "unknown", "Years in business not confirmed", ""


def _size(ev, _today):
    s = ev.get("size") or {}
    if not has_source(s):
        return 0, "unknown", "Team size not confirmed", ""
    value = str(s.get("value") or "").lower()
    if s.get("is_franchise_or_national") is True:
        return 0, "not_met", "Franchise or national brand", s["source"]
    if value in SMALL_SIZES:
        return 1, "met", s.get("evidence") or value, s["source"]
    if value in LARGE_SIZES:
        return 0, "not_met", f"Larger than target ({value})", s["source"]
    return 0, "unknown", "Team size not confirmed", ""


def _serves_target(ev, _today):
    t = ev.get("serves_target") or {}
    if has_source(t) and t.get("value") is True:
        return 1, "met", t.get("areas") or "Yes", t["source"]
    if has_source(t) and t.get("value") is False:
        return 0, "not_met", t.get("areas") or "No", t["source"]
    return 0, "unknown", "Service area not confirmed", ""


def _insured(ev, _today):
    i = ev.get("insured") or {}
    if has_source(i) and i.get("value") is True:
        return 1, "met", f"\"{i.get('quote') or 'insured'}\"", i["source"]
    if has_source(i) and i.get("value") is False:
        return 0, "not_met", i.get("quote") or "Says not insured", i["source"]
    return 0, "unknown", "Insurance not confirmed", ""


def _other_trust(ev, _today):
    t = ev.get("other_trust") or {}
    signals = [s for s in t.get("signals") or [] if has_source(s)]
    if signals:
        return 1, "met", ", ".join(s.get("signal") or "" for s in signals), signals[0]["source"]
    if t.get("checked") is True:
        return 0, "not_met", "None found", ""
    return 0, "unknown", "Not checked", ""


def _activity(ev, today):
    a = ev.get("activity") or {}
    if not has_source(a):
        return 0, "unknown", "Recent activity not confirmed", ""
    if a.get("responds_to_reviews") is True:
        return 1, "met", "Replies to reviews", a["source"]
    last = _parse_date(a.get("last_active"))
    if last and (today - last).days <= 90:
        return 1, "met", f"Active {a.get('last_active')}", a["source"]
    if last:
        return 0, "not_met", f"Last active {a.get('last_active')}", a["source"]
    return 0, "unknown", "Recent activity not confirmed", ""


CHECKS = {
    "rating": _rating, "complaints": _complaints, "presence": _presence,
    "established": _established, "size": _size, "serves_target": _serves_target,
    "insured": _insured, "other_trust": _other_trust, "activity": _activity,
}


def required_license(niche):
    niche = (niche or "").lower()
    return next((text for key, text in LICENSE_REQUIRED.items() if key in niche), "")


def score(lead, ev, market):
    """Score one lead. `ev` is the researcher's evidence dict, or None if not researched."""
    if lead.get("screen") == "skip_duplicate":
        return _result(lead, "SKIP", f"Duplicate of {lead['duplicate_of']}")
    if not ev:
        return _result(lead, "NOT RESEARCHED", "Research not run yet")

    today = _parse_date(ev.get("researched_at")) or date.today()
    breakdown, total, maximum = [], 0, 0
    for key, area, points, label, short in CRITERIA:
        got, status, finding, source = CHECKS[key](ev, today)
        breakdown.append({"key": key, "area": area, "label": label, "short": short, "max": points,
                          "points": got, "status": status, "finding": finding, "source": source})
        total += got
        maximum += points if status == "unknown" else got

    identity = ev.get("identity") or {}
    niche = (ev.get("niche") or {}).get("value") or lead.get("niche_guess") or ""
    flags = [f for f in ev.get("red_flags") or [] if has_source(f)]
    serious = [f for f in flags if str(f.get("severity", "")).lower() in ("high", "medium")]
    license_text = required_license(niche)
    lic = ev.get("license") or {}
    license_ok = has_source(lic) and str(lic.get("status", "")).lower() == "active" and lic.get("number")
    unknowns = [b["short"] for b in breakdown if b["status"] == "unknown"]
    target = ev.get("serves_target") or {}
    provider = identity.get("is_service_provider")

    if identity.get("status") == "not_found":
        verdict, reason = "SKIP", "Could not confirm a real, active business"
    elif provider is False and has_source(identity):
        verdict, reason = "SKIP", "Not a local service provider"
    elif has_source(target) and target.get("value") is False:
        verdict, reason = "SKIP", f"Does not serve {market}"
    elif license_text and not license_ok:
        verdict, reason = "DO NOT CONTACT", f"{license_text} not verified (no license shown = do not contact)"
    elif maximum < MESSAGE_THRESHOLD:
        verdict, reason = "SKIP", f"Can't reach {MESSAGE_THRESHOLD}/10 even if unconfirmed items check out"
    elif serious:
        verdict, reason = "HOLD", "Red flag for Terell to review: " + "; ".join(f.get("flag", "") for f in serious)
    elif total >= MESSAGE_THRESHOLD:
        verdict, reason = "MESSAGE", "Meets partner standard"
    else:
        verdict, reason = "VERIFY", f"{total}/10 confirmed; could reach {maximum} — check: " + ", ".join(unknowns)

    result = _result(lead, verdict, reason)
    result.update({
        "score": total,
        "max_possible": maximum,
        "review_total": sum(_int(r.get("count")) or 0 for r in ev.get("reviews") or [] if has_source(r)),
        "breakdown": breakdown,
        "to_verify": unknowns,
        "niche": niche,
        "business_name": identity.get("business_name") or lead.get("name") or lead.get("handle"),
        "red_flags": flags,
        "unsourced_concerns": [f.get("flag", "") for f in ev.get("red_flags") or [] if not has_source(f)],
        "license": lic if license_text else {},
        "license_required": license_text,
        "why": "; ".join(b["finding"] for b in breakdown if b["status"] == "met")[:400],
        "opener": ev.get("opener") if has_source(ev.get("opener")) else {},
        "contact": _best_contact(lead, ev),
        "website": (ev.get("online_presence") or {}).get("website_url") or lead.get("website", ""),
        "notes": ev.get("notes", ""),
        "researched_at": ev.get("researched_at", ""),
    })
    return result


def _best_contact(lead, ev):
    contact = ev.get("contact") or {}
    email = (contact.get("email") or lead.get("email") or "").lower()
    listed_at = contact.get("email_publicly_listed_at") or ""
    if email and listed_at:
        basis = "publicly listed"
    elif email and email == lead.get("email"):
        basis = "from IGLeads (Instagram profile)"
    else:
        basis = ""
    free = email.split("@")[-1] in FREE_MAIL_DOMAINS
    phone = contact.get("phone") or lead.get("phone") or ""
    if email:
        best = f"Email {email}" + (" (free-mail, business-listed)" if free and listed_at else " (free-mail)" if free else "")
    elif phone:
        best = f"Phone {phone}"
    elif lead.get("handle"):
        best = f"Instagram DM @{lead['handle']}"
    else:
        best = "No contact found"
    return {"best": best, "email": email, "email_basis": basis, "email_listed_at": listed_at,
            "email_free_mail": bool(email) and free, "phone": phone,
            "contact_page": contact.get("contact_page") or ""}


def _result(lead, verdict, reason):
    return {
        "lead_id": lead["lead_id"], "verdict": verdict, "reason": reason, "score": None,
        "max_possible": None, "review_total": 0, "breakdown": [], "to_verify": [], "niche": lead.get("niche_guess", ""),
        "business_name": lead.get("name") or lead.get("handle"), "red_flags": [],
        "unsourced_concerns": [], "license": {}, "license_required": "", "why": "", "opener": {},
        "contact": _best_contact(lead, {}), "website": lead.get("website", ""), "notes": "",
        "researched_at": "",
    }
