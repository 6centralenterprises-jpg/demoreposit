"""Render the daily GBP Opportunity Brief (HTML page + short text summary).

The page carries the scout's memory: the watchlist and past briefs live in a
JSON block (id="scout-state") so tomorrow's run can read them back.
"""
import json
from html import escape

GUARDRAILS = [
    "A profile only for a real business that does the work, has a real base and real staff. "
    "Google bars lead-generation companies from holding profiles.",
    "Home-based: set it up as a service-area business and hide the home address. "
    "Never use a virtual office, a mailbox or a borrowed address.",
    "One profile per real business. Don't make city-by-city copies unless each city has real, staffed operations.",
    "Managed clients stay Primary Owner of their profile. 6 Central asks for Manager access.",
    "Real reviews only: no buying, gating or writing reviews.",
    "Licensed trades: the business on the profile holds the license for that market.",
]

PILL = {"Surging": "up", "Rising": "up2", "Steady": "flat", "Cooling": "down",
        "Own it": "own", "Partner & manage": "partner", "Validate": "validate", "Watch": "watch"}


def pct(value):
    return "–" if value is None else f"{value * 100:+.0f}%"


def num(value):
    return "–" if value in (None, "") else f"{value:,}" if isinstance(value, int) else f"{value:,.0f}"


def money(value):
    return "–" if value in (None, "") else f"${value:,.2f}"


def focus_section(f):
    if not f:
        return ""
    today = "".join(f"<li>“{escape(c['query'])}” in {escape(c['market'])}: median {num(c.get('median_reviews'))} reviews"
                    f" (openness {c['weakness']:.2f})</li>" for c in f["today"] if c.get("weakness") is not None)
    rows = "".join(f"<tr><td class=\"n\">{i}</td><td>{escape(r['market'])}</td><td class=\"n\">{r['openness']:.2f}</td>"
                   f"<td>{escape(r['best_query'])} <span class=\"muted\">(median {num(r['best_median'])})</span></td>"
                   f"<td class=\"n\">{escape(r['last'])}</td></tr>" for i, r in enumerate(f["leaderboard"][:8], 1))
    lic = "".join(f"<li><strong>{escape(s)}:</strong> {escape(v['note'])} {link(v['source'], 'source')}</li>"
                  for s, v in f["licensing"].items())
    return f"""<section><h2>Standing watch: {escape(f['label'])}</h2>
<p class="muted" style="margin-bottom:10px">Licensed trades: the play is Partner &amp; manage with a real licensed builder,
or a 6 Central company that holds the license itself. Checked in every market, alternating searches daily.</p>
<div class="grid2"><div class="panel"><h3>Today's checks</h3><ul>{today or '<li class="muted">No focus checks saved today.</li>'}</ul></div>
<div class="panel"><h3>License rules in these markets</h3><ul>{lic or '<li class="muted">No rules on file for these states yet.</li>'}</ul></div></div>
{f'<div class="table" style="margin-top:14px"><table><thead><tr><th>#</th><th>Market</th><th>Openness</th><th>Most open</th><th>Last checked</th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else ''}
</section>"""


def own_line(o):
    if not o["checked"]:
        return f"{o['name']}: not checked today."
    spot = f"#{o['position']} in the map pack" if o["position"] else "not in the top 3"
    text = f"{o['name']} is {spot} for '{o['query']}' in {o['market']}"
    if o["position"]:
        text += f" ({o['rating']}★, {num(o['reviews'])} reviews)"
    prev = o.get("previous")
    if prev:
        was = f"#{prev['position']}" if prev.get("position") else "out of the top 3"
        text += f"; last check {prev['date']}: {was}, {num(prev.get('reviews'))} reviews"
    return text + "."


