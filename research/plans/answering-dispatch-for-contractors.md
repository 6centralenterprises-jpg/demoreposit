# Answering & after-hours dispatch for home-service contractors

Slug `answering-dispatch-for-contractors`. Based in Chicago, sold nationally online. TJ's Nationwide Roadside is the first client.
Plan date: 2026-10-04. Raw pulls: `runs/plans/answering-dispatch-for-contractors/` (gitignored).
Labels: **[S]** = sourced (see §9). **Assumption** = an estimate, with what it rests on.

---

## 1. Verdict

**Go now, as an AI-plus-human hybrid sold online, with no Google profile yet.** Contractors shop for answering services in early fall: "after hours answering service" peaked at 3,600/mo in Sep 2025 [S: OpenRush]. Winter emergency calls peak Jan–Feb: "emergency plumber near me" hit 246,000 in Feb 2026 [S: OpenRush]. TJ's dispatch can prove the service live before that peak.

---

## 2. Verification readiness: **Hard** (deferred to Phase 2)

| Item | Finding |
|---|---|
| Why it's hard | "A business must make in-person contact with customers during its stated hours." Online-only businesses are ineligible [S: Google 13763036]. A rented mailing address you don't work from (a virtual office) is ineligible. A co-working office qualifies only with "clear signage", customers received there during business hours, and your own staff on site [S: Google 3038177]. |
| Profile type | **Storefront with the address shown.** An answering service doesn't travel to customers, so it isn't a service-area business (6 Central niche study, OpenRush/Semrush, 2026-10-04; `research/video_niches/licensing.md`). |
| Launch decision | Sell through the website, organic search, partner lists and ads only. Open the Google profile only when a staffed, signed dispatch office exists (Phase 2, trigger in §7). |
| Prize when ready | Chicago "answering service" map pack: the top 3 have **1, 1 and 15** reviews. "call center": **5, 9, 1** (6 Central niche study, OpenRush/Semrush, 2026-10-04). |

### What's missing today, and what it costs

| Missing | Cost |
|---|---|
| A staffed office with signage that customers can visit | Chicago 2-person suite: from $298/mo, city median $610/mo; private offices "typically start at $500 per month" [S: Workbox] |
| Permanent exterior sign with the exact business name | **Assumption** $300–800 (typical small fabricated sign; get a quote) |
| Staff on site during every stated hour | Dispatcher payroll (§3). Publish only the hours someone is really there. |
| Lease or utility bill, client invoice and business license, all in the business name | Lease: above. Business license fee: not sourced; check with the City of Chicago (BACP) before Phase 2. |
| Branded shirts and business cards | Already on the scout's kit list (`config/gbp_scout.json` → `verification.common_items`). Prices not pulled. |

### The 60–120 second, one-take video script (Phase 2 office only)

Record live in the Business Profile app, in one continuous take with no edits. Google checks three proofs: location, that the business exists, and that you manage it [S: Google 14271705].

| Time | Camera | Say |
|---|---|---|
| 0:00–0:15 | **Location.** Start at the nearest corner street sign, pan to the building number, then hold on the permanent exterior sign with the exact business name. | "This is [Business Name] at [street address], Chicago. Here's the cross street and our sign." |
| 0:15–0:30 | **Management.** Unlock the office door with your own key and walk in. Show the posted hours sign and the client visit desk. | "I'm Terell John, the owner. I'm unlocking our dispatch office. Clients visit us here during these hours." |
| 0:30–0:60 | **Exists.** Dispatcher at a desk in a branded shirt and headset. Wall screen showing the live call queue under the business name. Business cards on the desk. | "This is our dispatch floor. [Name] is on shift now, handling after-hours calls for our contractor clients." |
| 0:60–1:30 | **Management.** Log into the dispatch console's admin account showing the business name. Then show three documents with the same name and address: a client invoice, the office lease or a utility bill, and the business license on the wall. | "Here's our admin account, a client invoice, our lease and our city business license. Every name and address matches this profile." |
| 1:30–1:45 | Walk back out and finish on the sign and the street. | "That's [Business Name], open [hours]." |

