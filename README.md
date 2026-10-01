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
python3 -m pytest -q
```

Research quality depends on the session's network access. With limited
access, research runs through web search only. **Full** network access lets
the researcher also read business websites, BBB and public license records.