def own_listing_section(listings):
    if not listings:
        return ""
    cards = []
    for o in listings:
        issues = "".join(f"<li>{escape(i)}</li>" for i in o["issues"])
        cards.append(f"""<div class="panel"><div class="row"><h3>{escape(o['name'])}</h3><span class="pill own">Ours</span></div>
<p>{escape(own_line(o))}</p>{f'<p><strong>Fix before Google asks:</strong></p><ul>{issues}</ul>' if issues else '<p class="muted">No mismatches found.</p>'}</div>""")
    return f"""<section><h2>Our listings</h2><p class="muted" style="margin-bottom:10px">Confirmed 6 Central listings,
checked in their map pack every day.</p><div class="grid2">{''.join(cards)}</div></section>"""


def pill(text):
    return f'<span class="pill {PILL.get(text, "flat")}">{escape(text)}</span>'


def link(url, text):
    return f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener">{escape(text)}</a>'


CSS = """
/* Layout: one reading column; summary first, data tables scroll on their own. */
:root {
  --bg: #f3f5f4; --surface: #ffffff; --ink: #18211f; --muted: #5b6a66; --line: #d9e0dd;
  --accent: #1d6b57; --accent-soft: #e2efe9;
  --up: #1d7a45; --up-bg: #dff3e6; --down: #a3392b; --down-bg: #f8e3df; --warn: #8a5a00; --warn-bg: #fbefd5;
  --info: #2f4f8f; --info-bg: #e3eaf8;
  --display: "Barlow Semi Condensed", "Arial Narrow", sans-serif;
  --body: "Source Sans 3", "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #111816; --surface: #18211e; --ink: #e5ece9; --muted: #9aaba5; --line: #2b3834;
  --accent: #6cc7a8; --accent-soft: #1d3029;
  --up: #7fd9a2; --up-bg: #183424; --down: #f0a093; --down-bg: #3a1f1a; --warn: #f0c46b; --warn-bg: #352a12;
  --info: #9db8f0; --info-bg: #1b2640; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #111816; --surface: #18211e; --ink: #e5ece9; --muted: #9aaba5; --line: #2b3834;
  --accent: #6cc7a8; --accent-soft: #1d3029;
  --up: #7fd9a2; --up-bg: #183424; --down: #f0a093; --down-bg: #3a1f1a; --warn: #f0c46b; --warn-bg: #352a12;
  --info: #9db8f0; --info-bg: #1b2640; color-scheme: dark; }
body { background: var(--bg); color: var(--ink); font: 16px/1.55 var(--body); }
.wrap { max-width: 1040px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 56px; display: grid; gap: 28px; }
header { display: grid; gap: 6px; }
.eyebrow { font: 600 12px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--accent); }
h1 { font: 700 clamp(30px, 5vw, 44px)/1.05 var(--display); margin: 0; text-wrap: balance; }
h2 { font: 700 24px/1.15 var(--display); margin: 0 0 12px; text-wrap: balance; }
h3 { font: 600 17px/1.3 var(--body); margin: 0; }
p { margin: 0; max-width: 68ch; }
.muted { color: var(--muted); }
a { color: var(--accent); }
a:focus-visible, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.moves { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
.move { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px; display: grid; gap: 10px; align-content: start; min-width: 0; }
.move .score { font: 700 34px/1 var(--display); font-variant-numeric: tabular-nums; }
.move .score small { font: 500 13px var(--mono); color: var(--muted); }
.row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.pill { font: 600 12px/1 var(--mono); padding: 5px 8px; border-radius: 999px; white-space: nowrap; background: var(--accent-soft); color: var(--accent); }
.pill.up { background: var(--up-bg); color: var(--up); } .pill.up2 { background: var(--up-bg); color: var(--up); opacity: .85; }
.pill.down { background: var(--down-bg); color: var(--down); } .pill.flat { background: var(--line); color: var(--muted); }
.pill.own { background: var(--accent); color: var(--surface); } .pill.partner { background: var(--info-bg); color: var(--info); }
.pill.validate { background: var(--warn-bg); color: var(--warn); } .pill.watch { background: var(--line); color: var(--muted); }
.pill.flag { background: var(--warn-bg); color: var(--warn); }
.table { overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font: 600 11px/1.2 var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--muted); white-space: nowrap; }
td.n { font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
tr:last-child td { border-bottom: 0; }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px; display: grid; gap: 10px; min-width: 0; }
ul { margin: 0; padding-left: 20px; display: grid; gap: 6px; }
.note { background: var(--warn-bg); color: var(--ink); border-radius: 10px; padding: 14px 16px; display: grid; gap: 6px; }
.tactic { background: var(--accent-soft); border-radius: 10px; padding: 16px; display: grid; gap: 6px; }
details summary { cursor: pointer; font-weight: 600; }
footer { font-size: 13px; color: var(--muted); display: grid; gap: 6px; }
@media (prefers-reduced-motion: no-preference) { .move { transition: border-color .15s; } .move:hover { border-color: var(--accent); } }
"""


