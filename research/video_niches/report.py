"""Build the niche-audit page from runs/video-niches/ranked.json.

Usage: python3 research/video_niches/report.py [frame.jpg]
Writes runs/video-niches/niche-audit.html. The optional frame is the video still embedded in the header.
"""
import base64
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs" / "video-niches"
HERE = ROOT / "research" / "video_niches"

# The on-screen Notepad list, in the order it appears in the video.
SCREEN = ["passenger van rental", "escape room", "haunted houses", "auditions", "golf courses", "private equity firms",
          "credit union", "homeschool program", "passport", "grocery delivery", "airports", "makeup artist",
          "celebrity hair stylist", "celebrity makeup artist", "celebrity nanny agency", "celebrity nutritionist",
          "celebrity personal trainer", "celebrity PR", "celebrity publicist", "celebrity realtors", "celebrity tours",
          "comedians", "illustrator", "music marketing company", "mobile DJ", "translation services",
          "celebrity impersonators", "flyboarding", "parasailing", "adult entertainment", "screenwriting",
          "kitesurfing lessons", "call centers", "barber school", "cosmetology beauty school", "carports",
          "room additions", "pool deck resurfacing", "patio covers", "art consultant", "music consultant", "loctician"]

VERIFY_TEXT = {}
VERIFY_NAME = {"own": "A · Verify & own it", "own-licensed": "B · Own it, licensed staff do the work",
               "office": "C · Needs a real office", "partner": "D · Partner's profile, we own the site",
               "no": "F · Can't be verified"}
VERDICT_CLASS = {"Pursue": "go", "Test": "test", "Pass": "pass", "Avoid": "off", "Off-limits": "off"}
SOURCE_LABEL = {"screen": "On screen", "spoken": "Said aloud", "adjacent": "Found by us"}


def num(v):
    return "–" if v in (None, "") else f"{v:,.0f}" if isinstance(v, (int, float)) else escape(str(v))


def pct(v):
    return "–" if v is None else f"{v * 100:+.0f}%"


def packs_cell(r):
    if r["channel"] == "online":
        return '<span class="muted">Sold online (no map pack)</span>'
    bits = []
    for p in r["packs"]:
        city = escape(p["market"].split(",")[0])
        if p.get("error"):
            bits.append(f"{city}: <span class='muted'>{escape(str(p['error']))}</span>")
        elif p.get("median") is None:
            bits.append(f"{city}: <span class='muted'>no pack</span>")
        else:
            bits.append(f"{city}: <strong>{num(p['median'])}</strong>")
    return "<br>".join(bits) or "–"


def risk_cell(r):
    risk = r.get("risk")
    if not risk:
        return '<span class="muted">none flagged</span>'
    cls = {"high": "v-off", "medium": "v-test", "low": "v-pass"}.get(risk["level"], "v-pass")
    return f'<span class="tag {cls}">{escape(risk["level"])}</span> <span class="muted">{escape(risk.get("what") or "")}</span>'


