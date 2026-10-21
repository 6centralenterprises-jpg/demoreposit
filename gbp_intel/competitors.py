"""Turning a competitor search into a table, a summary and a CSV."""
import csv
import io
from statistics import median
from urllib.parse import urlparse

CSV_COLUMNS = ["rank", "name", "ours", "primary_type", "rating", "reviews", "website", "phone",
               "status", "address", "maps_url", "place_id"]


def rows(results, ours):
    out = []
    for r in results:
        p = r["place"] or {}
        website = p.get("websiteUri", "")
        out.append({
            "rank": r["rank"],
            "place_id": r["place_id"],
            "expired": r["place"] is None,
            "ours": r["place_id"] in ours,
            "name": p.get("displayName", ""),
            "primary_type": p.get("primaryTypeDisplayName") or p.get("primaryType", ""),
            "rating": p.get("rating"),
            "reviews": p.get("userRatingCount") or 0,
            "website": website,
            "domain": urlparse(website).netloc.removeprefix("www.") if website else "",
            "phone": p.get("nationalPhoneNumber", ""),
            "status": p.get("businessStatus", ""),
            "address": p.get("formattedAddress", ""),
            "maps_url": p.get("googleMapsUri", ""),
        })
    return out


def summary(table):
    """What it takes to compete: the bar set by the top 3 and the whole list."""
    live = [r for r in table if not r["expired"]]
    if not live:
        return None
    top3 = live[:3]

    def med(items, key):
        values = [r[key] for r in items if r[key]]
        return round(median(values), 1) if values else None

    types = {}
    for r in live:
        if r["primary_type"]:
            types[r["primary_type"]] = types.get(r["primary_type"], 0) + 1
    return {
        "count": len(live),
        "top3_reviews": med(top3, "reviews"),
        "top3_rating": med(top3, "rating"),
        "all_reviews": med(live, "reviews"),
        "with_website": sum(1 for r in live if r["website"]),
        "top_types": sorted(types.items(), key=lambda kv: -kv[1])[:5],
        "ours": [r["rank"] for r in live if r["ours"]],
    }


def to_csv(table):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for r in table:
        writer.writerow({**r, "ours": "yes" if r["ours"] else ""})
    return buf.getvalue()