def move_card(o):
    flags = []
    if o["new"]:
        flags.append('<span class="pill flag">New</span>')
    if o["licensed"]:
        flags.append('<span class="pill flag">License check</span>')
    yo = o.get("openrush") or {}
    facts = (f"{num(yo.get('volume') or o['semrush']['volume'])} searches/mo · CPC {money(yo.get('cpc') or o['semrush']['cpc'])}"
             f" · {pct(o['change'])} {'vs last year' if o['trend_source'].startswith('openrush') else '(seasonal)'}")
    return f"""<article class="move">
  <div class="row">{pill(o['play'])}{pill(o['label'])}{''.join(flags)}</div>
  <h3>{escape(o['keyword'])}</h3>
  <div class="score">{o['score']:.0f}<small> / 100</small></div>
  <p class="muted">{escape(facts)}</p>
  <p>{escape(o['why'])}</p>
  <p class="muted">{escape(o['portfolio'])}</p>
</article>"""


def opportunity_rows(opps):
    rows = []
    for o in opps:
        yo = o.get("openrush") or {}
        packs = o["map_packs"]
        pack = "; ".join(f"{p['market']}: median {num(p.get('median_reviews'))} reviews" for p in packs
                         if p.get("weakness") is not None) or "not checked"
        p = o["parts"]
        rows.append(f"""<tr><td>{escape(o['keyword'])}<br><span class="muted">{escape(o['niche'])}</span></td>
<td class="n">{o['score']:.0f}</td><td>{pill(o['label'])}</td>
<td class="n">{pct(yo.get('yoy'))}</td><td class="n">{pct(yo.get('mom'))}</td><td class="n">{escape(yo.get('latest_month') or '–')}</td>
<td class="n">{num(yo.get('volume'))}</td><td class="n">{num(o['semrush']['volume'])}</td>
<td class="n">{money(yo.get('cpc') if yo.get('cpc') is not None else o['semrush']['cpc'])}</td>
<td>{escape(pack)}</td><td>{pill(o['play'])}</td>
<td class="n">D{p['demand']:.0f} V{p['job_value']:.0f} M{p['momentum']:.0f} C{p['competition']:.0f} F{p['home_fit']:.0f}</td></tr>""")
    return "\n".join(rows)


def serp_panels(serps):
    panels = []
    for checks in serps.values():
        for c in checks:
            if not c["pack"]:
                body = f'<p class="muted">{escape(c["reason"])}</p>'
            else:
                ours = ' <span class="pill flag">Possibly ours: confirm</span>'
                mine = ' <span class="pill own">Ours</span>'
                items = "".join(
                    f"<li>{escape(p['name'])} · {p['rating'] if p['rating'] is not None else '–'}★ · "
                    f"{num(p['reviews'])} reviews{mine if p.get('ours') else ours if p['possibly_ours'] else ''}"
                    f"<br><span class=\"muted\">{escape(p['domain'])}</span></li>" for p in c["pack"])
                body = f"<ul>{items}</ul><p class=\"muted\">{escape(c['reason'])}</p>"
            weak = "–" if c.get("weakness") is None else f"{c['weakness']:.2f}"
            panels.append(f"""<div class="panel"><div class="row"><h3>“{escape(c['query'])}”</h3>
<span class="pill">{escape(c['market'])}</span><span class="pill">openness {weak}</span></div>{body}</div>""")
    return "\n".join(panels) or '<p class="muted">No map-pack checks today.</p>'


