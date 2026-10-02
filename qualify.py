#!/usr/bin/env python3
"""Partner qualification pipeline for 6 Central Enterprises.

    python3 qualify.py prepare      <leads file> [--market "Chicago, IL"] [--limit N]
    python3 qualify.py status       --run <run id>
    python3 qualify.py score        --run <run id> [--out-dir DIR]
    python3 qualify.py audit-plan   --run <run id> [--top 20] [--include-verify] [--all]
    python3 qualify.py audit-report --run <run id> [--out-dir DIR]

`prepare` cleans the lead file and splits it into research batches. The
partner-researcher agent then writes one evidence file per lead into
runs/<run>/evidence/. `score` turns that evidence into the ranked report.
`audit-plan` picks the qualified partners for a full audit (Google
reputation, SEO, keywords, competition, custom email); the market-analyst
and partner-auditor agents write runs/<run>/market/ and runs/<run>/audits/;
`audit-report` builds the audit workbook and audit book.
Nothing here contacts anyone.
"""
import argparse
import json
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

from partner_qualifier.audit import audit_partner, load_markets, market_for, rank_partners
from partner_qualifier.audit_report import build_audit_book, build_audit_workbook
from partner_qualifier.normalize import domain_of, normalize, read_rows, website_kind
from partner_qualifier.report import build_workbook, write_partner_csv
from partner_qualifier.rubric import has_source, score

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"
CONFIG = ROOT / "config"

# OpenRush credits per call (from describe_capabilities), used for the audit estimate.
CREDITS = {"research_keywords": 3, "inspect_serp": 2, "inspect_domain": 9, "audit_site": 9,
           "inspect_backlinks": 9, "inspect_search_visibility": 10}
MARKET_SERPS = 4

# Sections the researcher fills in that must carry a source when they assert something.
SOURCED_SECTIONS = ["identity", "niche", "serves_target", "insured", "size", "established",
                    "activity", "license", "opener"]


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def run_dir(run_id):
    path = RUNS / run_id
    if not (path / "run.json").exists():
        sys.exit(f"No run named '{run_id}' in {RUNS}. Run `prepare` first.")
    return path


def cmd_prepare(args):
    source = Path(args.file)
    if not source.exists():
        sys.exit(f"File not found: {source}")
    rows = read_rows(source)
    leads = normalize(rows, args.market)
    if not leads:
        sys.exit("No leads found in the file — check that it has a header row.")

    slug = re.sub(r"[^a-z0-9]+", "-", source.stem.lower()).strip("-")[:40] or "leads"
    run_id = args.run or f"{date.today().isoformat()}_{slug}"
    out = RUNS / run_id
    (out / "evidence").mkdir(parents=True, exist_ok=True)
    (out / "batches").mkdir(exist_ok=True)

    queue = sorted((l for l in leads if l["screen"] == "research"),
                   key=lambda l: (-l["priority"], l["lead_id"]))
    if args.limit:
        for lead in queue[args.limit:]:
            lead["screen"] = "deferred"
        queue = queue[:args.limit]

    (out / "leads.jsonl").write_text("".join(json.dumps(l) + "\n" for l in leads))
    for old in (out / "batches").glob("batch_*.json"):
        old.unlink()
    fields = ["lead_id", "handle", "profile_url", "name", "bio", "category", "location_text",
              "email", "email_type", "website", "website_kind", "phone", "followers", "posts",
              "niche_guess", "niche_candidates", "location_hint"]
    batches = [queue[i:i + args.batch_size] for i in range(0, len(queue), args.batch_size)]
    for n, batch in enumerate(batches, start=1):
        payload = {"run_id": run_id, "market": args.market, "batch": n,
                   "leads": [{k: lead.get(k) for k in fields} for lead in batch]}
        (out / "batches" / f"batch_{n:02d}.json").write_text(json.dumps(payload, indent=2))

    run = {"run_id": run_id, "market": args.market, "source_file": source.name,
           "created_at": datetime.now().isoformat(timespec="minutes"), "lead_count": len(leads),
           "research_count": len(queue), "batch_count": len(batches), "batch_size": args.batch_size}
    (out / "run.json").write_text(json.dumps(run, indent=2))

    def tally(key):
        counts = {}
        for lead in leads:
            counts[lead[key] or "(none)"] = counts.get(lead[key] or "(none)", 0) + 1
        return ", ".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))

    print(f"Run: {run_id}")
    print(f"Rows read: {len(rows)} | leads: {len(leads)} | to research: {len(queue)} "
          f"| duplicates: {sum(l['screen'] == 'skip_duplicate' for l in leads)} "
          f"| deferred: {sum(l['screen'] == 'deferred' for l in leads)}")
    print(f"Niche guesses: {tally('niche_guess')}")
    print(f"Location hints for {args.market}: {tally('location_hint')}")
    print(f"Email types: {tally('email_type')}")
    print(f"Batches: {len(batches)} x up to {args.batch_size} leads -> {out / 'batches'}")