def build(frame=None):
    rows = json.loads((RUNS / "ranked.json").read_text())
    VERIFY_TEXT.update({k: v for k, v in json.loads((HERE / "assessment.json").read_text())["_verify"].items()})
    picks = json.loads((HERE / "picks.json").read_text()) if (HERE / "picks.json").exists() else {}
    by_name = {r["niche"]: r for r in rows}
    counts = {v: sum(1 for r in rows if r["verdict"] == v) for v in VERDICT_CLASS}
    counts["Off-limits"] += counts.pop("Avoid", 0)

    # Annotated Notepad list
    words = []
    for name in SCREEN:
        r = by_name.get(name)
        cls = VERDICT_CLASS[r["verdict"]] if r else "pass"
        words.append(f'<mark class="v-{cls}" title="{escape(r["verdict"] if r else "")}">{escape(name)}</mark> + City')
    notepad = ", ".join(words)

    cards = []
    for name, p in picks.items():
        r = by_name.get(name)
        if not r:
            continue
        cards.append(f"""<article class="pick">
  <div class="pick-head"><span class="tag v-{VERDICT_CLASS[r['verdict']]}">{escape(r['verdict'])}</span>
  <span class="src">{escape(SOURCE_LABEL[r['source']])}</span><span class="score">{r['score']:.0f}</span></div>
  <h3>{escape(p.get('title', name))}</h3>
  <p class="facts">{num(r['vol_national'])} searches/mo (US) · ${r['cpc']:.2f} CPC · KD {num(r['kd'])}{' · ' + pct(r['yoy']) + ' YoY' if r['yoy'] is not None else ''}</p>
  <p class="facts">{packs_cell(r)}</p>
  <p>{escape(p['why'])}</p>
  <p><strong>How 6 Central does it:</strong> {escape(p.get('model', r['model']))}</p>
  <p class="lic"><strong>Check first:</strong> {escape(p.get('license', r['license']))}</p>
  <p class="next"><strong>Next step:</strong> {escape(p['next'])}</p>
</article>""")

    table_rows = []
    for i, r in enumerate(rows, 1):
        v = VERDICT_CLASS[r["verdict"]]
        table_rows.append(f"""<tr data-verdict="{v}" data-source="{escape(r['source'])}">
<td class="n">{i}</td><td><strong>{escape(r['niche'])}</strong><br><span class="muted">{escape(r['kw_national'])}</span></td>
<td>{escape(SOURCE_LABEL[r['source']])}</td><td><span class="tag v-{v}">{escape(r['verdict'])}</span></td>
<td class="n">{r['score']:.0f}</td><td><span class="grade g-{r['grade']}">{r['grade']}</span></td>
<td><span class="grade g-{r['verify_grade']}" title="{escape(VERIFY_TEXT[r['verify']])}">{r['verify_grade']}</span></td><td class="n">{num(r['vol_national'])}</td><td class="n">{num(r['vol_chicago']) if r.get('kw_chicago') else '–'}</td>
<td class="n">${r['cpc']:.2f}</td><td class="n">{num(r['kd'])}</td><td class="n">{pct(r['yoy'])}</td>
<td>{packs_cell(r)}</td><td>{risk_cell(r)}</td><td class="note">{escape(r['note'])}</td></tr>""")

    # Grade board: verification path (rows) x opportunity grade (chips sorted best first)
    board = []
    for key in ["own", "own-licensed", "office", "partner", "no"]:
        group = sorted([r for r in rows if r["verify"] == key], key=lambda r: (r["grade"], -r["score"]))
        chips = "".join(f'<span class="chip"><span class="grade g-{r["grade"]}">{r["grade"]}</span>{escape(r["niche"])}</span>'
                        for r in group)
        board.append(f"""<div class="lane"><div class="lane-head"><span class="grade g-{group[0]['verify_grade'] if group else 'F'}">{(group[0]['verify_grade'] if group else 'F')}</span>
<div><h3>{escape(VERIFY_NAME[key].split(' · ')[1])}</h3><p class="muted">{escape(VERIFY_TEXT[key].split(': ', 1)[1])}</p></div></div>
<div class="chips">{chips}</div></div>""")
    off = [r for r in rows if r["verdict"] == "Off-limits"]
    off_items = "".join(f"<li><strong>{escape(r['niche'])}</strong>: {escape(r['note'])}</li>" for r in off)
    img = ""
    if frame and Path(frame).exists():
        data = base64.b64encode(Path(frame).read_bytes()).decode()
        img = (f'<figure class="frame"><img src="data:image/jpeg;base64,{data}" alt="Frame from the video showing the '
               f'BONUS DROP SERVICING NICHES list in Notepad"><figcaption>The list as shown on screen (frame at the '
               f'halfway point of the video).</figcaption></figure>')

    template = (HERE / "report_template.html").read_text()
    return (template.replace("{{NOTEPAD}}", notepad).replace("{{FRAME}}", img).replace("{{PICKS}}", "\n".join(cards)).replace("{{BOARD}}", "\n".join(board))
            .replace("{{ROWS}}", "\n".join(table_rows)).replace("{{OFF}}", off_items)
            .replace("{{DATE}}", "October 4, 2026").replace("{{N_TOTAL}}", str(len(rows))).replace("{{N_SCREEN}}", str(sum(r['source'] == 'screen' for r in rows)))
            .replace("{{N_SPOKEN}}", str(sum(r['source'] == 'spoken' for r in rows)))
            .replace("{{N_ADJ}}", str(sum(r['source'] == 'adjacent' for r in rows)))
            .replace("{{N_GO}}", str(counts["Pursue"])).replace("{{N_TEST}}", str(counts["Test"]))
            .replace("{{N_PASS}}", str(counts["Pass"])).replace("{{N_OFF}}", str(counts["Off-limits"])))


if __name__ == "__main__":
    out = RUNS / "niche-audit.html"
    out.write_text(build(sys.argv[1] if len(sys.argv) > 1 else None))
    print(f"Wrote {out}")
