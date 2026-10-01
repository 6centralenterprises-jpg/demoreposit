"""Google Places API (New) client. Official API only, called within its terms.

Text Search is used with Pro-tier fields to find candidates; Place Details
pulls the fuller profile for assets we own. See the cost notes in README.
"""
import httpx

from . import config

BASE = "https://places.googleapis.com/v1"
SEARCH_FIELDS = ["id", "displayName", "formattedAddress", "primaryType", "primaryTypeDisplayName",
                 "googleMapsUri"]
DETAIL_FIELDS = SEARCH_FIELDS + ["types", "websiteUri", "nationalPhoneNumber", "rating", "userRatingCount",
                                 "regularOpeningHours", "businessStatus"]


class PlacesError(Exception):
    pass


class PlacesClient:
    def __init__(self, api_key=None, transport=None):
        self.api_key = api_key if api_key is not None else config.GOOGLE_MAPS_API_KEY
        self.http = httpx.Client(base_url=BASE, timeout=20, transport=transport)

    @property
    def configured(self):
        return bool(self.api_key)

    def _call(self, method, path, fields, **kwargs):
        if not self.configured:
            raise PlacesError("GOOGLE_MAPS_API_KEY is not set.")
        headers = {"X-Goog-Api-Key": self.api_key, "X-Goog-FieldMask": ",".join(fields)}
        resp = self.http.request(method, path, headers=headers, **kwargs)
        if resp.status_code != 200:
            try:
                message = resp.json()["error"]["message"]
            except Exception:
                message = resp.text[:200]
            raise PlacesError(f"Google Places returned {resp.status_code}: {message}")
        return resp.json()

    def search(self, text, limit=5):
        data = self._call("POST", "/places:searchText", [f"places.{f}" for f in SEARCH_FIELDS],
                          json={"textQuery": text, "pageSize": limit})
        return [flatten(p) for p in data.get("places", [])]

    def details(self, place_id):
        return flatten(self._call("GET", f"/places/{place_id}", DETAIL_FIELDS))


def flatten(place):
    """Unwrap Google's {text: ...} objects so templates stay simple."""
    out = dict(place)
    for key in ("displayName", "primaryTypeDisplayName"):
        if isinstance(out.get(key), dict):
            out[key] = out[key].get("text", "")
    hours = out.get("regularOpeningHours")
    if isinstance(hours, dict):
        out["regularOpeningHours"] = hours.get("weekdayDescriptions", [])
    return out