def cmd_status(args):
    out = run_dir(args.run)
    done = {p.stem for p in (out / "evidence").glob("*.json")}
    pending = []
    for path in sorted((out / "batches").glob("batch_*.json")):
        ids = [l["lead_id"] for l in json.loads(path.read_text())["leads"]]
        missing = [i for i in ids if i not in done]
        if missing:
            pending.append(f"{path.name}: {len(missing)} left ({', '.join(missing)})")
    run = json.loads((out / "run.json").read_text())
    print(f"Run {args.run}: {len(done)}/{run['research_count']} researched")
    print("\n".join(pending) if pending else "All batches complete — run `score`.")


def validate(ev, lead_id):
    problems = []
    if ev.get("lead_id") != lead_id:
        problems.append(f"lead_id is {ev.get('lead_id')!r}")
    for key in SOURCED_SECTIONS:
        item = ev.get(key)
        asserts = isinstance(item, dict) and any(
            item.get(k) not in (None, "", [], "not_found") for k in ("value", "status", "number", "text", "year_started"))
        if asserts and not has_source(item):
            problems.append(f"{key} has no source (scored as not confirmed)")
    for key in ("reviews", "red_flags"):
        unsourced = [i for i in ev.get(key) or [] if not has_source(i)]
        if unsourced:
            problems.append(f"{len(unsourced)} {key} entr{'y' if len(unsourced) == 1 else 'ies'} without source")
    return problems


def cmd_score(args):
    out = run_dir(args.run)
    run = json.loads((out / "run.json").read_text())
    leads = load_jsonl(out / "leads.jsonl")
    results, warnings = [], []
    for lead in leads:
        path = out / "evidence" / f"{lead['lead_id']}.json"
        ev = None
        if path.exists():
            try:
                ev = json.loads(path.read_text())
            except json.JSONDecodeError as exc:
                warnings.append(f"{lead['lead_id']}: unreadable evidence ({exc})")
            else:
                warnings += [f"{lead['lead_id']}: {p}" for p in validate(ev, lead["lead_id"])]
        results.append(score(lead, ev, run["market"]))

    (out / "results.json").write_text(json.dumps(results, indent=2))
    xlsx = out / "partner_qualification.xlsx"
    csv_path = out / "partner_sheet.csv"
    build_workbook(xlsx, leads, results, run)
    write_partner_csv(csv_path, leads, results, run)
    if args.out_dir:
        dest = Path(args.out_dir)
        dest.mkdir(parents=True, exist_ok=True)
        for f in (xlsx, csv_path):
            shutil.copy(f, dest / f"{args.run}_{f.name}")

    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print(f"Scored {len(results)} leads: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    top = sorted((r for r in results if r["verdict"] == "MESSAGE"),
                 key=lambda r: (-r["score"], -r["review_total"]))[:10]
    for r in top:
        print(f"  {r['score']}/10  {r['business_name']}  — {r['contact']['best']}")
    if warnings:
        print(f"\n{len(warnings)} evidence warning(s):")
        print("\n".join(f"  {w}" for w in warnings[:50]))
    print(f"\nReport: {xlsx}\nPartner sheet CSV: {csv_path}")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "general"


def load_sender():
    for name in ("sender.json", "sender.example.json"):
        path = CONFIG / name
        if path.exists():
            return json.loads(path.read_text())
    return {"name": "Terell John", "title": "Founder", "company": "6 Central Enterprises",
            "phone": "[YOUR PHONE]", "mailing_address": "[YOUR MAILING ADDRESS]"}


