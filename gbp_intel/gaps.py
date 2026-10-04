"""Profile gap analysis: one of our Google profiles against a market's leaders.

Every check uses data Google's Places API returns. Checks that need posts,
photos, review replies or full review history arrive with the Business
Profile API (our profiles) and DataForSEO (competitors)."""
from collections import Counter
from statistics import median

GAP, OK, INFO = "gap", "ok", "info"


def nice_type(t):
    return t.replace("_", " ").capitalize()


def _median(values):
    values = [v for v in values if v is not None]
    return median(values) if values else None


def _share(items, test):
    return sum(1 for r in items if test(r)), len(items)


def analyze(ours, competitors):
    """ours: our cached place dict. competitors: places from a search, in rank order, ours removed."""
    top3, top10 = competitors[:3], competitors[:10]
    checks = []

    def add(name, status, ours_value, benchmark, step=""):
        checks.append({"check": name, "status": status, "ours": ours_value, "benchmark": benchmark, "step": step})

    # Primary category: the strongest single ranking factor for the 3-pack.
    leader_types = Counter(p.get("primaryType") for p in top3 if p.get("primaryType"))
    our_type = ours.get("primaryType")
    our_label = ours.get("primaryTypeDisplayName") or (nice_type(our_type) if our_type else "None")
    if leader_types:
        best, n = leader_types.most_common(1)[0]
        label = next((p.get("primaryTypeDisplayName") for p in top3 if p.get("primaryType") == best), None) or nice_type(best)
        if our_type == best:
            add("Primary category", OK, our_label, f"{n} of top 3 use {label}")
        else:
            add("Primary category", GAP, our_label, f"{n} of top 3 use {label}",
                f"If {label} truly describes our main service, make it the primary category in Google Business Profile.")

    # Secondary types the leaders share and we lack.
    our_types = set(ours.get("types", []))
    generic = {"point_of_interest", "establishment", "service", "general_contractor"} | {our_type}
    common = Counter(t for p in top3 for t in set(p.get("types", [])) if t not in generic)
    missing = [t for t, n in common.most_common() if n >= 2 and t not in our_types]
    if missing:
        names = ", ".join(nice_type(t) for t in missing[:5])
        add("Secondary categories", GAP, ", ".join(nice_type(t) for t in sorted(our_types - generic)) or "None",
            f"At least 2 of top 3 have: {names}",
            "Add the ones that match services we actually offer. Google's place types are close to, not identical to, "
            "Business Profile categories, so pick the nearest real category.")
    elif common:
        add("Secondary categories", OK, "Covers what the top 3 share", "")

    # Reviews: volume and rating against the top 3.
    reviews = ours.get("userRatingCount") or 0
    bar = _median([p.get("userRatingCount") or 0 for p in top3])
    if bar is not None:
        if reviews >= bar:
            add("Review count", OK, reviews, f"Top 3 median {bar:g}")
        else:
            add("Review count", GAP, reviews, f"Top 3 median {bar:g}",
                f"About {int(bar - reviews)} more reviews to reach the top-3 median. Ask every happy customer, every job. "
                "Never buy, filter or incentivize reviews.")
    rating = ours.get("rating")
    bar = _median([p.get("rating") for p in top3])
    if bar is not None:
        if rating is not None and rating >= bar - 0.1:
            add("Rating", OK, rating, f"Top 3 median {bar:g}")
        else:
            add("Rating", GAP, rating if rating is not None else "No reviews", f"Top 3 median {bar:g}",
                "Read the lower reviews for a pattern to fix in the service itself, and reply to each one.")

    # Profile completeness: fields the leaders fill in.
    for name, key, step in (
            ("Website on profile", "websiteUri", "Link the profile to the matching site or service-area page."),
            ("Phone on profile", "nationalPhoneNumber", "Add a tracked local number we own."),
            ("Hours on profile", "regularOpeningHours", "Add real opening hours, including emergency hours if we offer them.")):
        has, total = _share(top10, lambda p, k=key: bool(p.get(k)))
        benchmark = f"{has} of top {total} have it" if total else ""
        if ours.get(key):
            add(name, OK, "Yes", benchmark)
        else:
            add(name, GAP, "Missing", benchmark, step)

    status = ours.get("businessStatus")
    if status and status != "OPERATIONAL":
        add("Business status", GAP, status.replace("_", " ").lower(), "", "Fix the status in Google Business Profile.")

    checks.sort(key=lambda c: c["status"] != GAP)
    return checks


LATER = [
    "Review replies and how fast new reviews come in (DataForSEO for competitors, Business Profile API for us)",
    "Post frequency and photo count",
    "Services, products and attributes listed",
    "Which keywords our site and theirs rank for (keyword phase)",
]
