#!/usr/bin/env python3
"""Daily GBP Opportunity Scout for 6 Central Enterprises.

    python3 scout.py plan   [--date YYYY-MM-DD]   # today's niches, keywords and credit budget
    python3 scout.py batch  --date D              # after discovery: the Semrush keyword list
    python3 scout.py screen --date D              # after Semrush: what to deep-dive and map-check
    python3 scout.py build  --date D              # after deep dives + signals: brief.html, summary.md
    python3 scout.py restore --date D --html F    # read the watchlist back out of yesterday's published brief
    python3 scout.py register-sync --date D       # copy watch items the run promoted into research/google/risk_register.json

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
    return cfg["markets"]["home"] + cfg["markets"]["roster"] + (cfg["markets"].get("international") or [])


def market_country(m):
    return m.get("country", "United States")


def localize(query, market):
    """Spell a US search the way the market searches it ('mobile tire repair' -> 'mobile tyre repair')."""
    words = market.get("spelling") or {}
    return " ".join(words.get(w, w) for w in query.split()) if words else query


def todays_markets(cfg, day):
    """Home markets every day, plus the next few roster metros in rotation."""
    roster = cfg["markets"]["roster"]
    per_day = cfg["budget"]["rotating_markets_per_day"]
    start = (datetime.strptime(day, "%Y-%m-%d").toordinal() * per_day) % len(roster) if roster else 0
    rotating = [roster[(start + i) % len(roster)] for i in range(min(per_day, len(roster)))]
    intl = cfg["markets"].get("international") or []
    per_intl = cfg["budget"].get("international_markets_per_day", 0)
    abroad = []
    if intl and per_intl:
        start = (datetime.strptime(day, "%Y-%m-%d").toordinal() * per_intl) % len(intl)
        abroad = [intl[(start + i) % len(intl)] for i in range(min(per_intl, len(intl)))]
    return ([dict(m, role="home") for m in cfg["markets"]["home"]]
            + [dict(m, role="rotating") for m in rotating]
            + [dict(m, role="international") for m in abroad])


def market_checks(plan, cfg):
    """Which map-pack searches run in which market today."""
    per_rotating = cfg["budget"]["rotating_checks_per_market"]
    focus = cfg.get("focus") or {}
    out = []
    for m in plan["markets"]:
        if m.get("role") == "international":  # the cluster's top searches, spelled the local way; no focus, no own listings
            out.append((m, [localize(q, m) for q in plan["map_checks"][:per_rotating]]))
            continue
        queries = list(plan["map_checks"] if m["role"] == "home" else plan["map_checks"][:per_rotating])
        focus_q = focus_query(cfg, plan.get("date"))
        allowed = (focus.get("query_states") or {}).get(focus_q)  # no snow-removal check in Phoenix
        if focus_q and focus_q not in queries and (allowed is None or m.get("state") in allowed):
            queries.append(focus_q)  # standing focus watch: one search per market per day
        for listing in cfg.get("own_listings", []):  # our own listings are tracked every day
            if listing["market"] == m["name"] and listing["track_query"] not in queries:
                queries.append(listing["track_query"])
        out.append((m, queries))
    return out


def base_checks(cfg, day):
    """Target bases checked today: every daily base, plus the rotating bases taking turns.

    Returns a list of (base, query, relative serp path)."""
    bases = (cfg.get("bases") or {}).get("list") or []
    daily = [b for b in bases if b.get("cadence", "daily") == "daily"]
    rotating = [b for b in bases if b.get("cadence") == "rotating"]
    per_day = (cfg.get("bases") or {}).get("daily_rotating", 1)
    todays = list(daily)
    if rotating and day:
        start = (datetime.strptime(day, "%Y-%m-%d").toordinal() * per_day) % len(rotating)
        todays += [rotating[(start + i) % len(rotating)] for i in range(min(per_day, len(rotating)))]
    out = []
    for b in todays:
        for q in b["queries"]:
            out.append((b, q, f"serp/base__{scoring.slug(b['name'])}__{scoring.slug(q)}.json"))
    return out


def focus_query(cfg, day):
    """Today's standing-watch map search (alternates daily between the focus searches)."""
    queries = (cfg.get("focus") or {}).get("map_queries") or []
    if not queries or not day:
        return None
    return queries[datetime.strptime(day, "%Y-%m-%d").toordinal() % len(queries)]


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
    checks += sum(1 for m in markets if m["role"] != "international") * bool(focus_query(cfg, day))
    checks += len(cfg.get("own_listings", [])) + len(base_checks(cfg, day))
    abroad = [m for m in markets if m["role"] == "international"]
    demand_checks = budget.get("international_demand_checks", 0) if abroad else 0
    est = (len(seeds) * credits["research_keywords"]
           + (0 if recap else budget["openrush_deep_dives"] * credits["inspect_keyword"])
           + demand_checks * credits["inspect_keyword"]
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
    for m in abroad:
        spelled = ", ".join(f"{a} -> {b}" for a, b in (m.get("spelling") or {}).items()) or "US spelling"
        print(f"International today: {m['name']} ({market_country(m)}; {spelled}). Map packs ranked separately; "
              f"the play abroad is always Partner & manage.")
    if recap:
        print("Weekly recap: no new keyword research. Re-check the watchlist leaders' map packs.")
    else:
        print(f"Discovery seeds (save each result to discovery/<seed-slug>.json): {seeds}")
        print(f"Config keywords: {len(keywords)}")
    if focus_query(cfg, day):
        print(f"Focus watch ({cfg['focus']['label']}): '{focus_query(cfg, day)}' map pack in every market today")
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
    elif (out / "semrush.csv").exists():
        rows = screened(args.date, cfg, plan)
        dives = pick_deep_dives(rows, budget["openrush_deep_dives"])
        plan.update(deep_dives=[r["keyword"] for r in dives],
                    map_checks=[scoring.local_query(r["keyword"]) for r in dives][:budget["openrush_map_pack_checks"]])
        (out / "screen.json").write_text(json.dumps(rows, indent=2))
        print(f"Screened {len(rows)} keywords. Top 10:")
        for r in rows[:10]:
            print(f"  {r['screen']:5.1f}  {r['keyword']}  vol {r['volume']}  cpc ${r['cpc']}  "
                  f"3-vs-9 {r['momentum']}  [{r['niche']}]")
    else:  # Semrush unavailable (no units, tool down): keep the day alive on OpenRush alone
        dives = fallback_deep_dives(cfg, plan, out, budget["openrush_deep_dives"])
        plan.update(deep_dives=dives, screen_source="openrush-fallback",
                    map_checks=[scoring.local_query(k) for k in dives][:budget["openrush_map_pack_checks"]])
        print("No semrush.csv saved, so there is no Semrush screen today. Falling back to OpenRush: deep-dive the "
              "cluster's best-known keywords directly (volume and CPC come from inspect_keyword; the Semrush "
              "columns stay blank). Say so in the report.")
    out.joinpath("plan.json").write_text(json.dumps(plan, indent=2))
    print("\nDeep dives (OpenRush inspect_keyword, save `data` to keywords/<slug>.json):")
    for k in plan["deep_dives"]:
        print(f"  {k}  ->  keywords/{scoring.slug(k)}.json")
    print("Map-pack checks (OpenRush inspect_serp, save `data` to the path shown):")
    for m, queries in market_checks(plan, cfg):
        for q in queries:
            print(f"  '{q}' @ {m['serp_location']}  ->  serp/{scoring.slug(m['name'])}__{scoring.slug(q)}.json")
    abroad = [m for m in plan["markets"] if m.get("role") == "international"]
    if abroad and cfg["budget"].get("international_demand_checks", 0):
        print("International demand (OpenRush inspect_keyword is country-level: pass the country as the location; "
              "save `data` to the path shown):")
        for m in abroad:
            for q in [localize(q, m) for q in plan["map_checks"]][:cfg["budget"]["international_demand_checks"]]:
                print(f"  '{q}' @ {market_country(m)}  ->  keywords/intl__{scoring.slug(market_country(m))}__{scoring.slug(q)}.json")
    print("Target-base checks (our planned bases, every day; same tool, same save format):")
    for b, q, path in base_checks(cfg, args.date):
        print(f"  '{q}' @ {b['serp_location']}  ->  {path}")


def fallback_deep_dives(cfg, plan, out, limit):
    """Without a Semrush screen, deep-dive the cluster's keywords we already know best (watchlist score first)."""
    cluster = cfg["clusters"][plan["cluster"]]
    watch = (read_json(out / "prev_state.json", {}) or {}).get("watchlist", {})
    rows = [{"keyword": kw, "niche": n, "score": watch.get(kw, {}).get("score", 0), "order": i}
            for i, (n, v) in enumerate(cluster["niches"].items()) for kw in v["keywords"]]
    rows.sort(key=lambda r: (-r["score"], r["order"]))
    return [r["keyword"] for r in pick_deep_dives(rows, limit)]


def openrush_row(kw, raw, cluster):
    """A screen row built from an OpenRush deep dive alone, for days when Semrush is unavailable."""
    niche = niche_index(cluster).get(kw)
    if not niche:
        return None
    trend = sorted(raw.get("trend") or [], key=lambda p: (p["year"], p["month"]))
    values = [p.get("search_volume") or 0 for p in trend][-12:]
    momentum = round((sum(values[9:]) / 3) / (sum(values[:9]) / 9), 2) if len(values) == 12 and sum(values[:9]) else None
    return {"keyword": kw, "volume": raw.get("monthly_volume") or 0, "cpc": raw.get("cpc_usd") or 0, "kd": None,
            "momentum": momentum, "trend": values, "niche": niche, "discovered": False, "source": "openrush"}


def international_demand(out, day):
    """Country-level OpenRush keyword reads saved as keywords/intl__<country>__<query>.json."""
    reads = []
    for path in sorted((out / "keywords").glob("intl__*.json")):
        raw = payload(read_json(path) or {})
        if not raw.get("keyword"):
            continue
        yoy = scoring.yoy(raw.get("trend")) or {}
        reads.append({"keyword": raw["keyword"], "country": raw.get("location"), "volume": raw.get("monthly_volume"),
                      "cpc": raw.get("cpc_usd"), "yoy": yoy.get("yoy"), "latest_month": yoy.get("latest_month"),
                      "season": scoring.season_ahead(raw.get("trend"), day)})
    return reads


def best_picks(cfg, day, opportunities, watch, board, demand):
    """The three picks Terell asked for (2026-10-13): best seasonal, best nationwide, best international."""
    countries = {m["name"]: market_country(m) for m in all_markets(cfg)}
    states = {m["name"]: m.get("state") for m in all_markets(cfg)}
    home = {m["name"] for m in cfg["markets"]["home"]}
    focus = cfg.get("focus") or {}
    focus_qs = {scoring.slug(q): q for q in focus.get("map_queries", [])}
    query_states = focus.get("query_states") or {}
    by_slug = {}
    for kw, w in watch.items():
        by_slug.setdefault(scoring.slug(scoring.local_query(kw)), []).append((kw, w))

    seen, cands = set(), []
    for o in opportunities:
        s = o.get("season") or {}
        if s.get("ratio", 0) >= 1.3 and o["play"] != "Avoid":
            cands.append({"keyword": o["keyword"], "niche": o["niche"], "score": o["score"], "play": o["play"],
                          "ratio": s["ratio"], "peak_month": s.get("peak_month"), "peak_volume": s.get("peak_volume"),
                          "as_of": day})
            seen.add(o["keyword"])
    for kw, w in watch.items():
        s = w.get("season") or {}
        if kw not in seen and s.get("ratio", 0) >= 1.3 and w.get("play") != "Avoid":
            cands.append({"keyword": kw, "niche": w.get("niche"), "score": w.get("score", 0), "play": w.get("play", "Watch"),
                          "ratio": s["ratio"], "peak_month": s.get("peak_month"), "peak_volume": s.get("peak_volume"),
                          "as_of": w.get("last_seen")})
    # An actionable play beats a bigger spike we can't act on (a cooling "Watch" keyword).
    cands.sort(key=lambda c: (scoring.PLAY_ORDER.get(c["play"], 3), -(c["ratio"] * max(c["score"] or 0, 1))))
    seasonal = None
    if cands:
        c = cands[0]
        peak = f", peaking in {c['peak_month']} ({c['peak_volume']:,} searches, OpenRush)" if c.get("peak_volume") else ""
        seasonal = dict(c, why=(f"Last year the next 3 months ran {c['ratio']:.1f}x this month{peak}. Play: {c['play']}. "
                                f"Launch or sign the partner now so the profile has reviews before the peak."),
                        also=[f"{x['keyword']} ({x['ratio']:.1f}x, {x['play']})" for x in cands[1:3]])

    def candidates(keep):
        rows = []
        for market, readings in board.items():
            if not keep(market):
                continue
            for r in readings:
                if r.get("weakness") is None:
                    continue
                sl = scoring.slug(r["query"])
                matches = by_slug.get(sl, [])
                best = max(matches, key=lambda kv: kv[1].get("score", 0), default=None)
                if not best and sl not in focus_qs:
                    continue  # only searches we have demand numbers for, or the standing watch
                if not best and query_states.get(focus_qs[sl]) and states.get(market) not in query_states[focus_qs[sl]]:
                    continue  # snow removal in Phoenix is open because nobody needs it
                kw, w = best if best else (r["query"], {})
                rows.append({"query": r["query"], "market": market, "country": countries.get(market, "United States"),
                             "median": r["median"], "weakness": r["weakness"], "date": r["date"], "keyword": kw,
                             "score": w.get("score"), "play": w.get("play"), "verify": w.get("verify")})
        rows.sort(key=lambda c: (-c["weakness"], -(c["score"] or 60), c["date"]), reverse=False)
        return rows

    nat = candidates(lambda m: m not in home and countries.get(m, "United States") == "United States")
    nationwide = None
    if nat:
        c = nat[0]
        score = f" Watchlist score {c['score']:.0f}, play {c['play']}." if c.get("score") else " Standing-watch search (licensed trade)."
        nationwide = dict(c, why=(f"The most open map pack outside Chicago for a search with real demand: the top 3 have a "
                                  f"median of {c['median']:g} reviews ({c['date']}).{score} Partner & manage unless 6 Central "
                                  f"opens a real staffed base there."),
                          also=[f"{x['query']} in {x['market']} (median {x['median']:g})" for x in nat[1:3]])

    intl = candidates(lambda m: countries.get(m, "United States") != "United States")
    dem = {(d.get("country"), scoring.slug(d["keyword"])): d for d in demand}
    for c in intl:
        c["demand"] = dem.get((c["country"], scoring.slug(c["query"])))
    intl.sort(key=lambda c: (-c["weakness"], -((c.get("demand") or {}).get("volume") or 0), c["date"]))
    international = None
    if intl:
        c = intl[0]
        d = c.get("demand") or {}
        dtext = (f" {d['volume']:,} searches/mo in {c['country']} at ${d['cpc']:.2f} CPC (OpenRush)" if d.get("volume") else
                 f" Demand in {c['country']} not measured yet")
        international = dict(c, play="Partner & manage",
                             why=(f"The most open map pack abroad: the top 3 have a median of {c['median']:g} reviews ({c['date']})."
                                  f"{dtext}. Play abroad: Partner & manage only. The profile belongs to the local operator who does "
                                  f"the work; 6 Central sells the back office (answering, dispatch, reviews, marketing) for a percentage."),
                             also=[f"{x['query']} in {x['market']} (median {x['median']:g})" for x in intl[1:3]])
    return {"seasonal": seasonal, "nationwide": nationwide, "international": international}


# ------------------------------------------------------------------- build

def build(day, cfg):
    plan = require_plan(day)
    out = run_path(day)
    cluster = cfg["clusters"][plan["cluster"]]
    prev = read_json(out / "prev_state.json", {}) or {}
    watch = prev.get("watchlist", {})
    raw_signals = read_json(out / "signals.json", {}) or {}
    signals = {k: [s for s in v if isinstance(s, dict) and s.get("source")]
               for k, v in raw_signals.items() if isinstance(v, list)}
    register, flags, gw_status, additions = google_watch(cfg, prev, signals | {"google_checked": raw_signals.get("google_checked")}, day)
    signals = {k: v for k, v in signals.items() if k not in ("google", "policy")}  # those two feed the Google watch
    countries = {m["name"]: market_country(m) for m in all_markets(cfg)}

    serps = {}
    for path in sorted((out / "serp").glob("*.json")):
        if path.name.startswith("base__"):
            continue  # target bases are read separately below
        data = payload(read_json(path))
        market_slug, _, q = path.stem.partition("__")
        market = next((m["name"] for m in all_markets(cfg) if scoring.slug(m["name"]) == market_slug), market_slug)
        result = scoring.pack_weakness(data, cfg["own_brand_markers"],
                                       [x["name"] for x in cfg.get("own_listings", [])])
        result.update(query=data.get("query") or q.replace("-", " "), market=market,
                      country=countries.get(market, "United States"), fetched_at=data.get("fetched_at"))
        serps.setdefault(scoring.slug(result["query"]), []).append(result)

    opportunities = []
    if not plan["recap"]:
        rows = {r["keyword"]: r for r in read_json(out / "screen.json", [])}
        for kw in plan.get("deep_dives", []):
            raw = payload(read_json(out / "keywords" / f"{scoring.slug(kw)}.json", {}) or {})
            row = rows.get(kw) or (openrush_row(kw, raw, cluster) if raw else None)  # Semrush-less fallback
            if not row:
                continue
            niche = cluster["niches"][row["niche"]]
            deep = scoring.yoy(raw.get("trend")) if raw else None
            if deep is not None:
                deep.update(volume=raw.get("monthly_volume"), cpc=raw.get("cpc_usd"))
            checks = serps.get(scoring.slug(scoring.local_query(kw)), [])
            weak_values = [c["weakness"] for c in checks if c.get("weakness") is not None]
            serp_summary = {"weakness": max(weak_values)} if weak_values else None
            risk = scoring.google_risk(row["niche"], {"keywords": [kw]}, register, flags)  # per keyword, not per niche
            season = scoring.season_ahead(raw.get("trend"), day) if raw else None
            score, parts, change, trend_source = scoring.opportunity(row, niche, deep, serp_summary, risk, season)
            weakness = serp_summary and serp_summary["weakness"]
            play, why = scoring.play_for(score, niche, weakness, change, risk, season)
            verify = niche.get("verify", "partner")
            opportunities.append({
                "verify": verify, "verify_grade": scoring.VERIFY_GRADE[verify], "risk": risk, "season": season,
                "big_fish": scoring.big_fish((deep or {}).get("volume") or row["volume"], weakness, verify),
                "keyword": kw, "niche": row["niche"], "portfolio": niche["portfolio"],
                "licensed": niche.get("licensed", False), "discovered": row.get("discovered", False),
                "score": score, "parts": parts, "change": change, "trend_source": trend_source,
                "label": scoring.label(change), "play": play, "why": why,
                "semrush": ({"volume": None, "cpc": None, "kd": None, "momentum": None} if row.get("source") == "openrush"
                            else {"volume": row["volume"], "cpc": row["cpc"], "kd": row["kd"], "momentum": row["momentum"]}),
                "openrush": deep, "map_packs": checks, "new": kw not in watch})
        opportunities.sort(key=lambda o: (scoring.PLAY_ORDER[o["play"]], -o["score"]))

    # Merge today into the watchlist.
    for o in opportunities:
        entry = watch.get(o["keyword"], {"first_seen": day, "history": []})
        entry.update(niche=o["niche"], cluster=plan["label"], last_seen=day, label=o["label"],
                     score=o["score"], change=o["change"], play=o["play"], verify=o["verify_grade"],
                     risk=(o["risk"] or {}).get("level"), season=o["season"], big_fish=o["big_fish"])
        history = [h for h in entry["history"] if h[0] != day]  # a re-run replaces today's point
        entry["history"] = (history + [[day, o["score"], o["change"]]])[-MAX_HISTORY:]
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
            readings.append({"date": day, "query": c["query"], "median": c["median_reviews"], "weakness": c["weakness"],
                             "country": c.get("country", "United States")})
            board[c["market"]] = readings[-60:]

    top = [{"keyword": o["keyword"], "score": o["score"], "label": o["label"], "play": o["play"]}
           for o in opportunities[:3]]
    briefs = [b for b in prev.get("briefs", []) if b.get("date") != day]
    briefs = ([{"date": day, "label": plan["label"], "top": top}] + briefs)[:MAX_HISTORY]
    # Our confirmed listings: today's map-pack position and reviews, with history.
    cities = [m["name"].split(",")[0] for m in all_markets(cfg)]
    own_listings, own_state = [], prev.get("own_listings", {})
    for listing in cfg.get("own_listings", []):
        check = next((c for c in serps.get(scoring.slug(listing["track_query"]), [])
                      if c["market"] == listing["market"]), None)
        others = [c for c in cities if c.lower() != listing["market"].split(",")[0].lower()]
        health = scoring.listing_health(listing, check, others)
        history = [h for h in own_state.get(listing["name"], []) if h["date"] != day]
        if check is not None:
            history = (history + [{"date": day, "position": health["position"], "reviews": health["reviews"],
                                   "rating": health["rating"]}])[-MAX_HISTORY:]
        health["previous"] = next((h for h in reversed(history) if h["date"] != day), None)
        own_state[listing["name"]] = history
        own_listings.append(health)
    states = {m["name"]: m.get("state") for m in all_markets(cfg)}
    query_states = (cfg.get("focus") or {}).get("query_states") or {}

    def sensible(r, market):  # no credit for an open "snow removal" pack in Phoenix
        allowed = query_states.get(r["query"])
        return allowed is None or states.get(market) in allowed

    us_board = {m: [r for r in rs if sensible(r, m)] for m, rs in board.items()
                if countries.get(m, "United States") == "United States"}
    intl_board = {m: r for m, r in board.items() if countries.get(m, "United States") != "United States"}
    focus = cfg.get("focus") or {}
    fq = {scoring.slug(q) for q in focus.get("map_queries", [])}
    focus_board = {m: [r for r in rows if scoring.slug(r["query"]) in fq] for m, rows in us_board.items()}
    focus_view = None
    if focus:
        today_checks = [c for k in fq for c in serps.get(k, [])]
        states = {m["name"].split(",")[-1].strip() for m in plan["markets"]} | {
            r["market"].split(",")[-1].strip() for r in scoring.leaderboard(focus_board)[:5]}
        focus_view = {"label": focus["label"], "today": today_checks,
                      "leaderboard": scoring.leaderboard({m: r for m, r in focus_board.items() if r}),
                      "licensing": {s: focus["licensing"][s] for s in sorted(states) if s in focus.get("licensing", {})}}
    bases_view, base_state = target_bases(cfg, day, out, prev)
    demand = international_demand(out, day)
    intl_view = {"today": [c for checks in serps.values() for c in checks if c.get("country", "United States") != "United States"],
                 "leaderboard": scoring.leaderboard(intl_board), "demand": demand,
                 "markets": sorted({m["name"] for m in plan["markets"] if m.get("role") == "international"}
                                   | {c["market"] for checks in serps.values() for c in checks
                                      if c.get("country", "United States") != "United States"})}
    picks = best_picks(cfg, day, opportunities, watch, board, demand)
    base_today = sum(1 for v in bases_view if v.get("today"))
    kits_today = [k for k in read_json(out / "kits.json", []) or [] if "amazon.com" in (k.get("url") or "") and k.get("title")]
    market_checks_today = sum(len(c) for c in serps.values())
    freshness = [
        {"section": "Best opportunities (3 picks)", "ok": True, "detail": "recomputed today"},
        {"section": "Keyword research", "ok": bool(opportunities) or plan["recap"],
         "detail": (f"{len(opportunities)} keywords scored" if opportunities else "recap day" if plan["recap"]
                    else "no keywords scored: Semrush out and no OpenRush deep dives saved")},
        {"section": "Map packs", "ok": market_checks_today > 0, "detail": f"{market_checks_today} checks today"},
        {"section": "Target bases", "ok": base_today == len(bases_view) and base_today > 0,
         "detail": f"{base_today} of {len(bases_view)} checked today"},
        {"section": "Our listings", "ok": all(o.get("checked") for o in own_listings) and bool(own_listings),
         "detail": ", ".join(f"{o['name'][:24]}: {'checked' if o.get('checked') else 'NOT checked'}" for o in own_listings) or "none configured"},
        {"section": "International", "ok": bool(intl_view["today"]), "detail": f"{len(intl_view['today'])} checks today"},
        {"section": "Google watch", "ok": bool(gw_status.get("checked")),
         "detail": (f"checked today, {gw_status.get('new', 0)} new" if gw_status.get("checked") else f"NOT checked (last {gw_status.get('last_checked') or 'never'})")},
        {"section": "Google register", "ok": True,
         "detail": f"as of {gw_status.get('register_as_of')}; {len(gw_status.get('promoted_today') or [])} promoted today, {len(gw_status.get('register_pending') or [])} awaiting repo sync"},
        {"section": "Timing signals", "ok": any(signals.get(k) for k in ("weather", "news", "season")),
         "detail": ", ".join(f"{k} {len(v)}" for k, v in signals.items() if v) or "none saved"},
        {"section": "Verification kits", "ok": bool(kits_today), "detail": f"{len(kits_today)} listings" if kits_today else "none saved"},
    ]
    notes = []
    stale = [f["section"] for f in freshness if not f["ok"]]
    if stale:
        notes.append("Not updated today: " + ", ".join(stale) + ". Every section must refresh every day (Terell, 2026-10-23).")
    if plan.get("screen_source") == "openrush-fallback":
        notes.append("No Semrush screen today (semrush.csv missing: Semrush reported no API units). Today's moves come from "
                     "OpenRush deep dives of the cluster's best-known keywords, and the Semrush columns are blank. "
                     "Top up API units at https://www.semrush.com/mcp-access to restore discovery of new keywords.")
    state = {"version": 1, "updated": day, "watchlist": watch, "briefs": briefs, "markets": board,
             "own_listings": own_state, "google_flags": flags, "google_watch": gw_status, "register_additions": additions,
             "bases": base_state}

    own_sightings = [dict(p, query=c["query"], market=c["market"])
                     for checks in serps.values() for c in checks for p in c["pack"] if p["possibly_ours"]]
    kits = [k for k in read_json(out / "kits.json", []) or []
            if "amazon.com" in (k.get("url") or "") and k.get("title")]
    tactic = cfg["playbook"][datetime.strptime(day, "%Y-%m-%d").toordinal() % len(cfg["playbook"])]
    brief = {"date": day, "weekday": plan["weekday"], "label": plan["label"], "recap": plan["recap"],
             "markets": [m["name"] for m in plan["markets"]], "leaderboard": scoring.leaderboard(us_board),
             "international": intl_view, "picks": picks, "notes": notes, "freshness": freshness,
             "opportunities": opportunities,
             "serps": serps, "signals": signals, "kits": kits, "verification": cfg["verification"], "own_sightings": own_sightings,
             "own_listings": own_listings, "focus": focus_view, "tactic": tactic, "bases": bases_view,
             "google": {"register": [e for e in register if e.get("level") in ("high", "medium")],
                        "flags": flags, "status": gw_status, "as_of": gw_status.get("register_as_of")},
             "season_ahead": sorted([o for o in opportunities if (o["season"] or {}).get("ratio", 0) >= 1.3],
                                    key=lambda o: -o["season"]["ratio"]),
             "spend": spend_for(out, cfg), "state": state}
    return brief


def target_bases(cfg, day, out, prev):
    """Today's reading for every planned base: our position, the top 3, the median, and the change since last time."""
    own_names = [x["name"] for x in cfg.get("own_listings", [])]
    markers = cfg.get("own_brand_markers", [])
    base_state = prev.get("bases") or {}
    view = []
    for b, q, rel in base_checks(cfg, day):
        path = out / rel
        key = f"{b['name']} | {q}"
        history = [h for h in base_state.get(key, []) if h.get("date") != day]
        reading = None
        if path.exists():
            data = payload(read_json(path))
            pw = scoring.pack_weakness(data, markers, own_names)
            ours = next((i for i, p in enumerate(pw["pack"], 1) if p.get("ours")), None)
            reading = {"date": day, "median": pw.get("median_reviews"), "weakness": pw.get("weakness"),
                       "our_position": ours,
                       "top3": [{"name": p["name"], "reviews": p["reviews"]} for p in pw["pack"][:3]]}
            history = (history + [reading])[-MAX_HISTORY:]
        base_state[key] = history
        previous = next((h for h in reversed(history) if h.get("date") != day), None)
        view.append({"base": b["name"], "location": b["serp_location"], "query": q, "plan": b.get("plan", ""),
                     "today": reading, "previous": previous})
    return view, base_state


def flag_key(item):
    """One key per story: the source URL when there is one, else the summary. Lets a re-report count as a re-confirmation."""
    src = (item.get("source") or "").strip().lower().rstrip("/")
    return "src:" + src if src else "sum:" + scoring.slug(item.get("summary", ""))[:60]


def google_watch(cfg, prev, signals, day):
    """The dated Google risk register plus the rolling daily watch, and whether the watch was checked today.

    Daily items come from signals.json under "google" (the watch) and "policy" (the Google timing signal), each
    {"summary", "source", "niches": [...], "keywords": [...], "level": high|medium|low, "plan"?}. A missing level
    counts as low and missing niches as "all niches" rather than dropping the item. Items carry over between runs,
    a re-report refreshes last_seen, and items expire after `flag_days` without being seen again.

    The register updates itself every day: a medium or high item that is re-confirmed, or a week old, is promoted
    into the register (kept in the page state), so nothing waits on a repo commit. `scout.py register-sync`
    copies the promoted items into research/google/risk_register.json when someone with repo access runs it.
    """
    path = cfg.get("google_risk_register")
    reg = (read_json(ROOT / path, {}) or {}) if path else {}
    repo_entries = reg.get("entries", [])
    keep_days = (cfg.get("google_watch") or {}).get("flag_days", 60)
    today = datetime.strptime(day, "%Y-%m-%d")
    flags = {}
    for key, f in (prev.get("google_flags") or {}).items():
        if (today - datetime.strptime(f["last_seen"], "%Y-%m-%d")).days <= keep_days:
            flags[flag_key(f) if (f.get("source") or f.get("summary")) else key] = f
    todays, seen = [], set()
    for item in (signals.get("google") or []) + (signals.get("policy") or []):
        if not isinstance(item, dict) or not item.get("source") or not item.get("summary"):
            continue
        key = flag_key(item)
        if key in seen:
            continue  # the same story written under both keys
        seen.add(key)
        todays.append((key, item))
    new = reconfirmed = 0
    for key, item in todays:
        level = item.get("level") if item.get("level") in scoring.RISK_RANK else "low"
        niches = item.get("niches") or item.get("keywords") or ["all niches"]
        prior = flags.get(key)
        first = prior["first_seen"] if prior else day
        reconfirmed += bool(prior)
        new += not prior
        flags[key] = dict(item, level=level, niches=niches, first_seen=first, last_seen=day)
    checked = signals.get("google_checked") if isinstance(signals.get("google_checked"), dict) else {}
    ran = bool(todays) or bool(checked) or isinstance(signals.get("google"), list)

    def norm(url):
        return (url or "").strip().lower().rstrip("/")
    repo_sources = {norm(src["url"]) for e in repo_entries for src in e.get("sources", []) if src.get("url")}
    additions = dict(prev.get("register_additions") or {})
    promoted_today = []
    for key, f in flags.items():
        age = (today - datetime.strptime(f["first_seen"], "%Y-%m-%d")).days
        settled = f.get("last_seen") != f.get("first_seen") or age >= 7
        if f.get("level") in ("high", "medium") and settled and key not in additions and norm(f.get("source")) not in repo_sources:
            additions[key] = {"id": "watch-" + scoring.slug(f.get("summary", ""))[:48], "niches": f.get("niches") or ["all niches"],
                              "keywords": f.get("keywords") or [], "level": f["level"], "what": f.get("summary", ""),
                              "since": f["first_seen"][:7], "plan": f.get("plan") or "Prepare before launching; see the source.",
                              "sources": [{"url": f.get("source"), "date": f["first_seen"]}],
                              "scope": "general" if (f.get("niches") or ["all niches"]) == ["all niches"] else "niche",
                              "promoted": day}
            promoted_today.append(additions[key]["what"][:100])
    register = repo_entries + [a for a in additions.values() if norm(a["sources"][0]["url"]) not in repo_sources]
    unsynced = [a for a in additions.values() if norm(a["sources"][0]["url"]) not in repo_sources]
    as_of = max([reg.get("as_of") or ""] + [a.get("promoted", "") for a in additions.values()]) or None
    last = (prev.get("google_watch") or {}).get("last_checked")
    status = {"checked": ran, "last_checked": day if ran else last, "searches": list(checked.get("searches") or []),
              "new": new, "reconfirmed": reconfirmed, "active": len(flags),
              "last_new": max((f["first_seen"] for f in flags.values()), default=None),
              "register_as_of": as_of, "register_repo_as_of": reg.get("as_of"), "register_entries": len(register),
              "promoted_today": promoted_today,
              "register_pending": [a["what"][:100] for a in unsynced]}
    return register, flags, status, additions


def spend_for(out, cfg):
    """Tool-reported spend, falling back to counting saved results x the per-call costs in config."""
    spend = dict(read_json(out / "spend.json", {}) or {})
    costs = cfg["openrush_credits"]
    if spend.get("openrush_credits") is None:
        counted = sum(len(list((out / sub).glob("*.json"))) * costs[tool] for sub, tool in
                      (("discovery", "research_keywords"), ("keywords", "inspect_keyword"), ("serp", "inspect_serp"))
                      if (out / sub).is_dir())
        spend["openrush_credits"] = f"~{counted} (counted)" if counted else None
    if spend.get("semrush_units") is None and (out / "semrush.csv").exists():
        rows = max(0, len((out / "semrush.csv").read_text().strip().splitlines()) - 1)
        spend["semrush_units"] = f"~{rows * cfg['semrush_units_per_keyword']} (counted)"
    return {k: v for k, v in spend.items() if v is not None}


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


def cmd_register_sync(args):
    """Copy the register entries the daily watch promoted (kept in the page state) into the repo file."""
    cfg = load_config()
    out = run_path(args.date)
    state = read_json(out / "state.json", None) or read_json(out / "prev_state.json", {}) or {}
    additions = state.get("register_additions") or {}
    path = ROOT / cfg["google_risk_register"]
    reg = read_json(path, {"entries": []})
    have = {(src.get("url") or "").strip().lower().rstrip("/") for e in reg["entries"] for src in e.get("sources", [])}
    added = []
    for a in additions.values():
        url = (a["sources"][0].get("url") or "").strip().lower().rstrip("/")
        if url and url not in have:
            entry = {k: v for k, v in a.items() if k != "promoted"}
            entry["id"] = entry["id"] if entry["id"] not in {e["id"] for e in reg["entries"]} else entry["id"] + "-" + a["promoted"]
            reg["entries"].append(entry)
            have.add(url)
            added.append(entry["id"])
    if added:
        reg["as_of"] = args.date
        reg.setdefault("changelog", []).append({"date": args.date, "change": "register-sync added " + ", ".join(added) + " (promoted by the daily watch)."})
        path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")
    print(f"Synced {len(added)} promoted item(s) into {path.relative_to(ROOT)}: {', '.join(added) or 'nothing new'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("register-sync")
    p.add_argument("--date", required=True)
    p.set_defaults(func=cmd_register_sync)
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