def cmd_audit_plan(args):
    out = run_dir(args.run)
    if not (out / "results.json").exists():
        sys.exit("Run `score` first: audits are only for qualified partners.")
    run = json.loads((out / "run.json").read_text())
    leads = {l["lead_id"]: l for l in load_jsonl(out / "leads.jsonl")}
    results = json.loads((out / "results.json").read_text())
    picks = sorted((r for r in results if r["verdict"] == "MESSAGE"),
                   key=lambda r: (-r["score"], -r["review_total"]))
    if args.include_verify:
        picks += sorted((r for r in results if r["verdict"] == "VERIFY" and r["max_possible"] >= 8),
                        key=lambda r: (-r["max_possible"], -r["score"]))
    if getattr(args, "all", False):
        # Every real business: skip only duplicates, non-businesses and unlicensed license-required niches.
        not_real = ("Duplicate", "Could not confirm a real", "Not a local service provider")
        rest = [r for r in results if r["verdict"] in ("VERIFY", "HOLD", "SKIP")
                and not (r["verdict"] == "SKIP" and r["reason"].startswith(not_real))]
        order = {"VERIFY": 0, "HOLD": 1, "SKIP": 2}
        picks += sorted(rest, key=lambda r: (order[r["verdict"]], -r["score"], -r["review_total"]))
    picks = picks[:args.top]
    if not picks:
        sys.exit("No MESSAGE partners to audit yet (try --include-verify).")

    batch_dir = out / "audit_batches"
    batch_dir.mkdir(exist_ok=True)
    for old in batch_dir.glob("batch_*.json"):
        old.unlink()
    (out / "audits").mkdir(exist_ok=True)
    (out / "market").mkdir(exist_ok=True)
    (out / "seo_cache").mkdir(exist_ok=True)

    entries, niches, with_site = [], {}, 0
    for r in picks:
        lead = leads[r["lead_id"]]
        evidence = json.loads((out / "evidence" / f"{r['lead_id']}.json").read_text())
        site = (evidence.get("online_presence") or {}).get("website_url") or lead.get("website") or ""
        domain = domain_of(site) if site and website_kind(site) == "own_site" else ""
        niche = r["niche"] or "general"
        niches.setdefault(niche, []).append(r["lead_id"])
        with_site += bool(domain)
        entries.append({"lead_id": r["lead_id"], "business_name": r["business_name"], "niche": niche,
                        "domain_to_audit": domain, "market_file": f"runs/{args.run}/market/{slugify(niche)}.json",
                        "qualification": {k: r[k] for k in ("verdict", "score", "why", "contact", "website")},
                        "terell_decides": r["verdict"] in ("HOLD", "SKIP"),
                        "lead": lead, "evidence": evidence})
    batches = [entries[i:i + args.batch_size] for i in range(0, len(entries), args.batch_size)]
    for n, batch in enumerate(batches, start=1):
        (batch_dir / f"batch_{n:02d}.json").write_text(json.dumps(
            {"run_id": args.run, "market": run["market"], "partners": batch}, indent=2))

    missing_markets = [n for n in niches if not (out / "market" / f"{slugify(n)}.json").exists()]
    market_credits = len(missing_markets) * (CREDITS["research_keywords"] + MARKET_SERPS * CREDITS["inspect_serp"])
    low = with_site * (CREDITS["inspect_domain"] + CREDITS["audit_site"])
    high = with_site * sum(CREDITS[k] for k in ("inspect_domain", "audit_site", "inspect_backlinks",
                                                 "inspect_search_visibility"))
    plan = {"partners": [e["lead_id"] for e in entries], "niches": niches, "missing_markets": missing_markets,
            "batches": len(batches), "estimated_credits": [market_credits + low, market_credits + high]}
    (out / "audit_plan.json").write_text(json.dumps(plan, indent=2))

    print(f"Audit plan for {args.run}: {len(entries)} partners in {len(batches)} batch(es)")
    for e in entries:
        print(f"  {e['lead_id']}  {e['business_name']}  [{e['niche']}]  site: {e['domain_to_audit'] or 'none'}")
    print("Market research needed for: " + (", ".join(missing_markets) or "none (already done)"))
    print(f"Estimated OpenRush credits: {market_credits + low}-{market_credits + high} "
          f"({with_site} partner site(s) to audit; partners without a site cost 0)")