def signal_list(signals):
    names = {"weather": "Weather", "season": "Season", "news": "News & demand", "policy": "Google policy",
             "competitors": "Competitors"}
    blocks = []
    for key, items in signals.items():
        if not items:
            continue
        lis = "".join(f"<li>{escape(s.get('summary') or s.get('headline', ''))} "
                      f"({link(s['source'], 'source')})</li>" for s in items)
        blocks.append(f'<div class="panel"><h3>{escape(names.get(key, key.title()))}</h3><ul>{lis}</ul></div>')
    return "\n".join(blocks) or '<p class="muted">No sourced timing signals today.</p>'


def watchlist_rows(watch):
    rows = []
    for kw, w in sorted(watch.items(), key=lambda kv: -kv[1].get("score", 0))[:40]:
        pack = w.get("last_pack") or {}
        rows.append(f"""<tr><td>{escape(kw)}<br><span class="muted">{escape(w.get('niche', ''))}</span></td>
<td class="n">{w.get('score', 0):.0f}</td><td>{pill(w.get('label', 'Steady'))}</td><td class="n">{pct(w.get('change'))}</td>
<td>{pill(w.get('play', 'Watch'))}</td><td class="n">{escape(w.get('first_seen', ''))}</td>
<td class="n">{escape(w.get('last_seen', ''))}</td><td class="n">{num(pack.get('median_reviews'))}</td></tr>""")
    return "\n".join(rows)


def leaderboard_rows(rows):
    out = []
    for i, r in enumerate(rows[:25], 1):
        out.append(f"""<tr><td class="n">{i}</td><td>{escape(r['market'])}</td><td class="n">{r['openness']:.2f}</td>
<td class="n">{r['readings']}</td><td>{escape(r['best_query'])} <span class="muted">(median {num(r['best_median'])} reviews)</span></td>
<td class="n">{escape(r['last'])}</td></tr>""")
    return "\n".join(out)


def kit_section(b):
    kits = b.get("kits") or []
    if not kits:
        return ""
    proofs = b["verification"]["proofs"]
    names = {"location": "Where you operate", "exists": "Business exists", "management": "You manage it"}
    groups = {}
    for k in kits:
        groups.setdefault(k.get("niche", "every business"), []).append(k)
    blocks = []
    for niche, items in groups.items():
        rows = "".join(
            f"<tr><td>{pill(names.get(k.get('proof'), k.get('proof', '')))}</td><td>{escape(k.get('item', ''))}</td>"
            f"<td>{link(k['url'], k['title'][:90])}</td></tr>" for k in items)
        blocks.append(f'''<div class="panel"><h3>{escape(niche.title())}</h3><div class="table"><table>
<thead><tr><th>Google proof</th><th>What to have</th><th>Amazon listing found today</th></tr></thead>
<tbody>{rows}</tbody></table></div></div>''')
    reqs = "".join(f"<li><strong>{escape(names[k])}:</strong> {escape(v)}</li>" for k, v in proofs.items())
    return f'''<section><h2>Verification readiness kits</h2>
<p class="muted" style="margin-bottom:10px">What a real service-area business needs on camera for Google's video verification
(<a href="{escape(b['verification']['source'], quote=True)}" target="_blank" rel="noopener">Google's rules</a>). Listings come from today's
Amazon search; check price, reviews and seller before buying.</p>
<div class="note" style="margin-bottom:14px"><ul>{reqs}</ul>
<p><strong>Kits are for businesses that really do this work.</strong> Showing tools you don't use, or setting up a business that doesn't operate,
is misrepresentation, and it's the pattern Google's suspension waves target. A kit helps a real operator show what's true; it can't make a fake pass.</p></div>
<div class="grid2">{"".join(blocks)}</div></section>'''