**What would get it rejected, and how to avoid that:**
- A virtual office, or a co-working desk without a sign or our own staff. **Fix:** a real unit with our own staff [S: Google 3038177].
- An unattended office, or published hours with nobody there. **Fix:** list only the staffed hours.
- Keyword stuffing, e.g. "24 Hour Answering Service Chicago". **Fix:** use the real brand name only. Names must not carry marketing taglines [S: Google 3038177; `config/gbp_scout.json` playbook].
- Using TJ's address or a home address, or documents whose name doesn't match the profile.
- An edited or spliced video, or one shorter than 1 minute. Google suggests 1–2 minutes; one guide says videos under 30 seconds fail [S: Google 14271705; Wiremo].

---

## 3. Who does the work

### Choosing the model: build vs white-label human vs AI + human hybrid

| Model | Cost basis | For | Against | Call |
|---|---|---|---|---|
| **Build: in-house human agents 24/7** | Covering every after-hours slot is 118 hrs/wk: weeknights 6pm–8am plus weekends. 118 × $17.05 [S: Indeed/Chicago min wage] × 1.15 burden (**Assumption**: FICA 7.65% plus UI, workers' comp and paid leave) ≈ **$10,000/mo for one seat** | Quality and control; makes the Phase 2 office (and the Google profile) possible | The fixed floor needs ~29 clients at $349 contribution each just to cover one seat | **Not now** |
| **White-label human answering (wholesale partner)** | Wholesale terms aren't published. VoiceNation's partner page now redirects to Moneypenny [S]. Retail ceilings: MAP $1.30–1.43/min effective [S], PATLive $1.52–1.98/min plus $1.79–2.99 overage [S] | No fixed cost; 24/7 from day one | Thin margin. **Assumption:** about $1/min wholesale against a $1.75/min sale price. Message-taking only, no real dispatch, and quality we don't control. | **Use only as overflow for cold-snap surges** |
| **AI + human hybrid** | AI front line through the AI Front Desk white-label program at **$54.99 per receptionist wholesale** [S]. Human dispatchers only in peak windows. | 24/7 coverage at low cost; humans handle the high-value emergency calls; lets us price under human-only rivals | AI can mishandle an emergency; Illinois recording-consent and biometric-privacy (BIPA) exposure; dependence on one vendor | **Go** |

How the hybrid works: AI answers every after-hours call. It books routine work into the contractor's own software and texts a job ticket. Emergencies (no heat, active leak, stranded driver, water loss) go to a live 6 Central dispatcher during staffed windows. Outside those windows, the AI calls the client's on-call tech directly, then the backup tech, then the owner. The case stays open until a tech confirms and the customer gets an ETA text. That loop is the product. A message alone is not.

### Roles

| Role | Hire / contractor / partner | Where to find them | Pay (sourced) | License / caution |
|---|---|---|---|---|
| **1. Lead evening dispatcher: first hire** (about 30 hrs/wk across evenings and weekends; also runs TJ's dispatch) | **W-2 hire**, Chicago | Indeed; poach from local answering services and trade dispatch desks | Roto-Rooter evening dispatcher, Lombard IL: **$19–21/hr**. Transdev dispatcher, Tinley Park: **$18–20.50/hr**. Johnstone Supply HVAC call center rep, Crestwood: **$22–26/hr** [S: Indeed]. **Plan $21/hr.** | No license needed. Do HIPAA training only if we ever take medical clients (we won't; see §8). |
| **2. Part-time call agents** (weekends, overnight surge) | **W-2 part-time**, Chicago or remote | Indeed. Excel Answering Service (Chicago) is hiring at this rate, so it is the local wage benchmark. | Excel Answering Service, Chicago PT bilingual operator: **$17.05/hr**. Chicago minimum wage has been **$17.05** since Jul 1, 2026 [S]. Remote: AnswerNet **$15–16/hr**; Peaden home-services remote dispatcher **$18–25/hr**; towing remote dispatcher **from $16/hr** [S: Indeed]. | Remote agents in other states need employer registration in those states. Pay a bilingual premium; Spanish is billable (Smith.ai charges $1.00/call for a Spanish line [S]). |
| **3. Overnight AI layer** | **Vendor/partner** (white-label) | AI Front Desk reseller program | $54.99 per receptionist wholesale [S]; resellers commonly charge $250–500+/mo [S, vendor-reported] | Pick a vendor that **does not build voiceprints** and contracts to that (BIPA, §7). |
| **4. Surge overflow (human)** | **Partner** | Chicago map-pack operators: Excel Answering Service (S Pulaski Rd, since 1989 [S]) and Unicom Teleservices (15 reviews) | Quote only. Retail benchmarks above. | Get a written SLA and data-handling terms. |
| **5. Supervisor / QA** (at ~20 clients) | W-2 hire | Indeed | Home Comfort Services customer care manager, Des Plaines: **$60–68k**. Dental call center manager, Villa Park: **$50–60k** [S: Indeed] | Not needed in the first 90 days. |
| **6. Sales** | Terell first | Partner lists from `qualify-partners` | Commission rep later | **Classification caution:** Illinois unemployment law presumes a worker is an employee unless all three parts of the ABC test are met (820 ILCS 405/212) [S]. Answering calls is 6 Central's own business, so agents fail prong B. **Agents must be W-2, never 1099.** |

---

## 4. Unit economics

### Competitor prices (what contractors compare us to)

| Provider | Plan → effective rate | Type |
|---|---|---|
| MAP Communications | $49 + $1.37/min PAYG; $179/125 min; $339/250; $649/500 → **$1.30–1.43/min** [S] | Human |
| PATLive | $99/50 min … $759/500 → **$1.52–1.98/min**; overage $1.79–2.99 [S] | Human |
| Posh | $65 (0 min, $2.30/min) … $420/200 … $975/500 → **$1.95–2.60/min** [S] | Human |
| AnswerForce (home services) | $349/200 min + $75 setup; $389/300; $669/500; overage $1.85–2.00 [S, third-party rate card] | Human |
| Ruby | $250/50 min … $1,725/500 → **$3.45–5.00/min** [S] | Human |
| Smith.ai | $300/30 calls; $810/90; $2,100/300 → **$7–10/call**; add-ons $0.25–1.50/call [S] | Human + AI |
| Upfirst (ranks #1 for "after hours answering service") | $24.95/30 calls … $299/600 → **$0.50–0.83/call** [S] | AI only |
| Trillet, OnCrew | "From $49/mo" [S: SERP snippets] | AI only |
| Jobber AI Receptionist; Housecall Pro CSR AI; ServiceTitan Voice Agent | Built into the contractor's own software. Jobber and Housecall Pro don't publish the price on the pages fetched; ServiceTitan's is in early access [S] | AI, bundled |

### Proposed offer (**Assumption**: priced between AnswerForce $349/200 min and PATLive $479/300 min)

| Tier | Price | Includes |
|---|---|---|
| Night Watch | $199/mo | AI answers after hours (up to 300 calls); emergency warm transfer to the client's on-call tech; SMS ticket; morning report |
| **Dispatch** (core) | **$449/mo** | Night Watch plus 150 live-dispatcher minutes, an on-call ladder (tech, backup, owner) with callbacks until confirmed, and an ETA text to the customer. Overage $1.75/min. |
| Dispatch Plus | $899/mo | Dispatch plus daytime overflow; 400 minutes |

### One Dispatch client per month

**Assumption:** 120 after-hours calls a month. AI resolves 60%; 48 calls reach a human at 3 minutes each, so 144 human minutes.

| Line | $/mo | Basis |
|---|---|---|
| Revenue | 449.00 | Assumption (above) |
| AI receptionist (wholesale) | 54.99 | [S] AI Front Desk |
| AI usage buffer | 25.00 | **Assumption**: per-minute terms not published |
| Telephony | 6.55 | [S] Twilio: 360 min × ($0.0085 inbound + $0.004 client leg + $0.0025 recording) + $1.15 number |
| Card fees | 13.47 | **Assumption** 3% |
| **Contribution before human time** | **348.99** | |
| Human time | 115.92–165.60 | 144 min × $24.15/hr loaded dispatcher ($21 × 1.15). Busy 50% of paid time: $0.80/min; busy 35%: $1.15/min. **Occupancy is an Assumption.** |
| **Gross margin** | **$183–233 (41–52%)** | |
| Night Watch tier, for comparison | $106 GM (53%) | No human time |

### Fixed costs, break-even and payback

| Item | Amount |
|---|---|
| Dispatcher seat: 130 hrs/mo × $24.15 | $3,140/mo |
| Phone platform: Aircall, 3-license minimum at $30 each [S] | $90/mo |
| E&O insurance + misc software | $200/mo (**Assumption**) |
| **Fixed total** | **$3,430/mo** |
| **Break-even** | **10 Dispatch clients** (3,430 ÷ 349) |
| One seat's capacity at 35% busy | ~19 clients (130 h × 21 talk-min ÷ 144) → **~$3,200/mo operating profit** |
| One-time startup (**Assumption**) | ≈ **$3,600**: attorney review of service agreement and recording scripts $1,500; site and domain $200; sponsored job post $300; 40 training hours $966; first month of stack and TJ's AI seat $145; insurance deposit $300; QA tools $200 |
| Cash needed before break-even (**Assumption**: client ramp 3 → 6 → 10 by month 3) | ≈ **$7,000–8,000** in total (startup plus about $3,700 of operating losses) |

Phone platform alternatives: Dialpad contact center from $80/user/mo [S]. Purpose-built answering platforms are much heavier: Startel Cloud $375/seat + $17k setup; Amtelco Genesis $300/seat + $20k [S, 2021 data, re-quote]. Don't buy these until about 30 clients.

### Customer acquisition

| Channel | Cost to win a client | Use |
|---|---|---|
| Google Ads | CPC $39.62–68.59 on contractor terms [S: Semrush]. **Assumption:** 2% of clicks become clients, so **$2,400–3,100 per client**, paid back in 13–17 months. Too slow. | Test only, capped at $1,000 (wk 6) |
| **Partner lists** (`qualify-partners` → `audit-partners` drafts → the team sends) | **Assumption:** 30 conversations → 3 pilots → 2 paid; about $400–600 per client in team time plus the free 30-day pilot (~$266 direct cost each) | **Lead channel** |
| Organic search | Contractor terms are easy to rank for: "plumbing answering service" 1,600/mo KD 8; "hvac answering service" 1,300 KD 10; "answering service for contractors" 1,000 KD 10; "answering service for plumbers" 480 KD 11; "restoration answering service" 170 KD 5 [S: Semrush]. The top results are mostly AI-vendor blogs [S: OpenRush SERP]. | One page per trade, plus real dispatch SOP content |
| Trade groups | PHCC (~3,300 member businesses [S]); Illinois PHCC Expo in Oakbrook Terrace, 500–1,000 attendees [S] | Spring push |

Pitch line, vendor-reported and unverified: "HVAC contractors miss 27–38% of calls between 6pm and 8am" [S: ainora/stealthagents]. Use it only with attribution.

---

## 5. Where to start

The service is national, so "areas" means client markets. Phase 1 has no profile or service-area list.

| Order | Market | Why |
|---|---|---|
| 0 | **TJ's Nationwide Roadside** (client #0) | Live call flow from day one, towing intake SOPs, and a case study |
| 1 | **Chicago metro HVAC, plumbing and restoration** | Home base and partner lists. The Chicago "answering service" pack is weak (1/1/15) for Phase 2. Cold-climate peaks: "furnace repair near me" ran 135,000 in Jan 2026 vs 27,100 in May 2026 (5×) [S: OpenRush]. |
| 2 | **Milwaukee, Minneapolis, Detroit** (scout roster markets) | Same winter emergency profile and nearby time zones. **Assumption**, based on climate. |
| 3 | **Houston, Dallas, Phoenix** (roster) | Counter-seasonal AC "no cool" summer calls keep dispatchers busy year-round. "emergency plumber near me" also peaked at 135,000 in Jul 2026 [S]. |

**Phase 2 office ZIP:** none chosen yet. Use TJ's base ZIP if it's a commercial unit that can carry permanent signage and receive visitors. Otherwise pick a ground-floor unit on a CTA line so overnight staff can commute. **Profile service areas: none.** It's a storefront.

---

## 6. Timeline against the season

Demand timing [S: OpenRush 24-mo]:

| Series | Pattern |
|---|---|
| Buyers ("after hours answering service") | Peaked Sep 2025 at 3,600 and Oct 2025 at 2,400; second wave Mar–May 2025 at 2,400/mo; Jul 2026 1,300 vs Jul 2025 880 (+48%) |
| Clients' emergency calls | "emergency plumber near me": Feb 2026 246,000 vs Nov 2025 33,100 (7.4×). "furnace repair near me": Jan 2026 135,000. |

**So: sell now (Oct), be live by mid-Nov, and be battle-tested before the Jan–Feb surge.**

| Week (Mon) | Work |
|---|---|
| 1 (Oct 5) | Write the offer and SLAs. Pick the stack (Twilio numbers + Aircall + AI Front Desk trial). Get an attorney to review the service agreement and the recording/AI disclosure script. Put TJ's after-hours line on the stack. Post the dispatcher job on Indeed. |
| 2 (Oct 12) | TJ's live. Measure answer rate, handle time, AI-resolved %. Write triage trees for plumbing, HVAC, towing and restoration. Run `qualify-partners` and `audit-partners` on the contractor lists and shortlist 30. |
| 3 (Oct 19) | Hire the lead dispatcher. Website live with the 4 trade pages. The team sends the outreach drafts, offering a 30-day free pilot. |
| 4 (Oct 26) | Sign 3 pilots. Onboard: on-call ladders, the client's own software or calendar, call forwarding. The client keeps ownership of their number. |
| 5 (Nov 2) | Pilots live. Run a weekly QA review of 10 recorded calls per client. |
| 6 (Nov 9) | Convert pilots to paid. Start the Google Ads test ($1,000 cap, exact match). |
| 7 (Nov 16) | Sign a surge-overflow partner. Add a part-time weekend agent if human minutes exceed 70% of seat capacity. |
| 8 (Nov 23) | Thanksgiving (Nov 26) is the first holiday stress test. Run the 30/60-day review against §8. Plan a cold-snap drill for December. |

Next sales wave: March, ahead of the spring buyer wave and AC season.

---

## 7. Two and three steps ahead

**Right after launch**
- The first cold snap multiplies emergency calls (7× swing in search demand). The AI absorbs volume, the overflow partner covers live minutes, and cold-snap overage is billed at $1.75/min.
- Pilots will ask "does it book into ServiceTitan / Housecall Pro / Jobber?" Integrate with those platforms; don't compete with them.

**Competitors and platforms**

| Who | Likely move | Our answer |
|---|---|---|
| AI-only vendors ($25–49/mo) | Push message-taking toward free | Sell confirmed dispatch, not answering. Keep Night Watch at $199 as the floor. |
| Contractor software (Jobber, Housecall Pro, ServiceTitan) | Bundle AI receptionists. ServiceTitan reports one HVAC shop where 90% of AI-handled calls ended in booked jobs (early access) [S]. | Be the human escalation and dispatch layer on top of their AI. |
| Offshore human providers (Armasourcing, Philippines [S]) | Undercut human labor | US-based, trade-trained dispatchers who know the local market |
| Google | AI overviews already show on "after hours answering service", "answering service for contractors" and "plumbing answering service" [S: OpenRush]. No Local Services Ads in the Chicago answering/call-center results (niche study). | Comparison pages and a review footprint on G2/Capterra (**Assumption**) to get cited in AI answers. Google profile in Phase 2. |
| Regulators | AI and recording rules tightening | See the table below |

**Regulatory exposure**

| Rule | What it means for us |
|---|---|
| FCC ruling (Feb 2024): AI voices count as "artificial" voices under the TCPA [S] | No AI-voice outbound callbacks without the consent the TCPA requires. Inbound answering is fine. |
| Illinois Eavesdropping Act (all-party consent; covers "surreptitious" recording) [S] | Disclose recording and AI at the start of every call. |
| BIPA (Illinois biometric privacy law): voiceprints are biometric identifiers; Lowe's and Walmart have been sued over call-center voiceprints [S] | Choose an AI vendor that doesn't build voiceprints, and put that in the contract. |
| TSR (16 CFR 310) business-to-business exemption, which now bans misrepresentation even on B2B calls [S] | Sales calls to contractors: manual dial only, accurate claims. |

**Build now so nothing gets rebuilt later**
- A separate brand and domain, not TJ-branded: working name "6 Central Answer & Dispatch" (`research/video_niches/picks.json`).
- 6 Central owns its numbers and the stack account. Clients keep their numbers and forward calls to us.
- A CRM tracking pilot → paid → churn.
- Call QA scorecard; triage SOP library per trade; on-call ladder template; a written emergency policy (gas smell or fire → 911 or the utility first).
- Client data agreement; recording-retention policy.
- Review system: ask happy clients for G2/Capterra reviews now and Google reviews in Phase 2. Never gate or buy reviews.

**Next adjacent service, and how this feeds the portfolio**
- Next services: daytime overflow / outsourced CSRs, maintenance-plan renewal calls (consent-based), review-request texts.
- One dispatch floor can serve the roadside, plumbing and water-restoration projects in `config/gbp_scout.json`.
- **Firewall:** never steer a client's callers to a 6 Central business. Put that in the contract. It is the trust the whole venture rests on.

**Phase 2 trigger (Google profile):** 15+ paying clients, or human minutes justifying a second staffed shift (**Assumption**). Then lease the signed office and record the §2 video.

---

## 8. Risks and kill criteria

| # | Risk | Mitigation |
|---|---|---|
| 1 | AI pricing ($25–49/mo) and software-bundled AI make answering a commodity | Sell the confirmed-dispatch outcome. Measure pilot-to-paid. Integrate with contractor software. |
| 2 | The labor floor (a 24/7 seat ≈ $10k/mo) outruns revenue | Humans only in peak windows; AI plus the on-call ladder overnight; surge overflow paid per minute |
| 3 | A missed or mishandled emergency (no heat, gas, flood) → harm and liability | Life-safety script (911 or utility first), escalation ladder with forced callback, E&O insurance, SLA limits, weekly QA |
| 4 | Compliance: Illinois all-party recording consent, BIPA voiceprints, TCPA on AI outbound calls | Disclosure script, vendor biometric terms, no AI outbound without consent, no medical/HIPAA clients |
| 5 | Over-reliance on TJ's, plus a portfolio conflict of interest | Firewall clause. Also check TJ's listing name, "TJ 24 Hour Mobile Tire Repair Service Chicago IL" (`config/gbp_scout.json`): if that isn't the registered name, it's a suspension risk under our own playbook, and it would cut client #0's call volume. |

| Checkpoint | Continue if | Stop or rethink if |
|---|---|---|
| **30 days (Nov 4)** | TJ's answer rate ≥95% (**Assumption** target); ≥3 pilots signed | <1 pilot from ≥30 conversations |
| **60 days (Dec 4)** | ≥3 paying clients at ≥$199; blended gross margin ≥35%; zero missed emergency escalations | <2 paying, GM <20%, or any missed life-safety escalation |
| **90 days (Jan 3)** | ≥8 paying clients; MRR ≥$2,500; ≤1 churned; any ad-acquired client cost ≤$1,500 | MRR <$1,500 → shrink to TJ's internal dispatch only and stop ads |

---

## 9. Sources

Internal: 6 Central niche study, OpenRush/Semrush, 2026-10-04 (`research/video_niches/`, `runs/video-niches/`). `config/gbp_scout.json`. Semrush `phrase_these`, US database, 2026-10-04 (200 units). OpenRush `inspect_keyword` ×3 and `inspect_serp` ×2, United States, 2026-10-04 (19 credits). Saved in `runs/plans/answering-dispatch-for-contractors/`.

**Google**
- https://support.google.com/business/answer/13763036
- https://support.google.com/business/answer/3038177
- https://support.google.com/business/answer/14271705
- https://wiremo.co/blog/google-business-profile-video-verification/

**Competitor pricing**
- https://www.ruby.com/pricing/
- https://smith.ai/pricing
- https://www.mapcommunications.com/pricing/
- https://upfirst.ai/pricing
- https://posh.com/pricing/
- https://www.patlive.com/pricing/ (via https://www.getaira.io/blog/virtual-receptionist-pricing)
- https://serviceagent.ai/blogs/answerforce-pricing/
- https://www.getnextphone.com/blog/answerforce-alternative
- https://armasourcing.com/hvac-answering-service/
- https://www.designrush.com/agency/profile/excel-answering-service-inc
- https://posh.com/industry/contractors-answering-service/
- https://dapta.ai/blog-posts/best-ai-answering-services-for-contractors/
- https://trillet.ai/receptionist/industries/plumbers
- https://www.housecallpro.com/resources/how-much-does-an-answering-service-cost/

**AI receptionists and white-label programs**
- https://www.myaifrontdesk.com/blogs/unlock-agency-growth-transparent-my-ai-front-desk-white-label-pricing-revealed
- https://llms.myaifrontdesk.com/white-label-reseller-agencies
- https://myaifrontdesk.com/white-label
- https://www.getjobber.com/features/ai-receptionist/
- https://www.beside.com/blog/housecall-pro-ai-phone-answering
- https://help.servicetitan.com/how-to/configure-your-voice-agent-settings-in-servicetitan
- https://servicetitan.com/features/pro/voice-agent
- https://www.barchart.com/story/news/2378208/bill-joplins-air-conditioning-and-heating-books-over-90-of-calls-with-servicetitan-ai-voice-agent-ahead-of-peak-season
- https://voicenation.com/affiliate-program (redirects to https://www.moneypenny.com/us/)

**Phone stack**
- https://www.twilio.com/en-us/voice/pricing/us
- https://justcall.io/blog/aircall-pricing.html
- https://www.ringly.io/blog/dialpad-pricing
- https://evs7.com/answering-service/6-best-virtual-receptionist-software-2021

**Pay and offices (Indeed postings, pulled 2026-10-04)**
- https://to.indeed.com/aawps7qhx8f9 (Excel Answering Service $17.05)
- https://to.indeed.com/aa8rs7l84qns (Roto-Rooter evening dispatcher $19–21)
- https://to.indeed.com/aarbvf9gsvnf (Transdev $18–20.50)
- https://to.indeed.com/aa8bf9q8j9g2 (Johnstone Supply $22–26)
- https://to.indeed.com/aag6gp6sbmtr (AnswerNet remote $16)
- https://to.indeed.com/aabryqkhzpn2 (AnswerNet remote $15)
- https://to.indeed.com/aay6x69tnwr8 (Peaden remote dispatcher $18–25)
- https://to.indeed.com/aacgggykn9bn (towing remote dispatcher $16)
- https://to.indeed.com/aapqg96k8kc6 (Home Comfort Services $60–68k)
- https://to.indeed.com/aal6cf489srf (call center manager $50–60k)
- https://www.hivedesk.com/compliance/united-states/minimum-wage-illinois
- https://www.workboxcompany.com/uncategorized/private-workspace-prices-in-chicago-a-strategy-for-teams/

**Law and regulation**
- https://www.ilga.gov/Documents/legislation/ilcs/documents/072000050K14-2.htm
- https://captaincompliance.com/education/illinois-eavesdropping-statute-a-huge-data-privacy-risk/
- https://www.americanbar.org/groups/litigation/resources/newsletters/class-actions-derivative-suits/voiceprints-ai-bipa-new-trends-biometric-privacy-litigation/
- https://news.bloomberglaw.com/artificial-intelligence/walmart-customers-sue-over-ai-generated-voiceprints-from-calls
- https://cooley.com/news/insight/2024/2024-02-15-fcc-ai-generated-robocalls-illegal-under-the-tcpa
- https://hunton.com/insights/legal/telemarketing-sales-rule-changes-remove-exception-for-business-to-business-calls-and-impose-new-recordkeeping-requirements
- https://www.overtime-flsa.com/blog/what-is-the-abc-test-for-worker-classification-in-illinois/

**Sales channels and market stats**
- https://www.phccweb.org/wp-content/uploads/2026/03/PHCC-Value-Proposition.pdf
- https://withorbital.com/conferences/illinois-phcc-expo-2026
- https://ainora.lt/blog/hvac-service-call-statistics-2026
- https://stealthagents.com/research/home-services-missed-call-revenue-statistics-2026
