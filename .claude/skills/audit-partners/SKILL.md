---
name: audit-partners
description: Full audit of qualified partner businesses for 6 Central Enterprises, covering Google reputation, SEO, keyword research, competition and what each does right and wrong, plus a custom outreach email draft per partner. Use after qualify-partners, when the user asks to dive deeper into partners, audit them, compare them, find the best partners, or write custom emails.
---

# Audit partners

This runs on a qualification run that already has `results.json` (see the
`qualify-partners` skill). It audits the best partners in depth and drafts
one custom email each. **Never send emails.** Drafts go to Terell for
approval, and the team sends them within the 25-per-week limit.

## Why "need" matters

The best partners do excellent work but are **hard to find online**: strong
reviews, weak search presence. They have room for more customers and the
most reason to say yes. Businesses that already dominate Google may not
need our jobs, and they compete with 6 Central's own brands for the same
customers. The audit book ranks partners by fit:
- **Ideal partner:** quality 7+ and need 6+
- **Good partner:** quality 7+ and need 4–5
- **Strong and visible:** quality 7+ and need 0–3
- **Vet first:** quality under 7

## Steps

1. **Plan:**
   ```bash
   python3 qualify.py audit-plan --run <run> --top 20   # add --include-verify for near-misses
   ```
   It prints the partners, the markets still to research and an **OpenRush
   credit estimate**. **Show the estimate and get the user's OK before
   spending credits.** Partners without a website cost 0 credits.

2. **Market research.** Do this once per niche listed under "Market
   research needed". Start a `market-analyst` agent with the niche, the
   market, today's date and the output path
   `runs/<run>/market/<niche-slug>.json` (slug: lowercase, hyphens).

3. **Partner audits.** For each `runs/<run>/audit_batches/batch_NN.json`,
   start a `partner-auditor` agent in the background, 3 at a time at most.
   Give it the batch path, run id and today's date. If those agent types
   aren't offered, use `general-purpose` agents told to read and follow
   `.claude/agents/<name>.md` exactly.

4. **Report:**
   ```bash
   python3 qualify.py audit-report --run <run> --out-dir /mnt/user-data/outputs
   ```
   This builds two files:
   - `partner_audits.xlsx`, with tabs Best Partners, SEO & Keywords,
     Market Leaders, Demand Keywords, Right & Wrong and Email Drafts
   - `partner_audit_book.md`, the full audit and email for each partner,
     in rank order
   
   Emails that fail a rule check are marked **Needs rewrite**. Reasons
   include over 120 words, no price up front, more than one question, an
   unsourced fact or a risky claim. Send those back to a `partner-auditor`
   to rewrite, then re-run the report.

5. **Deliver.** Send both files with SendUserFile, then summarize:
   - the top partners and why
   - the market leaders to know about
   - emails ready for approval versus needing a rewrite
   - credits used
   
   Remind Terell that nothing has been sent.

6. **Stage the drafts (when AgentMail is reachable).** Run
   `python3 qualify.py drafts --run <run>` and show the list. With Terell's
   yes, run it with `--apply`. Then he approves by lead id, and
   `python3 qualify.py send --run <run> <ids>` shows the plan. Only add
   `--apply` after he confirms those exact ids. Never send an id he didn't name.

## Sender details

Emails get this signature: name, title and company, phone and mailing
address, then the required opt-out line. The details come from
`config/sender.json`, which is gitignored. Copy `config/sender.example.json`
to create it. Until it exists, the drafts show `[YOUR PHONE]` and
`[YOUR MAILING ADDRESS]`.

## Opt-outs

When anyone replies "no thanks", asks to stop, or hard-bounces, run
`python3 qualify.py optout <their email> --reason "<what they said>" --source "<reply date>"`
right away. It blocks them in AgentMail for both send and reply, and every
future `prepare` marks them DO NOT CONTACT. Do this without waiting for
approval: it's the promise the opt-out line makes. Never use a bare free-mail
domain (gmail.com and similar); the command refuses it.
