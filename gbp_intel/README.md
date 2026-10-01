# 6 Central Local Intel

*A 6 Central Enterprises shared-services tool*

Our own version of what GMB Crush and GMB Everywhere do: track our sites and
Google Business Profiles, look up competitors, find profile gaps and research
keywords. It runs only on licensed data (Google's official APIs and paid data
vendors). It never scrapes Google pages, and it never creates listings,
reviews or anything else on anyone's behalf.

## Status

| Phase | What | State |
|---|---|---|
| 1 | **Our assets**: add or upload our websites and Maps links, match each to its Google profile | Built |
| 2 | Competitors: top businesses for a service + city, with categories and review stats | Next |
| 3 | Gap analysis: our profile scored against the top 3 and top 10 | Planned |
| 4 | Keywords: volume, trend, CPC, competition | Planned |
| Later | Geo-grid heatmaps and Teleport | Planned |

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env          # then add your Google Maps API key
python3 -m gbp_intel          # open http://localhost:8000
python3 -m pytest -q
```

Without a key the app still works for adding and uploading assets; matching
to Google profiles needs the key.

### Getting the Google key

1. In [Google Cloud Console](https://console.cloud.google.com/), create a
   project and turn on billing.
2. Enable **Places API (New)**.
3. Create an API key, restrict it to Places API (New), and put it in `.env`.

## Uploading our URLs

Paste one URL per line (websites and Google Maps links both work), or upload
a CSV with headers like `name, project, city, website, maps_url, notes`.
Duplicates (same website or Maps link) are skipped. Each asset then gets a
"Find this business on Google" step where you pick the right profile.

## Data rules we follow

- Google's terms allow keeping a **Place ID** forever, but other Places data
  only for **30 days**. The app stores profile data with its fetch date and
  deletes anything older than 30 days on startup. Refresh to pull it again.
- Matching uses Text Search with Pro-tier fields (about $32 per 1,000 after
  5,000 free a month). Refreshing a profile uses Place Details with rating,
  hours, phone and website (Enterprise tier, about $20 per 1,000 after 1,000
  free a month). Prices as of October 2026; check Google's pricing page.
- `.env` and `data/` are git-ignored. This repository is public, so keys and
  our database never get committed.
