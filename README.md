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

## Email allow and block lists (AgentMail)

Organization-wide lists keep outreach clean and honor every opt-out:

| Type, direction | What goes on it | How it's kept up to date |
|---|---|---|
| block, send | Anyone who asked not to be contacted, plus hard bounces | `qualify.py optout` adds them right away |
| block, reply | The same people, so no agent writes back to them | Same command |
| allow, receive | Our own domains and addresses | `config/email_lists.json` |
| block, receive | Spam senders | `config/email_lists.json` |
| allow, send | Optional: only MESSAGE partners from a scored run | Off until `restrict_send_to_approved_partners` is true |

```bash
cp config/email_lists.example.json config/email_lists.json   # add your domains and addresses
python3 qualify.py lists                 # shows what would change
python3 qualify.py lists --apply         # adds the missing entries
python3 qualify.py optout someone@biz.com --reason "Replied no thanks" --source "reply 2026-10-02"
```

- `lists` only ever **adds**. Entries on AgentMail that aren't in the config
  are listed and left alone.
- A bare free-mail domain (`gmail.com`, `yahoo.com`...) is refused anywhere:
  it would match every partner who uses Gmail. Use full addresses.
- Every `prepare` checks new leads against the opt-out list, so someone who
  opted out is never researched or messaged again.
- Needs `AGENTMAIL_API_KEY` in the environment and network access to
  `api.agentmail.to`. The key is read by the SDK and never printed.
- `config/email_lists.json` and `outreach/` (the local opt-out file) are
  gitignored. AgentMail's send block list is the lasting copy of opt-outs.
- On an unverified AgentMail organization, sending is limited to the send
  allow list, so check the account is verified before relying on outreach.

## Running outreach (AgentMail)

Partner outreach goes out from `terell@6cpartners.com` only. The brand
domains are for customers and never send cold email. The inbox map, daily
caps and sending hours are in `config/outreach.json`.

```bash
python3 qualify.py inboxes --apply                    # create the inbox map
python3 qualify.py drafts --run <run> --apply         # checked emails -> AgentMail drafts
python3 qualify.py send --run <run> L0004 L0011       # preview; add --apply to send
python3 qualify.py triage --apply                     # sort replies; block opt-outs and bounces
```

- **You approve every first email.** `send` only sends the lead ids you name.
  Without `--apply` it shows what would happen.
- `drafts` skips anyone not MESSAGE, any email that failed a check, unlisted
  free-mail addresses, opt-outs, and signatures still showing placeholders.
  It says why for each one, and never drafts the same lead twice.
- `send` re-checks the opt-out list, keeps to the daily cap (10 a day for
  the first 14 days, then 30), and sends only Monday to Friday, 9am to 4pm
  Chicago time. Outside those hours it schedules for the next opening. Set
  `warmup_start` to your first send date.
- `triage` sorts each new reply into needs Terell, opt-out, bounce,
  auto-reply or unclear bounce. Opt-outs and bounces are blocked right away.
  It only checks the new reply, not the quoted email below it.
- Drafts, labels and sent mail live in AgentMail (`6c-*` labels), so a new
  session picks up where the last one stopped.

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
python3 qualify.py lists [--run <run>] [--apply]
python3 qualify.py optout <email> --reason "..."
python3 -m pytest -q
```

Research quality depends on the session's network access. With limited
access, research runs through web search only. **Full** network access lets
the researcher also read business websites, BBB and public license records.
