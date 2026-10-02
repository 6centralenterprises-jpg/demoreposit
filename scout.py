#!/usr/bin/env python3
"""Daily GBP Opportunity Scout for 6 Central Enterprises.

    python3 scout.py plan   [--date YYYY-MM-DD]   # today's niches, keywords and credit budget
    python3 scout.py batch  --date D              # after discovery: the Semrush keyword list
    python3 scout.py screen --date D              # after Semrush: what to deep-dive and map-check
    python3 scout.py build  --date D              # after deep dives + signals: brief.html, summary.md
    python3 scout.py restore --date D --html F    # read the watchlist back out of yesterday's published brief

The `gbp-daily-scout` skill runs these steps and saves each tool result into
runs/gbp/<date>/. Volume data refreshes monthly, so each weekday covers a
different group of businesses (see config/gbp_scout.json). Nothing here
creates a Business Profile or contacts anyone.
"""
import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

from gbp_scout import scoring
from gbp_scout.brief import render_html, render_summary

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "gbp_scout.json"
RUNS = ROOT / "runs" / "gbp"
MAX_HISTORY = 30


def load_config():
    return json.loads(CONFIG.read_text())


def run_path(day):
    return RUNS / day


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def payload(obj):
    """Accept either a full OpenRush envelope or just its `data` object."""
    return obj.get("data", obj) if isinstance(obj, dict) else obj


def all_markets(cfg):
    return cfg["markets"]["home"] + cfg["markets"]["roster"]


def todays_markets(cfg, day):
    """Home markets every day, plus the next few roster metros in rotation."""
    roster = cfg["markets"]["roster"]
    per_day = cfg["budget"]["rotating_markets_per_day"]
    start = (datetime.strptime(day, "%Y-%m-%d").toordinal() * per_day) % len(roster) if roster else 0
    rotating = [roster[(start + i) % len(roster)] for i in range(min(per_day, len(roster)))]
    return ([dict(m, role="home") for m in cfg["markets"]["home"]]
            + [dict(m, role="rotating") for m in rotating])


def market_checks(plan, cfg):
    """Which map-pack searches run in which market today."""
    per_rotating = cfg["budget"]["rotating_checks_per_market"]
    return [(m, plan["map_checks"] if m["role"] == "home" else plan["map_checks"][:per_rotating])
            for m in plan["markets"]]


def kit_searches(cfg, cluster, day):
    """Today's Amazon kit searches: the cluster's niche tools first, then rotating basics."""
    ver = cfg["verification"]
    cap = ver["kits_per_day"]
    picks = [dict(it, niche=n) for n in cluster["niches"] for it in ver["niche_items"].get(n, [])]
    common = ver["common_items"]
    start = datetime.strptime(day, "%Y-%m-%d").toordinal() % len(common)
    rotated = common[start:] + common[:start]
    picks = picks[:max(cap - 2, 0)] + [dict(it, niche="every business") for it in rotated]
    return picks[:cap]


def niche_index(cluster):
    index = {}
    for name, niche in cluster["niches"].items():
        for kw in niche["keywords"]:
            index[kw.lower()] = name
    return index


