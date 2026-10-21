"""Keyword research through DataForSEO's Google Ads keyword data (licensed
Keyword Planner data: volume, CPC, competition, 12 months of history).

Built from DataForSEO's documented request and response format; check the
first live call against it."""
import httpx

from . import config

BASE = "https://api.dataforseo.com/v3"


class KeywordError(Exception):
    pass


class KeywordClient:
    def __init__(self, login=None, password=None, transport=None):
        self.auth = (login if login is not None else config.DATAFORSEO_LOGIN,
                     password if password is not None else config.DATAFORSEO_PASSWORD)
        self.http = httpx.Client(base_url=BASE, timeout=60, auth=self.auth, transport=transport)

    @property
    def configured(self):
        return all(self.auth)

    def ideas(self, seeds, location="United States"):
        """Related keywords for up to 20 seed terms, with volume, CPC, competition and monthly history."""
        if not self.configured:
            raise KeywordError("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD are not set.")
        task = {"keywords": seeds[:20], "location_name": location, "language_code": "en"}
        resp = self.http.post("/keywords_data/google_ads/keywords_for_keywords/live", json=[task])
        if resp.status_code != 200:
            raise KeywordError(f"DataForSEO returned HTTP {resp.status_code}.")
        body = resp.json()
        tasks = body.get("tasks") or [{}]
        if tasks[0].get("status_code") != 20000:
            raise KeywordError(f"DataForSEO: {tasks[0].get('status_message') or body.get('status_message')}")
        return [shape(k) for k in tasks[0].get("result") or []]


def shape(item):
    months = sorted(item.get("monthly_searches") or [], key=lambda m: (m["year"], m["month"]))
    return {
        "keyword": item.get("keyword", ""),
        "volume": item.get("search_volume"),
        "cpc": item.get("cpc"),
        "competition": (item.get("competition") or "").title(),
        "competition_index": item.get("competition_index"),
        "bid_low": item.get("low_top_of_page_bid"),
        "bid_high": item.get("high_top_of_page_bid"),
        "monthly": [m.get("search_volume") or 0 for m in months][-12:],
        "trend": trend(months),
    }


def trend(months):
    """Last 3 months against the 3 before them, as a percent change."""
    values = [m.get("search_volume") or 0 for m in months]
    if len(values) < 6 or sum(values[-6:-3]) == 0:
        return None
    return round((sum(values[-3:]) / sum(values[-6:-3]) - 1) * 100)


def sparkline(values, width=96, height=24):
    """SVG points for a small trend line."""
    if not values or max(values) == 0:
        return ""
    step = width / max(len(values) - 1, 1)
    top = max(values)
    return " ".join(f"{i * step:.1f},{height - (v / top) * (height - 2) - 1:.1f}" for i, v in enumerate(values))
