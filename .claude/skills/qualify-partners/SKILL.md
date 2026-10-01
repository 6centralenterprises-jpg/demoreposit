---
name: qualify-partners
description: Research and score an uploaded IGLeads export (or any list of local service businesses) to decide exactly who 6 Central Enterprises should message as a job partner. Use when the user uploads or points to a lead file and asks to qualify, score, research, vet or rank the leads, or asks who to message.
---

# Qualify partner leads

This turns a lead file into a ranked, sourced list of businesses worth
contacting. **This is a qualification tool only. Never message, email, DM or
call anyone.** The team does the outreach.

## 1. Find the file and protect it

- Uploaded files usually land in `/mnt/user-data/uploads/`. Otherwise use
  the path the user gives.
- **This repository is public.** Never commit lead files or anything under
  `runs/`, because `.gitignore` covers them. Never paste a whole lead list
  into a commit, PR or issue.
- Market: default **Chicago, IL** unless the user or the file says otherwise.
  Niche: the scoring is general. The niche is detected per business.

## 2. Prepare

```bash
pip install -q -r requirements.txt
python3 qualify.py prepare "<file>" --market "Chicago, IL"
```

This removes duplicates and sorts leads by research priority: location
match, niche match, real website, business email. It writes
`runs/<run>/batches/batch_NN.json`. Report the printed summary to the user.
If there are more than about 150 leads to research, offer `--limit N` to do
the strongest leads first, and say roughly how long a full run takes.

## 3. Research

For each batch, start a `partner-researcher` agent in the background. Run 4
at a time at most, and start the next batch as each finishes. Prompt
template:

> Research batch file `runs/<run>/batches/batch_NN.json`. Target market:
> Chicago, IL. Today's date: YYYY-MM-DD. Write one evidence file per lead
> to `runs/<run>/evidence/<lead_id>.json`, following your instructions
> exactly.

If `partner-researcher` isn't offered as an agent type (for example in a
session started before the file existed), use a `general-purpose` agent.
Start its prompt with: "You are acting as the partner-researcher agent. First
read `.claude/agents/partner-researcher.md` and follow it exactly."

Check progress with `python3 qualify.py status --run <run>`. Re-run any batch
that has missing leads. Interrupted runs resume, because finished evidence
files are kept.

## 4. Score and deliver

```bash
python3 qualify.py score --run <run> --out-dir /mnt/user-data/outputs
```

- Read the evidence warnings. A section without a source is scored as "not
  confirmed". If many leads have warnings, re-research those leads before
  delivering.
- Send the `.xlsx` with SendUserFile. Its tabs are **Who to Message**,
  **All Leads**, **Evidence**, **Partner Sheet** and **Summary**.
- Summarize in plain language:
  - the count for each verdict
  - the top 10 to message, with one reason each
  - every **HOLD** (Terell decides these)
  - every **DO NOT CONTACT** (license not verified)
  - the most common "To verify" gaps

## Verdicts

| Verdict | Meaning |
|---|---|
| MESSAGE | 7+ out of 10 with sources. Contact in rank order. |
| VERIFY | Under 7 so far, but could reach 7+ if the unconfirmed items check out. |
| HOLD | A sourced red flag. Ask Terell before anyone reaches out. |
| DO NOT CONTACT | License-required niche (pest control, plumbing or roofing in IL) without a verified active license. |
| SKIP | Duplicate, not a real business, not a service provider, out of area, or can't reach 7. |

## Network notes

If WebFetch reports `EGRESS_BLOCKED`, the environment's network policy is
limiting access. Research still works through WebSearch. Tell the user once
that Full network access in the environment settings allows deeper checks:
reading business websites, BBB, and city and state license records.