def render_html(b):
    opps = b["opportunities"]
    state_json = json.dumps(b["state"]).replace("</", "<\\/")
    moves = "\n".join(move_card(o) for o in opps[:3])
    if not moves:
        moves = ('<p class="muted">Recap day: no new keyword research. The watchlist below is ranked by score, '
                 'and today\'s map-pack rechecks are in the next section.</p>' if b["recap"]
                 else '<p class="muted">No opportunities scored today. See the run notes below.</p>')
    own = ""
    if b["own_sightings"]:
        items = "".join(f"<li>{escape(s['name'])} in the “{escape(s['query'])}” pack ({escape(s['market'])}), "
                        f"{num(s['reviews'])} reviews, site {escape(s['domain'])}</li>" for s in b["own_sightings"])
        own = f"""<section class="note"><h3>Listings that may be ours</h3><ul>{items}</ul>
<p>Confirm whether these belong to a 6 Central business. If they do, check each one: is it at the real
business base, is the service area one we really serve, and does its website match the city?
Google's video verification and suspension checks look for exactly this.</p></section>"""
    mine = own_listing_section(b.get("own_listings") or [])
    past = "".join(f"<li><strong>{escape(x['date'])}</strong> · {escape(x['label'])}: "
                   f"{escape(', '.join(t['keyword'] for t in x['top']) or 'recap')}</li>"
                   for x in b["state"]["briefs"][1:15])
    spend = b.get("spend") or {}
    spend_text = (f"Spent today: {spend.get('openrush_credits', 'unknown')} OpenRush credits, "
                  f"{spend.get('semrush_units', 'unknown')} Semrush API units." if spend else "")
    table = f"""<div class="table"><table>
<thead><tr><th>Keyword</th><th>Score</th><th>Trend</th><th>YoY</th><th>MoM</th><th>Data month</th><th>Vol (OpenRush)</th>
<th>Vol (Semrush)</th><th>CPC</th><th>Map pack</th><th>Play</th><th>Parts</th></tr></thead>
<tbody>{opportunity_rows(opps)}</tbody></table></div>""" if opps else ""
    return f"""<title>GBP Opportunity Scout</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@600;700&family=JetBrains+Mono:wght@500;600&family=Source+Sans+3:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header>
  <span class="eyebrow">6 Central Enterprises · Morning brief · {escape(b['weekday'])} {escape(b['date'])}</span>
  <h1>{escape(b['label'])}</h1>
  <p class="muted">Google Business Profile opportunities for home-based service businesses. Keyword data is
  national (US); map packs checked in {escape(', '.join(b['markets']))}.</p>
</header>

<section><h2>Today's moves</h2><div class="moves">{moves}</div></section>
{mine}
{own}
{focus_section(b.get("focus"))}
{f'<section><h2>Keywords checked today</h2>{table}<p class="muted" style="margin-top:8px">Score parts: D demand (25) · V job value from CPC (20) · M momentum (20) · C map-pack openness (25) · F home-based fit (10). Semrush and OpenRush volumes differ by vendor and are never compared with each other.</p></section>' if table else ''}

<section><h2>Map pack check</h2><div class="grid2">{serp_panels(b['serps'])}</div></section>

{f'''<section><h2>Best markets so far</h2><p class="muted" style="margin-bottom:10px">Ranked by map-pack openness across every check (1.00 = top 3 have under 20 reviews; 0.10 = hundreds). Chicago is checked daily; 34 national metros rotate, 3 a day. Early rankings compare different searches, so they firm up after a few weeks once every market has been checked across all business groups.</p><div class="table"><table>
<thead><tr><th>#</th><th>Market</th><th>Openness</th><th>Checks</th><th>Most open search</th><th>Last checked</th></tr></thead>
<tbody>{leaderboard_rows(b.get("leaderboard", []))}</tbody></table></div></section>''' if b.get("leaderboard") else ''}

<section><h2>Timing signals</h2><div class="grid2">{signal_list(b['signals'])}</div></section>

{kit_section(b)}

<section class="tactic"><span class="eyebrow">Profile tactic of the day</span><p>{escape(b['tactic'])}</p></section>

<section class="note"><h3>Guardrails for every profile</h3><ul>{''.join(f'<li>{escape(g)}</li>' for g in GUARDRAILS)}</ul></section>

<section><h2>Watchlist</h2><div class="table"><table>
<thead><tr><th>Keyword</th><th>Score</th><th>Trend</th><th>Change</th><th>Play</th><th>First seen</th><th>Last seen</th><th>Pack median reviews</th></tr></thead>
<tbody>{watchlist_rows(b['state']['watchlist'])}</tbody></table></div></section>

{f'<section><details><summary>Earlier briefs</summary><ul style="margin-top:10px">{past}</ul></details></section>' if past else ''}

<footer>
  <p>How to read this: "Surging" means the last 3 months are 25%+ above the same months last year (OpenRush, 24-month
  history). "(seasonal)" means only Semrush's 12-month curve was available, which can't separate a trend from the season.
  Search volumes update monthly; the data month column shows which month the numbers describe.</p>
  <p>{escape(spend_text)}</p>
</footer>
</div>
<script type="application/json" id="scout-state">{state_json}</script>
"""


