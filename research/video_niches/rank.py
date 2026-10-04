"""Rank every niche from the drop-servicing video on demand, value, map-pack openness and 6 Central fit.

Inputs (raw research stays in runs/, which is gitignored):
  research/video_niches/niches.json       niche list, keywords, map queries and markets
  research/video_niches/assessment.json   legitimacy gate, fit and license notes
  runs/video-niches/semrush_national.csv  Semrush phrase_these, "near me" / national forms
  runs/video-niches/semrush_chicago.csv   Semrush phrase_these, "<niche> chicago" forms
  research/video_niches/adjacent.json     similar niches found by applying the video's principles
  runs/video-niches/semrush_adjacent.csv  Semrush phrase_these for the adjacent niches
  runs/video-niches/serp/*.json           OpenRush inspect_serp map packs
  runs/video-niches/keywords/*.json       OpenRush inspect_keyword 24-month trends (optional)

Online-sold niches (channel "online") have no map pack to win, so their "openness" points come from
Semrush keyword difficulty instead: 25 at KD 0, falling to 0 at KD 60.

Output: runs/video-niches/ranked.json, plus a printed table.
"""
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gbp_scout import scoring  # noqa: E402

HERE = ROOT / "research" / "video_niches"
RUNS = ROOT / "runs" / "video-niches"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def semrush(path):
    rows = {r["keyword"]: r for r in scoring.parse_semrush(path.read_text())} if path.exists() else {}
    return rows


def log_scale(volume, floor, ceiling, points):
    if not volume or volume <= floor:
        return 0.0
    return min(points, points * (math.log10(volume) - math.log10(floor)) / (math.log10(ceiling) - math.log10(floor)))


def verdict(gate, score):
    if gate != "ok":
        return "Off-limits"
    if score >= 60:
        return "Pursue"
    if score >= 45:
        return "Test"
    return "Pass"


def main():
    niches = json.loads((HERE / "niches.json").read_text())
    adjacent = HERE / "adjacent.json"
    if adjacent.exists():
        niches += json.loads(adjacent.read_text())
    judged = json.loads((HERE / "assessment.json").read_text())
    nat, chi = semrush(RUNS / "semrush_national.csv"), semrush(RUNS / "semrush_chicago.csv")
    nat.update(semrush(RUNS / "semrush_adjacent.csv"))
    out = []
    for n in niches:
        a = judged[n["niche"]]
        kn, kc = nat.get(n["kw_national"]), chi.get(n.get("kw_chicago"))
        trend_file = RUNS / "keywords" / f"{slug(n['kw_national'])}.json"
        deep = json.loads(trend_file.read_text()) if trend_file.exists() else {}
        change = scoring.yoy(deep.get("trend")) if deep.get("trend") else None
        packs = []
        for market in n["markets"]:
            path = RUNS / "serp" / f"{slug(market.split(',')[0])}__{slug(n['map_query'])}.json"
            data = json.loads(path.read_text()) if path.exists() else {"error": "not checked"}
            if data.get("error"):
                packs.append({"market": market, "error": data["error"]})
                continue
            pw = scoring.pack_weakness(data)
            packs.append({"market": market, "median": pw.get("median_reviews"), "openness": pw["weakness"],
                          "pack_size": len(data.get("local_pack") or []),
                          "local_services_ads": bool(data.get("has_local_services")),
                          "paid": data.get("paid_count", 0),
                          "reviews": [p["reviews"] for p in pw["pack"]]})
        vol_n = kn["volume"] if kn else 0
        vol_c = kc["volume"] if kc else 0
        cpc = max((kn or {}).get("cpc") or 0, (kc or {}).get("cpc") or 0)
        if kc is not None:
            demand = 0.7 * log_scale(vol_n, 100, 1_000_000, 30) + 0.3 * log_scale(vol_c, 10, 10_000, 30)
        else:  # adjacent niches: national volume only
            demand = log_scale(vol_n, 100, 1_000_000, 30)
        value = min(15.0, cpc / 12 * 15)
        opens = [p["openness"] for p in packs if p.get("openness") is not None]
        online = n.get("channel") == "online"
        kd = (kn or {}).get("kd")
        if online:
            openness = 25 * max(0.0, (60 - (kd or 60)) / 60)
        else:
            openness = 25 * max(opens) if opens else 0.0
        yoy = change["yoy"] if change else None
        momentum = 0.0 if yoy is None else (5.0 if yoy >= 0.25 else 3.0 if yoy >= 0.10 else -5.0 if yoy <= -0.15 else 0.0)
        fit = 3 * a["fit"]
        score = round(demand + value + openness + fit + momentum, 1)
        out.append({"niche": n["niche"], "source": n["source"], "gate": a["gate"], "fit": a["fit"],
                    "kw_national": n["kw_national"], "vol_national": vol_n, "kd": (kn or {}).get("kd"),
                    "kw_chicago": n.get("kw_chicago"), "vol_chicago": vol_c, "cpc": cpc, "channel": "online" if online else "local",
                    "yoy": yoy, "trend_month": change["latest_month"] if change else None,
                    "packs": packs, "parts": {"demand": round(demand, 1), "value": round(value, 1),
                                              "openness": round(openness, 1), "fit": fit,
                                              "momentum": momentum},
                    "score": score, "verdict": verdict(a["gate"], score),
                    "model": a["model"], "license": a["license"], "note": a["note"]})
    order = {"Pursue": 0, "Test": 1, "Pass": 2, "Off-limits": 3}
    out.sort(key=lambda r: (order[r["verdict"]], -r["score"]))
    (RUNS / "ranked.json").write_text(json.dumps(out, indent=1))
    for i, r in enumerate(out, 1):
        meds = ", ".join(f"{p['market'].split(',')[0]} {p.get('median', p.get('error'))}" for p in r["packs"])
        y = "" if r["yoy"] is None else f" yoy {r['yoy']:+.0%}"
        print(f"{i:2} {r['verdict']:10} {r['score']:5} {r['niche']:28} nat {r['vol_national']:>7} chi {r['vol_chicago']:>5} "
              f"cpc {r['cpc']:>5} kd {r['kd']}{y} | {meds or r['channel']}")


if __name__ == "__main__":
    main()
