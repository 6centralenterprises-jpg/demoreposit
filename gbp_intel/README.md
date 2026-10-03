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
| 2 | **Competitors**: Google's top 20 for a service + city, with rating, reviews, website, phone, a "what it takes" summary and CSV export | Built (categories and full review stats come with DataForSEO) |
| 3 | **Gap analysis**: our profile scored against the top 3 and top 10, with a plain next step per gap | Built (posts, photos and review replies come with the Business Profile API and DataForSEO) |
| 4 | Keywords: volume, trend, CPC, competition | Next |
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

## Looking up competitors

Enter a service and a city. The app asks Google for "<service> in <city>"
and shows up to 20 businesses in Google's order, with our own assets
highlighted. The order is Google's relevance ranking for that search, which
is close to, but not the same as, the Maps 3-pack a customer sees from a
specific spot (that needs the geo-grid feature, planned later).

The summary shows the bar to beat: median reviews and rating of the top 3,
how many have websites, the most common primary types and where we show up.
"Download CSV" exports the table.

## Gap analysis

Open a matched asset and compare it with a saved competitor search, or run
a new one for its city. The checks:

| Check | Compared with |
|---|---|
| Primary category | The most common primary type in the top 3 |
| Secondary categories | Types at least 2 of the top 3 share that we lack |
| Review count | Top 3 median |
| Rating | Top 3 median (within 0.1 counts as even) |
| Website, phone, hours on profile | How many of the top 10 fill them in |
| Business status | Anything other than open is flagged |

Gaps come first, each with a next step. The tool never suggests buying,
filtering or incentivizing reviews, stuffing keywords into the business
name, or listing services we don't offer.

## Data rules we follow

- Google's terms allow keeping a **Place ID** forever, but other Places data
  only for **30 days**. The app stores profile data with its fetch date and
  deletes anything older than 30 days on startup. Competitor searches keep
  their ranked Place IDs; the details clear after 30 days until you run the
  search again. Refresh to pull it again.
- Matching uses Text Search with Pro-tier fields (about $32 per 1,000 after
  5,000 free a month). Refreshing a profile uses Place Details with rating,
  hours, phone and website (Enterprise tier, about $20 per 1,000 after 1,000
  free a month). A competitor search is one Text Search call at the
  Enterprise tier (about $35 per 1,000 after 1,000 free). Prices as of October 2026; check Google's pricing page.
- `.env` and `data/` are git-ignored. This repository is public, so keys and
  our database never get committed.
