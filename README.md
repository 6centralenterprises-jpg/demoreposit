# Partner Qualification Engine

*A 6 Central Enterprises shared-services tool*

Upload an IGLeads export (or any list of local service businesses). Claude
researches each business and returns a ranked, sourced list of **exactly who
to message** as a job partner. This tool only qualifies leads. It never
contacts anyone. Your team does the outreach.

## How to use it

1. In a Claude Code session on this repo, **attach the lead file to your
   message**. CSV, XLSX and JSON all work. Don't commit it to GitHub: this
   repository is public.
2. Say: *"Qualify these leads for Chicago, IL."* (Any market works.)
3. Claude runs the `qualify-partners` skill:
   - **prepare:** cleans the file, removes duplicates, guesses the niche and
     ranks leads by research priority.
   - **research:** `partner-researcher` agents check each business's
     website, Google, Yelp, Facebook and BBB reviews, complaints, insurance
     claims, licensing, service area, team size and recent activity. Every
     finding is saved with its source link.
   - **score:** the 10-point rubric below, with gates.
4. You get `partner_qualification.xlsx` with these tabs:

| Tab | What it's for |
|---|---|
| **Who to Message** | Ranked MESSAGE list: best contact, why they qualify, a true conversation opener |
| **All Leads** | Every lead with verdict, score, points per criterion and what's left to verify |
| **Evidence** | Every point with its finding and source URL, so anyone can audit a score |
| **Partner Sheet** | Paste-ready: Business, Niche, City, Email, Score, Status, Last contact date, Notes |
| **Summary** | Counts and how to read the report |

## The rubric (10 points)

| Area | Points | Criterion |
|---|---|---|
| Reputation | 2 | Rating 4.3+ with 15+ reviews (1 pt: 4.0+ with 5+) |
| Reputation | 1 | No unresolved complaints in the sources checked |
| Legitimacy | 1 | Confirmed real, active business (two sources agree) |
| Legitimacy | 1 | 2+ years in business, or a registered entity |
| Fit | 1 | Owner-run or 1–15 workers, not a chain |
| Fit | 1 | Serves the target market |
| Trust | 1 | Publicly states it is insured |
| Trust | 1 | Bonded, background-checked staff, certified or accredited |
| Responsiveness | 1 | Active in the last 90 days, or replies to reviews |

**We never guess.** A finding without a source URL scores 0 and is marked
"not confirmed". The scoring code enforces this, so it doesn't depend on the
researcher remembering to.

## Verdicts

| Verdict | Meaning |
|---|---|
| **MESSAGE** | 7+ out of 10. Contact in rank order. |
| **VERIFY** | Under 7 so far, but could reach 7+ if the unconfirmed items check out. The sheet lists what to check. |
| **HOLD** | Sourced red flag (complaints pattern, lawsuit, safety, misleading claims). Terell decides. |
| **DO NOT CONTACT** | Pest control, plumbing or roofing (Illinois) without a verified active state license. |
| **SKIP** | Duplicate, not a real business, not a service provider, out of area, or can't reach 7. |

## Full partner audits and custom emails

After qualifying, say *"Audit the best partners."* The `audit-partners`
skill digs into every MESSAGE partner (and near-misses if you ask):

| Section | What's in it | Source |
|---|---|---|
| **Google reputation** | Google rating (live map-pack reading when available), other platforms, what customers praise or complain about, review replies | Google results, web search |
| **SEO** | Ranking keywords, page-1 count, estimated visitors and their ad value, authority, linking sites, site health and top issues, where traffic really comes from | OpenRush |
| **Keywords** | Where they rank for the searches that bring paying customers, and the biggest searches they're missing | OpenRush + market demand list |
| **Competition** | Who owns Google's map pack and page 1 for the money searches, and where this partner stands | OpenRush live results |
| **Doing right / wrong** | 3–5 concrete, sourced points each | All of the above |
| **Custom email** | A draft in 6 Central's outreach standard, checked automatically | Written from the audit |

**Who's the best partner?** Each partner gets two scores:
- **Quality** (the 10-point rubric): can we trust them with our customers?
- **Need**: how much our jobs would matter to them. Need is high when
  they're hard to find online today.

The ideal partner does excellent work but is under-marketed. Businesses that
already own Google may not need our jobs, and they compete with our brands
for the same customers, so the report labels them clearly.

**Email checks:**
- under 120 words, including signature and opt-out
- says who we are
- paid jobs, with price agreed up front
- exactly one question
- uses a true, sourced fact
- no promises of volume, income or exclusivity, no size claims, no
  urgency, no jargon
- about an 8th-grade reading level

Drafts that fail are marked **Needs rewrite**. **Nothing is ever sent
automatically.** Every draft waits for Terell's approval.

**Cost:** about 15 OpenRush credits per niche for market research, plus
18–37 per partner with a website. Partners without a website cost 0. The
plan step shows the estimate before anything is spent.

Put your phone and mailing address for the signature in
`config/sender.json`. Copy `config/sender.example.json` to create it. It
stays out of git.

