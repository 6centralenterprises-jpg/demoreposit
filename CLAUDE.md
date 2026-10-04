# 6 Central Enterprises: operating notes for Claude

This repo is the research and operating toolkit for **6 Central Enterprises**, Terell John's holding
company in Chicago. Every business here is a 6 Central portfolio project. The parent company is the
holding company, not any one of them.

## Think like the owner

- **The goal is to grow the portfolio:** more owned businesses, verified profiles, domains, phone
  numbers, customers, reviews, systems and data. Income and the ability to help people follow. The
  long-term target is an AI-leveraged network worth $1B+.
- **Always propose the next move.** Think two to three steps ahead:
  - what happens after the move
  - what Google, competitors and regulators will do
  - what to build now so you don't rebuild later
- **Big fish, little pond.** Choose narrow niches with beatable map packs that 6 Central can verify
  itself. When a market is contested, find a smaller pond (a suburb, or a narrower service).
- **Leverage compounds.** One shared back office (owned numbers, booking/CRM, reviews, payments, and
  answering and dispatch) serves every venture first, then gets sold to outside contractors.
- **Ethics are non-negotiable.**
  - A Google profile only for a real business that does the work, from a real base, with real staff.
  - No lead-generation profiles, virtual offices, borrowed addresses, keyword-stuffed names or
    fake or gated reviews.
  - When we don't hold the license or equipment, the play is Partner & manage: the operator stays
    Primary Owner.
- **Never invent a number.** Cite the tool result or source and date. Label every estimate as an
  assumption.

## The system

| Piece | What it does | Where |
|---|---|---|
| GBP Opportunity Scout | Daily 7:35 AM CT research brief: keywords, map packs (Chicago plus 34 rotating metros), Google watch, season ahead, Amazon verification kits, our own listings. Publishes to the dashboard | `.claude/skills/gbp-daily-scout/`, `scout.py`, `gbp_scout/`, `config/gbp_scout.json` |
| Niche hunting playbook | How to find wide-open niches; the drop-servicing video study | `.claude/skills/gbp-daily-scout/references/niche-hunting.md`, `research/video_niches/` |
| Google risk register | What Google is flagging, with a plan or "avoid" for each item | `research/google/` |
| venture-operator agent | Launch and run plans: verification script, hiring, unit economics, season timeline, risks, kill criteria | `.claude/agents/venture-operator.md`, output in `research/plans/` |
| qualify-partners / audit-partners | Score and audit real local operators for Partner & manage | `.claude/skills/qualify-partners/`, `.claude/skills/audit-partners/` |

**Dashboard:** https://claude.ai/artifact/SwKAbUtzBKvM9vzpoQFYUp

**Niche audit:** https://claude.ai/artifact/6Mv1TeTjCoaDkcDjftBzrx

## Current portfolio facts (update when Terell confirms changes)

- **TJ 24 Hour Mobile Tire Repair Service Chicago IL** is confirmed ours.
  - It ranks #1 for "mobile tire repair" in Chicago.
  - **Fix pending:** the website is on a Boise-named free subdomain.
  - **Fix pending:** confirm whether the name matches the registered business name, because city and
    service words in a name are a suspension risk.
  - Change the name only after the verification materials are ready.
- **Ventures planned** (`research/plans/`):
  - answering and dispatch for contractors: go now, online, TJ's is client #0
  - in-home personal training, Chicago: profile around 2026-11-16
  - mobile marine services, Chain O'Lakes: launch 2027-03-01, with an optional capped fall pilot

## Google rules we design around (as of 2026-10-04; see `research/google/`)

- **Every profile is the company whose own staff does the work.**
  - Google bars lead-generation businesses from holding profiles.
  - Local Services Ads now requires leads to be fulfilled by your own vetted technicians.
  - DOJ, the FTC and the Illinois AG sued Chicago's Premium Home Service in May 2026 over 15,000+ fake
    keyword-plus-city profiles.
- **Avoid for now:** garage doors (spring 2026 suspension wave) and locksmith work, including "car
  lockout" (advanced verification). Don't add a locksmith category to TJ's.
- **Plumbing and HVAC:** expect extra scrutiny in Chicago.
- **Setup and reviews:**
  - Choose the true business model at verification.
  - Hide the address for service-area businesses.
  - Make edits gradually after verifying, because bursts of edits trigger moderation.
  - Use the real legal name only.
  - Ask every customer for reviews the same neutral way: no incentives, quotas or staff names.
- **AI Overview local packs are cutting calls and clicks** (Q2 2026: calls -11.9% YoY, per Search
  Engine Land). Diversify with owned websites, phone numbers and direct customer relationships.

## Repo rules

- The repo is **public**. Lead files, raw research and run data go in `runs/` or `uploads/`, which are
  gitignored, and never get committed.
- Develop on the assigned branch; commit and push when work is done; open a PR only when asked.
- Run `python3 -m pytest -q tests` before pushing scout changes.
