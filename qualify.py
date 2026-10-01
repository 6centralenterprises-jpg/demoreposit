#!/usr/bin/env python3
"""Partner qualification pipeline for 6 Central Enterprises.

    python3 qualify.py prepare <leads file> [--market "Chicago, IL"] [--limit N]
    python3 qualify.py status  --run <run id>
    python3 qualify.py score   --run <run id> [--out-dir DIR]

`prepare` cleans the lead file and splits it into research batches. The
partner-researcher agent then writes one evidence file per lead into
runs/<run>/evidence/. `score` turns that evidence into the ranked report.
Nothing here contacts anyone.
"""
import argparse
import json
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

from partner_qualifier.normalize import normalize, read_rows
from partner_qualifier.report import build_workbook, write_partner_csv
from partner_qualifier.rubric import has_source, score

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"

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
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
