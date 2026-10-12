# Demand Drivers for Mobile Tire Repair / Replacement: US Metro Shortlist (research as of Oct 2026)

Scope note: 15 tool calls made. Many primary datasets (FHWA Highway Statistics tables, ACS 2024 commute tables, latest TRIP urban-roads appendix) were not reachable through search snippets, so several per-metro quantitative fields are listed under Gaps rather than filled in. Nothing below is invented. Anything that is a judgement is under "Inferences" and labeled.

## 1. Which metros have the most vehicles, the most miles driven (VMT) and long commutes?

### Takeaway
I could not get current per-metro registered-vehicle or VMT figures (FHWA) or 2024 ACS commute tables. The only commute data I found is older Census-based reporting: New York-Newark has the longest commute among large metros (about 35.8 minutes one way).

### Cited Findings
- Census-based ranking (article dated Jan 2024, likely an earlier ACS vintage): East Stroudsburg, PA had the longest average one-way commute at about 36.2 minutes. New York-Newark-Jersey City was 35.8 minutes and Stockton, CA was 33.9 minutes. — [Black Enterprise, Jan 2024](https://blackenterprise.com/10-cities-longest-commute-times)
- Replica 2023 (not Census; measures total daily travel time per person, not commute): Nashville ranked first at 2 hrs 20 min of average daily travel time. — [FOX 5 Atlanta / Replica](https://www.fox5atlanta.com/news/cities-longest-commutes)

### Inferences
- (Inference) Total vehicle count and VMT largely follow metro population. The largest metros (NYC, LA, Chicago, Dallas-Fort Worth, Houston, Atlanta, Phoenix, Miami) will therefore lead on absolute vehicle-miles. Sunbelt metros that depend on cars (DFW, Houston, Atlanta, Phoenix) likely produce more VMT per resident than transit-heavy NYC or Chicago. This is not sourced.

### Gaps
- FHWA Highway Statistics (HM-71 urbanized-area VMT, MV-1 state registrations): no per-metro figures came back. Pull HM-71 directly from fhwa.dot.gov.
- ACS 2024 1-year mean travel time to work (table S0801/B08303) by metro: not retrieved.

## 2. Where are flat tires and road hazards most common (potholes, road condition, AAA calls, heat)?

### Takeaway
California urban areas (San Jose, LA, SF-Oakland) plus Honolulu, New Orleans and New York-Newark have the highest share of poor major roads in TRIP's data, but the rankings I found are several years old. Nationally, AAA answers more than 30 million roadside calls a year (2025), and blown tires are among the most common call types. Heat-driven blowouts are a documented Sunbelt summer driver, and potholes are a documented Northeast and Midwest winter-spring driver.

### Cited Findings
- TRIP large urban areas (500k+) with the highest share of major roads in poor condition: San Jose 64%, Los Angeles 63%, Honolulu 62%, Concord CA 58%, San Francisco-Oakland 58%, New Orleans 55%, New York-Newark 53%. Edition is older, likely based on FHWA 2016-era data, and the date is not confirmed. — [Equipment World](https://www.equipmentworld.com/business/article/14948004/the-top-20-urban-roads-in-poor-condition); [Informed Infrastructure](https://informedinfrastructure.com/post/urban-areas-with-the-worst-roads-top-3-are-in-california)
- CoPilot analysis of FHWA IRI data (date unclear): LA-Long Beach-Anaheim had 62.8% of major roads in poor condition and San Jose had 63.3%. — [NBC Los Angeles](https://www.nbclosangeles.com/local/major-roads-in-los-angeles-long-beach-and-anaheim-rank-third-worst-in-the-us/173082/)
- TRIP Nov 2016: 32% of major urban roads were in poor condition and 39% were mediocre or fair. — [InfrastructureUSA](https://infrastructureusa.org/?p=31815). Another TRIP edition put the figure at 33% poor, with an average cost of $599 per motorist per year. — [Roads & Bridges](https://roadsbridges.com/home/news/10585888/report-shows-24-of-urban-pavement-in-us-in-poor-condition). These differing figures (24%, 27%, 32%, 33%) come from different TRIP editions and years.
- TRIP Jan 2025 (New York State): 45% of major roads were poor or mediocre, costing $38B a year. Buffalo-Niagara Falls had 35% poor or mediocre roads, adding $465 per motorist per year. — [Spectrum News, Jan 16 2025](https://spectrumlocalnews.com/nys/central-ny/news/2025/01/16/new-report-shows-poor-road-conditions-cost-new-yorkers-billions)
- AAA: more than 30 million roadside service calls nationwide in 2025, with blown tires, battery replacements and jump starts the most common. — [AAA Mountain West Group press release, 2026](https://mwg.aaa.com/news/press-release/may-5-2026)
- AAA Mountain West: nearly 300,000 roadside calls in Nevada last year, mostly blown tires, batteries and jump starts, and mostly on freeways. — [KTNV Las Vegas](https://www.ktnv.com/news/auto-pros-urge-southern-nevada-drivers-to-take-preventative-steps-in-extreme-heat)
- AAA Carolinas logged 7,042 tire-related calls over two weeks during a hot stretch, and AAA Nevada expected 12,600 flat-tire calls (period as reported in local news). — [News3LV](https://news3lv.com/news/local/summer-heat-raises-concern-of-tire-blowouts); [WLBT, Jul 2026](https://www.wlbt.com/2026/07/29/extreme-heat-raising-breakdown-risk-mississippi-roads-experts-say/)
- Older national AAA figure: more than 4 million flat-tire assistance calls a year, many caused by potholes (about 2015). AAA's pothole repair estimate averages almost $600 per repair. — [CBS Detroit](https://www.cbsnews.com/detroit/news/aaa-pothole-damage-costs-drivers-3-billion-every-year)
- Regional AAA tire-call data for 2024 and early 2025:
  - Ohio: almost 60,000 tire-related calls, and 20% needed a tow because there was no spare. — [Spectrum News Ohio, Feb 2024](https://spectrumnews1.com/oh/cleveland/news/2024/02/07/aaa-s-tips-to-avoid-paying-extra-for-pothole-damage)
  - Maryland: 40% of 2024 calls were tire troubles that required a tow. — [CBS Baltimore](https://www.cbsnews.com/baltimore/news/maryland-drivers-frustrated-with-potholes)
  - New York City and Long Island: more than 10,000 flat-tire calls in December and January. — [Newsday via TRIP, Mar 15 2025](https://tripnet.org/wp-content/uploads/2025/03/NY_Long_Island_Newsday_03-15-2025.pdf)
- Missing spares: AAA rescued more than 450,000 members with a flat and no spare in one year (undated), and roughly one-third of new vehicles lack a spare. — [Journal-News](https://www.journal-news.com/classifieds/cars/spare-nearly-one-third-new-vehicles-are-missing-spare-tire/8C67XkO99MOIdNJMk5lYPI/)
- AAA Central Penn added an on-site flat-tire repair service (TireJect), which shows that roadside repair without a tow is being productized. — [AAA Central Penn](https://centralpenn.aaa.com/blog/aaa-central-penn-adds-flat-tire-service-featuring-tireject-repair-solution/)

### Inferences
- (Inference) Missing spare tires plus TPMS-era drivers who cannot change a tire create direct demand for "come to me" repair and replacement. That demand is national, not limited to one metro.
- (Inference) There are two demand profiles. In Sunbelt metros (Phoenix, Las Vegas, Houston, DFW, Atlanta, Florida), heat blowouts peak in summer. In Northern metros (NYC, Philadelphia, Chicago, Detroit, Ohio cities, Baltimore), pothole flats peak from winter through spring. California metros score high on poor pavement all year.

### Gaps
- No current (2024-2026) TRIP national urban-area ranking was retrieved. TRIP's latest urban-roads report and appendix at tripnet.org should be checked.
- No QuoteWizard or other 2025 pothole-complaint city ranking was retrieved.
- AAA does not publish flat-tire call counts broken out by metro. Only the regional snippets above were found.

## 3. Which metros have the fastest population and vehicle growth (Census 2025 estimates)?

### Takeaway
In Census Vintage 2025 (July 2024 to July 2025), Houston and Dallas-Fort Worth each added about 125,000 people, roughly double Atlanta, the next-largest gain. Phoenix and Seattle round out the top five. Ocala FL, Myrtle Beach SC and St. George UT led on percentage growth. Growth slowed in most metros.

### Cited Findings
- Numeric gains, 2024 to 2025:
  - Houston-Pasadena-The Woodlands: about 126,700
  - Dallas-Fort Worth-Arlington: about 123,600
  - Atlanta: 61,953
  - Phoenix-Mesa-Chandler: 59,065
  - Seattle-Tacoma-Bellevue: about 43,100
  - Source: [RealPage analysis of Census Vintage 2025](https://www.realpage.com/analytics/population-growth-markets-2025/); Phoenix figure from [ABC15](https://www.abc15.com/news/business/new-census-data-only-two-major-u-s-metros-outpaced-the-valleys-growth-rate-in-2025). Note: in RealPage's own list Seattle is 4th, while ABC15 calls Phoenix's gain the 4th-highest. The ordering of Phoenix and Seattle conflicts slightly between sources.
- Percentage growth: Ocala FL 3.4%, Myrtle Beach SC 3.2%, St. George UT 2.6% (population 213,670). Ten metros grew 2.4% or more. — [RealPage](https://www.realpage.com/analytics/population-growth-markets-2025/)
- 310 of 387 metros grew more slowly in 2024-25 than the year before, mainly because of lower international migration. — [RealPage](https://www.realpage.com/analytics/population-growth-markets-2025/)
- Census (May 2026): this decade's metro growth is driven mostly by exurbs and outer edges. — [Census Bureau](https://census.gov/library/stories/2026/05/major-city-outer-edge-growth.html)

### Inferences
- (Inference) Exurban growth means longer drives and more new roads and construction zones, which bring construction debris (nails and screws). It also puts customers far from fixed tire shops. Both favor mobile service in the DFW, Houston, Atlanta and Phoenix fringes.

### Gaps
- No per-metro vehicle-registration growth data was found. Texas, Georgia, Arizona and Florida DMV statistics would be needed.
- Total 2025 metro populations were not retrieved, apart from St. George.

## 4. Fleet and commercial demand (last-mile delivery, warehousing, rideshare, rental, commercial fleets)

### Takeaway
Dallas-Fort Worth (about 1.0B sq ft of industrial space and the largest US construction pipeline in mid-2025) and the Inland Empire / LA (the largest warehouse hub) are the top logistics concentrations confirmed by sources. 3PLs drove 2025 big-box leasing. I found no metro-level data on rideshare or rental fleets.

### Cited Findings
- DFW: about 1.0B sq ft of industrial space, with 28-29M sq ft under construction in mid-2025 (the largest pipeline in the US) and nearly 25M sq ft of net absorption in 2025. — [CBRE](https://www.cbre.com/press-releases/3pls-take-the-lead-in-2025s-top-100-industrial-leases); [MMCG](https://www.mmcginvest.com/post/the-top-five-u-s-industrial-markets-in-2025-an-investor-s-deep-dive)
- The Inland Empire is described as the largest US warehouse hub, tied to the LA and Long Beach ports. — [Cresa](https://www.cresa.com/blog/post-covid-warehouse-and-distribution-trends-in-major-us-logistics-markets)
- CBRE: 44 of the top 100 industrial leases in 2025 went to 3PLs, up from 28 in 2024. — [CBRE](https://www.cbre.com/press-releases/3pls-take-the-lead-in-2025s-top-100-industrial-leases)
- Cushman & Wakefield: deals over 500,000 sq ft rose 32% year over year, and 71% of large 2025 leases were in markets with below-average rents. — [Supply Chain 24/7](https://www.supplychain247.com/article/large-warehouse-leasing-rebounds-us)

### Inferences
- (Inference, not sourced) Other large distribution hubs commonly cited in industry rankings (Atlanta, Chicago, Houston, Phoenix, Pennsylvania I-78/I-81) would also have dense delivery-van fleets. Atlanta-specific data did not come back in this search.

### Gaps
- No metro data on Amazon DSP or last-mile van counts, Uber/Lyft driver counts, or rental-car fleet sizes. No BLS warehousing employment (NAICS 493) by MSA was retrieved.

## 5. Weather: year-round operability

### Takeaway
I found no quantified days-of-snow or extreme-cold data per metro. AAA sources confirm that hot climates bring blowout spikes (Nevada, Carolinas, Mississippi in summer 2026), while the Northern sources tie flats to winter and spring potholes.

### Cited Findings
- Hot pavement makes tires bulge, dry out and rot. Under-inflation raises overheating and blowout risk. — [AAA MWG release, 2026](https://mwg.aaa.com/news/press-release/may-5-2026); [WLBT, Jul 29 2026](https://www.wlbt.com/2026/07/29/extreme-heat-raising-breakdown-risk-mississippi-roads-experts-say/)
- AAA reported that pothole season arrived earlier than usual in 2024 (Feb 2024). — [12 On Your Side](https://www.12onyourside.com/2024/02/06/aaa-pothole-season-has-arrived-earlier-than-usual-this-year)

### Inferences
- (Inference) Sunbelt metros let a mobile technician work 12 months a year with no snow downtime, at the cost of heat stress on crews. Northern metros get a spring pothole surge but lose days to snow and ice.

### Gaps
- NOAA days below freezing and snowfall days per metro were not retrieved.

## 6. Size and trends of the US mobile tire service market

### Takeaway
I found no credible US-specific dollar figure for mobile tire service. Vendor reports give adjacent global numbers, and trade press shows distributors (ATD / Tire Pros) building mobile-install programs.

### Cited Findings
- Mobile tire balancing (global): $1.2B in 2025, with North America at $507.6M (42.3%) and a 7.8% CAGR through 2034. This is an unverified vendor estimate. — [Market Intelo](https://marketintelo.com/report/mobile-tire-balancing-service-market)
- Tire installation services (global): $9.8B in 2025, with mobile services at 18.3% penetration. Vendor estimate. — [Market Intelo](https://marketintelo.com/report/tire-installation-services-market)
- Tire Pros (ATD) piloted a mobile installation program in 2022, with early adopters in Atlanta and Minnesota, and grew to 623 locations by 2023. — [Modern Tire Dealer, 2023](https://moderntiredealer.com/industry-news/wholesale-distribution/article/33001275/tire-pros-focuses-on-mobile-installation-digital-tools-and-more); [MTD: How Two Dealers Plan to Grow Their Mobile Businesses](https://www.moderntiredealer.com/retail/article/33001683/how-two-dealers-plan-to-grow-their-mobile-businesses)
- Mobile repair product sales more than doubled from 2016 to 2021, and mobile technicians doubled over the same period. — [Auto Service World](https://www.autoserviceworld.com/?p=252332)
- Excluded as unreliable: spam pages claiming a "14% Q1 2026 increase in mobile tire requests."

### Gaps
- IBISWorld and Tire Business US mobile tire numbers are paywalled or were not retrieved.

## Ranked shortlist (synthesis; ranking is an INFERENCE from the cited findings above, not a published index)

| Rank | Metro | Key cited drivers |
|---|---|---|
| 1 | Dallas-Fort Worth, TX | +123,600 pop (2025); about 1.0B sq ft industrial and the largest US pipeline; Sunbelt heat; operable year-round |
| 2 | Houston, TX | +126,700 pop (2025, the largest gain); heat; large metro (no Houston-specific logistics or road data retrieved) |
| 3 | Atlanta, GA | +61,953 pop; Tire Pros mobile pilot market; heat (no road or logistics data retrieved) |
| 4 | Phoenix, AZ | +59,065 pop; extreme heat drives blowouts; operable year-round |
| 5 | Los Angeles / Inland Empire, CA | 62.8-63% of major roads poor (older data); largest warehouse hub |
| 6 | New York-Newark | 53% poor roads (older TRIP); 35.8-min commute; more than 10,000 flat calls Dec-Jan on NYC/LI; seasonal |
| 7 | San Jose / SF-Oakland, CA | 58-64% poor roads (older TRIP) |
| 8 | Las Vegas, NV | about 300,000 Nevada AAA calls (mostly tires, batteries, jumps); heat |
| 9 | Florida growth metros (e.g., Ocala, Orlando and Tampa areas) | Ocala +3.4% (the fastest in the US); heat |
| 10 | Seattle-Tacoma, WA | +43,100 pop (2025) |

Caveat: ranks 1-4 are weighted toward growth and logistics, and ranks 5-7 toward road condition. Validate against FHWA HM-71 VMT, ACS 2024 commute data and the latest TRIP appendix before relying on the order.
