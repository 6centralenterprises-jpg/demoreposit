# Elgin attack plan: growing the auto and snow network, Oct 2026 – Mar 2027

Terell lives in Elgin. The data comes from OpenRush map packs pulled 2026-10-04 (raw data in `runs/tire/serp/`,
which is gitignored). Numbers are the median review count of Google's top 3 results; lower is easier to beat.
TJ's tire listing showed up in **none** of these 40 checks, so the Elgin area is new ground.

## Why Elgin is the best base we've found
| City | Tire | Lockout | Mechanic | Snow |
|---|---|---|---|---|
| **Elgin** | **5** | **7** | **12** | **8** |
| South Elgin | 23 | 7 | 12 | 2 |
| Streamwood | 23 | 22 | 12 | 2 |
| Bartlett | 14 | 10 | 12 | 7 |
| Hoffman Estates | 14 | 117 | 103 | 11 |
| Carpentersville | 37 | 31 | 12 | 2 |
| Crystal Lake | 14 | 124 | 90 | 16 |
| Huntley | 23 | 31 | 90 | 1 |
| St. Charles | 23 | 36 | 90 | 211 |
| Algonquin | 101 | 105 | 90 | 2 |

All four services are wide open in the **Elgin, South Elgin, Streamwood and Bartlett** core. The leaders are weak:
- **Tire:** Michoacan Tire (23 reviews), AQ Mobile Mechanic (5), and a keyword-stuffed "... Schaumburg IL"
  listing with 2 reviews.
- **Mechanic:** Jacobs Mobile Mechanic (12) and AQ (5).
- **Lockout:** Otis Keys Crew (7).
- **Snow:** several listings with 1–8 reviews.

## How the listings are structured (CLAUDE.md)
- **6 Central's own listing from the Elgin home** only for a service that 6 Central's own people do from
  there, such as Terell or a W-2 tech running tire and mechanic calls.
  - Check Elgin's home-occupation rules for parking and dispatching service vehicles first.
  - TJ's could add Elgin as a **second real location** only if a tech actually works from there.
- **Everything subcontracted** goes on listings owned by the licensed operator, at the operator's real base
  (Partner & manage, with 6 Central's percentage in writing).
  - Lockout operators need an Illinois locksmith license or a confirmed towing exemption.
- **No listing goes live without a real base and a verification video filmed there.**

## Calendar
| Dates | Move | Why now |
|---|---|---|
| **Oct 5–11** | Fix TJ's name and website. Check Elgin home-occupation rules. Start recruiting Elgin-area operators (mechanic, licensed lockout, snow) using qualify-partners on a lead list. Pick the first Elgin listing. | November tire spike; re-verification has to clear before it |
| **Oct 12–25** | Verify the first Elgin listing (tire and mechanic from a real base). Partner snow operators verify their own listings. Sell snow seasonal contracts in Elgin, South Elgin, Streamwood and Bartlett (capped and fixed-price; El Niño winter). | Snow contracts must close by about Nov 15 |
| **Oct 26 – Nov 15** | Second and third partner listings (lockout, mechanic). Answering and dispatch live for every listing. Ask every customer for a review. | "mobile tire repair near me" peaks in November (90,500 last Nov) |
| **Nov 16 – Dec 31** | Ride the tire, winter-tire and snow season (first snow averages Nov 18). Add Hoffman Estates, Crystal Lake and Carpentersville partners. | Winter-tire searches run about 2.5× Nov–Jan |
| **Jan – Feb** | Snow peak (expect a light winter). Expand into Chicago gaps: Southwest/Midway (all three services), South Side 60617 (mechanic 5). | Keep pressure on while competitors coast |
| **March** | Tire-change wave (pothole season peaked Mar 2026 at 5,400/mo nationally). Marine launch Mar 1 on Chain O'Lakes. | Spring season |

## Daily routine
- **Every day:** contact 5 new operators; follow up with 5; one research or verification task; review requests.
- **Every week:** sign at least 1 new partner and get 1 new listing to verification.
- **Every Sunday:** the scout's owner memo picks the next target area.

Steady, real additions are what Google's 2026 rules reward. Bursts of new listings and edits are what they flag.

## Week 1 findings (2026-10-04)
- **Elgin home base.** The zoning code allows a home business only if it's incidental to the residence, with
  minimal customer traffic. Commercial vehicles over 10,000 lbs or 22 ft can't park on residential streets.
  A van or pickup run from home looks workable; confirm with Elgin Code Enforcement before verifying
  ([cityrulelookup](https://cityrulelookup.com/parking/commercial-vehicles/elgin-il)).
- **Towing exemption under the Illinois locksmith law.** Towing-service employees may open vehicle locks so
  a vehicle can be moved without towing, but only if the towing service does not advertise or hold itself out
  as a locksmith ([ILGA, P.A. 91-0287](https://lrb.ilga.gov/legislation/publicacts/pubact91/acts/91-0287.html)).
  A listing that advertises "car lockout" counts as holding out, so lockout listings need a licensed
  locksmith operator. Confirm against the current 225 ILCS 447 with IDFPR.
- **Partner shortlist.** Built from the Elgin-area map packs; local file `runs/tire/elgin_partner_candidates.json`.
  These are real operators with thin profiles who appear across many cities:
  1. AQ Mobile Mechanic: 5 reviews, mechanic and tire, 8 cities, has a website.
  2. Jacobs Mobile Mechanic: 12 reviews, 8 cities, no website.
  3. Michoacan Tire Mobile Repair: 23 reviews, 9 cities, no website.
  4. Otis Keys Crew: 7 reviews, lockout, 2 cities. Verify the locksmith license.
  5. Snow Warriors Snow Removal: 2 reviews, 6 cities, has a website.

  Skip listings with city-keyword names: "Central St 24 Hour ... Schaumburg IL" and "Hoffman Estates
  Auto Keys Replacement". These are suspension risks, not partners.