def cmd_audit_report(args):
    out = run_dir(args.run)
    run = json.loads((out / "run.json").read_text())
    plan_path = out / "audit_plan.json"
    if not plan_path.exists():
        sys.exit("Run `audit-plan` first.")
    plan = json.loads(plan_path.read_text())
    leads = {l["lead_id"]: l for l in load_jsonl(out / "leads.jsonl")}
    results = {r["lead_id"]: r for r in json.loads((out / "results.json").read_text())}
    markets = load_markets(out / "market")
    sender = load_sender()
    rows, missing = [], []
    for lead_id in plan["partners"]:
        path = out / "audits" / f"{lead_id}.json"
        if not path.exists():
            missing.append(lead_id)
            continue
        audit = json.loads(path.read_text())
        evidence = json.loads((out / "evidence" / f"{lead_id}.json").read_text())
        niche = audit.get("niche") or results[lead_id]["niche"]
        market = market_for(niche, markets)  # None when this niche has no market file yet
        rows.append(audit_partner(leads[lead_id], evidence, results[lead_id], audit, market, sender))
    if not rows:
        sys.exit("No audit files yet in runs/<run>/audits/.")
    rows = rank_partners(rows)
    xlsx, book = out / "partner_audits.xlsx", out / "partner_audit_book.md"
    build_audit_workbook(xlsx, rows, markets)
    build_audit_book(book, rows, markets, run)
    if args.out_dir:
        dest = Path(args.out_dir)
        dest.mkdir(parents=True, exist_ok=True)
        for f in (xlsx, book):
            shutil.copy(f, dest / f"{args.run}_{f.name}")

    print(f"Audited {len(rows)} partner(s)" + (f"; still missing: {', '.join(missing)}" if missing else ""))
    for rank, r in enumerate(rows, start=1):
        e = r["email"]
        print(f"  {rank}. {r['business_name']}: {r['quadrant']} | quality {r['quality']}/10, need {r['need']}/10 "
              f"| email: {e['status']}" + (f" ({'; '.join(e['failed'] + e['warnings'])})" if e["failed"] or e["warnings"] else ""))
    if "[YOUR" in sender["phone"] + sender["mailing_address"]:
        print("\nNote: add your phone and mailing address in config/sender.json (copy config/sender.example.json).")
    print(f"\nWorkbook: {xlsx}\nAudit book: {book}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare", help="clean a lead file and split it into research batches")
    p.add_argument("file")
    p.add_argument("--market", default="Chicago, IL")
    p.add_argument("--run", help="run id (default: date + file name)")
    p.add_argument("--batch-size", type=int, default=5)
    p.add_argument("--limit", type=int, help="research only the top N leads by priority")
    p.set_defaults(func=cmd_prepare)
    s = sub.add_parser("status", help="show research progress")
    s.add_argument("--run", required=True)
    s.set_defaults(func=cmd_status)
    c = sub.add_parser("score", help="score evidence and build the report")
    c.add_argument("--run", required=True)
    c.add_argument("--out-dir", help="also copy the report here")
    c.set_defaults(func=cmd_score)
    a = sub.add_parser("audit-plan", help="pick qualified partners for a full audit")
    a.add_argument("--run", required=True)
    a.add_argument("--top", type=int, default=20)
    a.add_argument("--include-verify", action="store_true", help="also audit VERIFY leads that could reach 8+")
    a.add_argument("--all", action="store_true",
                   help="audit every real business; HOLD and low scorers are marked for Terell to decide")
    a.add_argument("--batch-size", type=int, default=3)
    a.set_defaults(func=cmd_audit_plan)
    r = sub.add_parser("audit-report", help="build the audit workbook and audit book")
    r.add_argument("--run", required=True)
    r.add_argument("--out-dir", help="also copy the outputs here")
    r.set_defaults(func=cmd_audit_report)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