def normalize_kw(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def require_plan(day):
    plan = read_json(run_path(day) / "plan.json")
    if not plan:
        sys.exit(f"No plan for {day}. Run `python3 scout.py plan --date {day}` first.")
    return plan


# -------------------------------------------------------------------- plan

def cmd_plan(args):
    cfg = load_config()
    day = args.date or date.today().isoformat()
    weekday = datetime.strptime(day, "%Y-%m-%d").strftime("%A")
    cluster_id = cfg["rotation"][weekday]
    cluster = cfg["clusters"][cluster_id]
    budget = cfg["budget"]
    out = run_path(day)
    for sub in ("discovery", "keywords", "serp"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    keywords = [kw for n in cluster["niches"].values() for kw in n["keywords"]]
    recap = cluster_id == "weekly-recap"
    credits = cfg["openrush_credits"]
    seeds = cluster["discovery_seeds"][:budget["openrush_research_seeds"]]
    markets = todays_markets(cfg, day)
    checks = sum(budget["openrush_map_pack_checks"] if m["role"] == "home" else budget["rotating_checks_per_market"]
                 for m in markets)
    est = (len(seeds) * credits["research_keywords"]
           + (0 if recap else budget["openrush_deep_dives"] * credits["inspect_keyword"])
           + checks * credits["inspect_serp"])
    plan = {"date": day, "weekday": weekday, "cluster": cluster_id, "label": cluster["label"],
            "recap": recap, "seeds": seeds, "keywords": keywords,
            "kit_searches": kit_searches(cfg, cluster, day),
            "markets": markets, "estimate": {
                "openrush_credits_max": est,
                "semrush_units_max": 0 if recap else budget["semrush_keywords_per_day"] * cfg["semrush_units_per_keyword"]}}
    (out / "plan.json").write_text(json.dumps(plan, indent=2))
    print(f"{day} ({weekday}): {cluster['label']}")
    print(f"Run folder: {out}")
    print("Markets today: " + ", ".join(f"{m['name']} ({m['role']})" for m in markets))
    if recap:
        print("Weekly recap: no new keyword research. Re-check the watchlist leaders' map packs.")
    else:
        print(f"Discovery seeds (save each result to discovery/<seed-slug>.json): {seeds}")
        print(f"Config keywords: {len(keywords)}")
    print("Verification-kit searches (WebSearch, allowed_domains amazon.com; save to kits.json):")
    for k in plan["kit_searches"]:
        print(f"  [{k['niche']} / {k['proof']}] {k['item']}  ->  search: {k['search']}")
    print(f"Budget ceiling: {plan['estimate']['openrush_credits_max']} OpenRush credits, "
          f"{plan['estimate']['semrush_units_max']} Semrush API units")


# ------------------------------------------------------------------- batch

def discovered(day, cfg, plan):
    """New keywords from discovery that pass the filters, best first."""
    out = run_path(day)
    known = {normalize_kw(k) for k in plan["keywords"]}
    stop = [s.lower() for s in cfg["brand_stoplist"]]
    junk = [re.escape(j) for j in cfg["discovery"]["junk_words"]]
    min_volume = cfg["discovery"]["min_volume"]
    seen_shapes, rows = set(), []
    for path in sorted((out / "discovery").glob("*.json")):
        data = payload(read_json(path))
        for item in data.get("keywords", []):
            kw = item["keyword"].lower().strip()
            norm = normalize_kw(kw)
            volume = item.get("monthly_volume") or item.get("volume") or 0
            if (norm in known or volume < min_volume or item.get("intent") in ("navigational", "informational")
                    or any(s in kw for s in stop) or any(re.search(rf"\b{j}\b", kw) for j in junk)):
                continue
            if item.get("trend_12m"):
                shape = (volume, item.get("cpc_usd"), json.dumps(item["trend_12m"], sort_keys=True))
                if shape in seen_shapes:  # "24/7" vs "24 7": the same search counted twice
                    continue
                seen_shapes.add(shape)
            known.add(norm)
            trend = sorted(item.get("trend_12m") or [], key=lambda p: (p["year"], p["month"]))
            values = [p.get("search_volume") or 0 for p in trend]
            momentum = None
            if len(values) == 12 and sum(values[:9]):
                momentum = round((sum(values[9:]) / 3) / (sum(values[:9]) / 9), 2)
            rows.append({"keyword": kw, "volume": volume, "cpc": item.get("cpc_usd") or item.get("cpc") or 0,
                         "momentum_openrush": momentum, "seed": data.get("seed") or path.stem})
    rows.sort(key=lambda r: (-(r["momentum_openrush"] or 0), -r["volume"]))
    return rows[:cfg["discovery"]["max_new_keywords"]]


def cmd_batch(args):
    cfg = load_config()
    plan = require_plan(args.date)
    new = discovered(args.date, cfg, plan)
    room = cfg["budget"]["semrush_keywords_per_day"] - len(plan["keywords"])
    new = new[:max(room, 0)]
    plan["discovered"] = new
    run_path(args.date).joinpath("plan.json").write_text(json.dumps(plan, indent=2))
    phrase = ";".join(plan["keywords"] + [n["keyword"] for n in new])
    print(f"{len(plan['keywords'])} config keywords + {len(new)} discovered = {phrase.count(';') + 1} keywords")
    for n in new:
        print(f"  new: {n['keyword']} ({n['volume']}/mo, momentum {n['momentum_openrush']})")
    print("\nSemrush phrase_these, database us, export_columns "
          "keyword,volume,cpc,competitive_density,trend,intent,keyword_difficulty. phrase:")
    print(phrase)
    print(f"\nSave the returned `data` text to {run_path(args.date) / 'semrush.csv'}")


# ------------------------------------------------------------------ screen

def screened(day, cfg, plan):
    cluster = cfg["clusters"][plan["cluster"]]
    index = niche_index(cluster)
    seed_niche = {}
    for d in plan.get("discovered", []):
        seed_niche[d["keyword"]] = next((n for n, v in cluster["niches"].items()
                                         if any(normalize_kw(d["seed"]) in normalize_kw(k) for k in v["keywords"])),
                                        next(iter(cluster["niches"])))
    csv_path = run_path(day) / "semrush.csv"
    if not csv_path.exists():
        sys.exit(f"Missing {csv_path}. Save the Semrush result there first.")
    rows = []
    for row in scoring.parse_semrush(csv_path.read_text()):
        niche_name = index.get(row["keyword"]) or seed_niche.get(row["keyword"])
        if not niche_name or row["volume"] == 0:
            continue
        row["niche"] = niche_name
        row["discovered"] = row["keyword"] in seed_niche
        row["momentum"] = scoring.semrush_momentum(row["trend"])
        row["screen"] = scoring.screen_score(row, cluster["niches"][niche_name]["home_based_fit"])
        rows.append(row)
    rows.sort(key=lambda r: -r["screen"])
    return rows


def pick_deep_dives(rows, limit, per_niche=2):
    picks, count = [], {}
    for r in rows:
        if count.get(r["niche"], 0) >= per_niche:
            continue
        picks.append(r)
        count[r["niche"]] = count.get(r["niche"], 0) + 1
        if len(picks) == limit:
            break
    return picks


def cmd_screen(args):
    cfg = load_config()
    plan = require_plan(args.date)
    budget = cfg["budget"]
    out = run_path(args.date)
    if plan["recap"]:
        state = read_json(out / "prev_state.json", {}) or {}
        leaders = sorted(state.get("watchlist", {}).items(), key=lambda kv: -kv[1].get("score", 0))
        checks = [scoring.local_query(k) for k, v in leaders if v.get("play") != "Watch"]
        checks = checks[:budget["openrush_map_pack_checks"]]
        plan.update(deep_dives=[], map_checks=checks)
    else:
        rows = screened(args.date, cfg, plan)
        dives = pick_deep_dives(rows, budget["openrush_deep_dives"])
        plan.update(deep_dives=[r["keyword"] for r in dives],
                    map_checks=[scoring.local_query(r["keyword"]) for r in dives][:budget["openrush_map_pack_checks"]])
        (out / "screen.json").write_text(json.dumps(rows, indent=2))
        print(f"Screened {len(rows)} keywords. Top 10:")
        for r in rows[:10]:
            print(f"  {r['screen']:5.1f}  {r['keyword']}  vol {r['volume']}  cpc ${r['cpc']}  "
                  f"3-vs-9 {r['momentum']}  [{r['niche']}]")
    out.joinpath("plan.json").write_text(json.dumps(plan, indent=2))
    print("\nDeep dives (OpenRush inspect_keyword, save `data` to keywords/<slug>.json):")
    for k in plan["deep_dives"]:
        print(f"  {k}  ->  keywords/{scoring.slug(k)}.json")
    print("Map-pack checks (OpenRush inspect_serp, save `data` to the path shown):")
    for m, queries in market_checks(plan, cfg):
        for q in queries:
            print(f"  '{q}' @ {m['serp_location']}  ->  serp/{scoring.slug(m['name'])}__{scoring.slug(q)}.json")


# ------------------------------------------------------------------- build

def build(day, cfg):
    plan = require_plan(day)
    out = run_path(day)
    cluster = cfg["clusters"][plan["cluster"]]
    prev = read_json(out / "prev_state.json", {}) or {}
    watch = prev.get("watchlist", {})
    signals = read_json(out / "signals.json", {}) or {}
    signals = {k: [s for s in v if s.get("source")] for k, v in signals.items() if isinstance(v, list)}

    serps = {}
    for path in sorted((out / "serp").glob("*.json")):
        data = payload(read_json(path))
        market_slug, _, q = path.stem.partition("__")
        market = next((m["name"] for m in all_markets(cfg) if scoring.slug(m["name"]) == market_slug), market_slug)
        result = scoring.pack_weakness(data, cfg["own_brand_markers"])
        result.update(query=data.get("query") or q.replace("-", " "), market=market,
                      fetched_at=data.get("fetched_at"))
        serps.setdefault(scoring.slug(result["query"]), []).append(result)

    opportunities = []
    if not plan["recap"]:
        rows = {r["keyword"]: r for r in read_json(out / "screen.json", [])}
        for kw in plan.get("deep_dives", []):
            row = rows.get(kw)
            if not row:
                continue
            niche = cluster["niches"][row["niche"]]
            raw = payload(read_json(out / "keywords" / f"{scoring.slug(kw)}.json", {}) or {})
            deep = scoring.yoy(raw.get("trend")) if raw else None
            if deep is not None:
                deep.update(volume=raw.get("monthly_volume"), cpc=raw.get("cpc_usd"))
            checks = serps.get(scoring.slug(scoring.local_query(kw)), [])
            weak_values = [c["weakness"] for c in checks if c.get("weakness") is not None]
            serp_summary = {"weakness": max(weak_values)} if weak_values else None
            score, parts, change, trend_source = scoring.opportunity(row, niche, deep, serp_summary)
            play, why = scoring.play_for(score, niche, serp_summary and serp_summary["weakness"], change)
            opportunities.append({
                "keyword": kw, "niche": row["niche"], "portfolio": niche["portfolio"],
                "licensed": niche.get("licensed", False), "discovered": row.get("discovered", False),
                "score": score, "parts": parts, "change": change, "trend_source": trend_source,
                "label": scoring.label(change), "play": play, "why": why,
                "semrush": {"volume": row["volume"], "cpc": row["cpc"], "kd": row["kd"], "momentum": row["momentum"]},
                "openrush": deep, "map_packs": checks, "new": kw not in watch})
        opportunities.sort(key=lambda o: (scoring.PLAY_ORDER[o["play"]], -o["score"]))

    # Merge today into the watchlist.
    for o in opportunities:
        entry = watch.get(o["keyword"], {"first_seen": day, "history": []})
        entry.update(niche=o["niche"], cluster=plan["label"], last_seen=day, label=o["label"],
                     score=o["score"], change=o["change"], play=o["play"])
        entry["history"] = (entry["history"] + [[day, o["score"], o["change"]]])[-MAX_HISTORY:]
        watch[o["keyword"]] = entry
    for slug_key, checks in serps.items():  # recap days refresh map-pack readings on the watchlist
        for kw, entry in watch.items():
            if scoring.slug(scoring.local_query(kw)) == slug_key:
                entry["last_pack"] = {"date": day, "median_reviews": checks[0].get("median_reviews"),
                                      "weakness": checks[0].get("weakness")}

    # Market leaderboard: every map-pack reading, per market, so the best places surface over time.
    board = prev.get("markets", {})
    for checks in serps.values():
        for c in checks:
            if c.get("weakness") is None:
                continue
            readings = [r for r in board.get(c["market"], []) if not (r["date"] == day and r["query"] == c["query"])]
            readings.append({"date": day, "query": c["query"], "median": c["median_reviews"], "weakness": c["weakness"]})
            board[c["market"]] = readings[-60:]

    top = [{"keyword": o["keyword"], "score": o["score"], "label": o["label"], "play": o["play"]}
           for o in opportunities[:3]]
    briefs = [b for b in prev.get("briefs", []) if b.get("date") != day]
    briefs = ([{"date": day, "label": plan["label"], "top": top}] + briefs)[:MAX_HISTORY]
    state = {"version": 1, "updated": day, "watchlist": watch, "briefs": briefs, "markets": board}

    own_sightings = [dict(p, query=c["query"], market=c["market"])
                     for checks in serps.values() for c in checks for p in c["pack"] if p["possibly_ours"]]
    kits = [k for k in read_json(out / "kits.json", []) or []
            if "amazon.com" in (k.get("url") or "") and k.get("title")]
    tactic = cfg["playbook"][datetime.strptime(day, "%Y-%m-%d").toordinal() % len(cfg["playbook"])]
    brief = {"date": day, "weekday": plan["weekday"], "label": plan["label"], "recap": plan["recap"],
             "markets": [m["name"] for m in plan["markets"]], "leaderboard": scoring.leaderboard(board),
             "opportunities": opportunities,
             "serps": serps, "signals": signals, "kits": kits, "verification": cfg["verification"], "own_sightings": own_sightings, "tactic": tactic,
             "spend": read_json(out / "spend.json", {}), "state": state}
    return brief


def cmd_build(args):
    cfg = load_config()
    brief = build(args.date, cfg)
    out = run_path(args.date)
    (out / "state.json").write_text(json.dumps(brief["state"], indent=2))
    (out / "brief.html").write_text(render_html(brief))
    (out / "summary.md").write_text(render_summary(brief))
    print((out / "summary.md").read_text())
    print(f"\nWrote {out / 'brief.html'}")


def cmd_restore(args):
    """Pull the scout-state JSON out of a previously published brief.html."""
    html = Path(args.html).read_text()
    match = re.search(r'<script type="application/json" id="scout-state">(.*?)</script>', html, re.S)
    out = run_path(args.date)
    out.mkdir(parents=True, exist_ok=True)
    if not match:
        print("No saved state in that page. Starting a fresh watchlist.")
        return
    state = json.loads(match.group(1).replace("<\\/", "</"))
    (out / "prev_state.json").write_text(json.dumps(state, indent=2))
    print(f"Restored {len(state.get('watchlist', {}))} watchlist keywords and "
          f"{len(state.get('briefs', []))} past briefs (last update {state.get('updated')}).")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--date")
    p.set_defaults(func=cmd_plan)
    p = sub.add_parser("restore")
    p.add_argument("--date", required=True)
    p.add_argument("--html", required=True)
    p.set_defaults(func=cmd_restore)
    for name, func in (("batch", cmd_batch), ("screen", cmd_screen), ("build", cmd_build)):
        p = sub.add_parser(name)
        p.add_argument("--date", required=True)
        p.set_defaults(func=func)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