def render_summary(b):
    lines = [f"GBP Opportunity Scout · {b['weekday']} {b['date']} · {b['label']}"]
    if b["opportunities"]:
        lines.append("")
        lines.append("Today's moves:")
        for i, o in enumerate(b["opportunities"][:3], 1):
            vol = (o.get("openrush") or {}).get("volume") or o["semrush"]["volume"]
            lines.append(f"{i}. {o['keyword']}: {o['play']}, score {o['score']:.0f}, {o['label']} "
                         f"({pct(o['change'])}), {vol:,}/mo. {o['why']}")
    elif b["recap"]:
        lines += ["", "Weekly recap. Top of the watchlist:"]
        for kw, w in sorted(b["state"]["watchlist"].items(), key=lambda kv: -kv[1].get("score", 0))[:5]:
            lines.append(f"- {kw}: {w.get('play')}, score {w.get('score', 0):.0f}, {w.get('label')}")
    weak = [c for checks in b["serps"].values() for c in checks if (c.get("weakness") or 0) >= 0.75]
    if weak:
        lines += ["", "Open map packs (few reviews to beat):"]
        lines += [f"- '{c['query']}' in {c['market']}: median {c['median_reviews']:g} reviews" for c in weak]
    board = b.get("leaderboard") or []
    if board:
        lines += ["", "Most open markets so far: " + "; ".join(
            f"{r['market']} ({r['openness']:.2f}, best: '{r['best_query']}' median {r['best_median']:g})" for r in board[:3])]
    f = b.get("focus")
    if f and f["leaderboard"]:
        lines += ["", f"{f['label']}, most open markets: " + "; ".join(
            f"{r['market']} ({r['best_query']}, median {r['best_median']:g})" for r in f["leaderboard"][:3])]
    for o in b.get("own_listings") or []:
        lines += ["", f"Our listing: {own_line(o)}"] + [f"- Fix: {i}" for i in o["issues"]]
    if b["own_sightings"]:
        lines += ["", "Possibly ours in the map pack (confirm): "
                  + "; ".join(f"{s['name']} ({s['query']})" for s in b["own_sightings"])]
    for key in ("weather", "news", "policy"):
        for s in (b["signals"].get(key) or [])[:2]:
            lines.append(f"- {key.title()}: {s.get('summary') or s.get('headline')}")
    lines += ["", f"Tactic: {b['tactic']}"]
    return "\n".join(lines) + "\n"