## Rules built in

- Business-facing information only. No owners' personal accounts or private
  lives.
- Free-mail addresses (Gmail and similar) are allowed only when publicly
  listed as the business contact. The sheet shows where each email came
  from.
- Lead files and results stay in `runs/`, which is never committed.

## Make it smarter over time

Add an outcome to each partner in your sheet: signed, job quality, dropped
off. After a few months, compare outcomes to the scores and adjust the
weights in `partner_qualifier/rubric.py`. The rubric then becomes 6
Central's own partner-quality model, reusable for every niche and city.

## Developer notes

```bash
pip install -r requirements.txt
python3 qualify.py prepare leads.csv --market "Chicago, IL"   # → runs/<run>/batches/
python3 qualify.py status --run <run>
python3 qualify.py score  --run <run> --out-dir /mnt/user-data/outputs
python3 qualify.py audit-plan   --run <run> --top 20        # prints credit estimate
python3 qualify.py audit-report --run <run> --out-dir /mnt/user-data/outputs
python3 -m pytest -q
```

Research quality depends on the session's network access. With limited
access, research runs through web search only. **Full** network access lets
the researcher also read business websites, BBB and public license records.

---

# GBP Opportunity Scout

*A daily 6 Central Enterprises research agent*

Every morning before 8 AM Central, the scout finds where demand for
home-based service businesses is **rising** and **which cities nationwide**
have Google map packs open enough for a real local business to win. It publishes the brief
to a private dashboard and sends a short summary by push and email.

## What it checks each day

| Step | Tool | What it answers |
|---|---|---|
| Discovery | OpenRush `research_keywords` | What new searches are customers making in today's niches? |
| Screen | Semrush `phrase_these` (up to 45 keywords) | Volume, CPC (a proxy for job value), 12-month curve, difficulty |
| Deep dive | OpenRush `inspect_keyword` (top 5) | Is it really surging? Last 3 months vs the same 3 months last year, from 24 months of history |
| Map pack | OpenRush `inspect_serp`: Chicago daily + 3 rotating metros | Who holds the top 3 on Google Maps, and how many reviews they have |
| Signals | Web search (+ AccuWeather when available) | Freezes, storms, Google policy changes, news, each with a source |

Volume data refreshes monthly, so each weekday covers a different group:

| Day | Group |
|---|---|
| Mon | Water, restoration & plumbing |
| Tue | Mobile auto (tire, roadside, mechanic, detailing) |
| Wed | Outdoor & seasonal (tree, gutters, holiday lights, snow) |
| Thu | HVAC, energy & home upgrades |
| Fri | Home care & pets |
| Sat | Emerging & discovery |
| Sun | Weekly recap of the watchlist, with map packs re-checked |

## Markets

**Chicago** is checked every day. **34 large or fast-growing metros**
nationwide rotate, 3 a day, so every one is covered about every 11 days:
Houston, Dallas, Fort Worth, Austin, San Antonio, Phoenix, Atlanta,
Charlotte, Raleigh, Nashville, Orlando, Tampa, Jacksonville, Miami, Ocala,
Las Vegas, Denver, Salt Lake City, Boise, Indianapolis, Columbus, Kansas
City, St. Louis, Oklahoma City, Greenville, Charleston, Washington DC,
Philadelphia, New York, Los Angeles, Seattle, Detroit, Minneapolis and
Milwaukee.

The **Best markets so far** leaderboard ranks them by how open their map
packs are across every check. It firms up after a few weeks, once each
market has been checked across all business groups.

## Reading the brief

- **Score (0–100):** demand 25 + job value 20 + momentum 20 + map-pack
  openness 25 + home-based fit 10. Every part is shown.
- **Surging / Rising / Steady / Cooling:** +25% / +10% / flat / −15% or
  worse vs the same months last year. "(seasonal)" means only the 12-month
  curve was available, which can't tell a trend from a season.
- **Plays:** *Own it* (launch a real 6 Central service), *Partner & manage*
  (set up or manage real operators' profiles; they stay the owner),
  *Validate*, *Watch*.
- **Possibly ours:** a map-pack listing whose name matches a 6 Central
  brand marker. Confirm it is set up correctly.

## Guardrails

The scout never creates or edits a profile and never contacts anyone.
Every play assumes a real business that does the work from a real base.
Google bars lead-generation companies from Business Profiles, and
suspensions hurt the real businesses involved.

## Settings

Edit `config/gbp_scout.json` to change the home markets, the rotating
roster, niches, keywords, brand markers or budget. The daily cost is about
51 OpenRush credits and up to 450 Semrush API units (10 per keyword). Each
extra rotating metro per day adds about 4 OpenRush credits.

```bash
python3 scout.py plan    --date 2026-10-02
python3 scout.py batch   --date 2026-10-02
python3 scout.py screen  --date 2026-10-02
python3 scout.py build   --date 2026-10-02
python3 scout.py restore --date 2026-10-03 --html <published brief>
```

Run data stays in `runs/gbp/`, which is never committed. This repository
is public, and the strategy should stay private.
