"""Organization allow and block lists for outreach email (AgentMail).

The lists 6 Central keeps:

| Type, direction | What goes on it |
|---|---|
| block, send    | Everyone who asked not to be contacted, plus hard bounces |
| block, reply   | The same people, so no agent ever writes back to them |
| allow, receive | Our own domains and addresses, so internal mail is never filtered |
| block, receive | Spam senders, added as they show up |
| allow, send    | Optional: only approved partners (off unless the config turns it on) |

Opt-outs are honored right away. Everything else comes from
config/email_lists.json and is only sent to AgentMail with `--apply`.
Nothing here ever deletes an entry or sends an email.
"""
import json
import re
from datetime import date
from pathlib import Path

from .normalize import FREE_MAIL_DOMAINS

EMAIL_RE = re.compile(r"^[a-z0-9._%+'-]+@([a-z0-9-]+\.)+[a-z]{2,}$")
DOMAIN_RE = re.compile(r"^([a-z0-9-]+\.)+[a-z]{2,}$")
OPT_OUT_LISTS = [("send", "block"), ("reply", "block")]


def clean_entry(entry):
    """Lower-case an address or domain and check it is safe to put on a list.

    Returns (entry, problem). A bare free-mail domain is refused because it
    would match every Gmail, Yahoo or Outlook user, including our partners.
    """
    entry = (entry or "").strip().lower().removeprefix("mailto:").rstrip(".")
    if EMAIL_RE.match(entry):
        return entry, ""
    if DOMAIN_RE.match(entry):
        if entry in FREE_MAIL_DOMAINS:
            return entry, f"{entry} is a free-mail domain: it would match every address there. Use full addresses."
        return entry, ""
    return entry, f"{entry!r} is not an email address or domain"


def load_config(path):
    path = Path(path)
    if not path.exists():
        return None
    config = json.loads(path.read_text())
    for key in ("own_domains", "own_addresses", "blocked_senders"):
        config.setdefault(key, [])
    config.setdefault("restrict_send_to_approved_partners", False)
    return config


def read_suppression(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def add_suppression(path, entry, reason, source=""):
    """Record an opt-out locally. Returns the record, or None if it was already there."""
    entry, problem = clean_entry(entry)
    if problem:
        raise ValueError(problem)
    if entry in {r["entry"] for r in read_suppression(path)}:
        return None
    record = {"entry": entry, "reason": reason, "source": source, "date": date.today().isoformat()}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def opt_out_reason(record):
    text = f"Opt-out {record['date']}: {record['reason']}"
    return text + (f" ({record['source']})" if record.get("source") else "")


def desired_entries(config, suppression, partners=()):
    """Every entry the lists should hold, plus the problems that kept others off.

    `partners` is a list of (email, business name) for approved partners; they
    only become entries when the config restricts sending to them.
    """
    wanted, problems = {}, []

    def add(direction, list_type, entry, reason):
        entry, problem = clean_entry(entry)
        if problem:
            problems.append(f"{direction}/{list_type}: {problem}")
        else:
            wanted.setdefault((direction, list_type, entry), reason)

    config = config or {}
    for domain in config.get("own_domains", []):
        add("receive", "allow", domain, "6 Central Enterprises domain")
    for address in config.get("own_addresses", []):
        add("receive", "allow", address, "6 Central Enterprises address")
    for item in config.get("blocked_senders", []):
        entry, reason = (item, "Spam sender") if isinstance(item, str) else (item["entry"], item.get("reason") or "Spam sender")
        add("receive", "block", entry, reason)
    for record in suppression:
        for direction, list_type in OPT_OUT_LISTS:
            add(direction, list_type, record["entry"], opt_out_reason(record))
    if config.get("restrict_send_to_approved_partners"):
        suppressed = {r["entry"] for r in suppression}
        for email, name in partners:
            if email and email.lower() not in suppressed:
                add("send", "allow", email, f"Approved partner: {name}")

    entries = [{"direction": d, "type": t, "entry": e, "reason": r} for (d, t, e), r in wanted.items()]
    return sorted(entries, key=lambda x: (x["direction"], x["type"], x["entry"])), problems


def make_client():
    """AgentMail client. The SDK reads AGENTMAIL_API_KEY itself; the key is never printed."""
    import os
    if not os.getenv("AGENTMAIL_API_KEY"):
        raise RuntimeError("AGENTMAIL_API_KEY is not set in this environment.")
    from agentmail import AgentMail
    return AgentMail()


def current_entries(client, direction, list_type):
    found, token = set(), None
    while True:
        page = client.lists.list(direction, list_type, limit=100, page_token=token)
        found.update(e.entry.lower() for e in page.entries)
        token = page.next_page_token
        if not token:
            return found


def sync(client, entries, apply=False):
    """Compare `entries` with AgentMail. With apply=True, create the missing ones.

    Returns a dict of entry lists: to_add, added, failed (with the error),
    already (present), extra (on AgentMail but not wanted; left alone).
    """
    report = {"to_add": [], "added": [], "failed": [], "already": [], "extra": []}
    groups = {}
    for e in entries:
        groups.setdefault((e["direction"], e["type"]), []).append(e)
    for direction, list_type in sorted(set(groups) | {(d, t) for d in ("send", "receive", "reply") for t in ("allow", "block")}):
        present = current_entries(client, direction, list_type)
        wanted = groups.get((direction, list_type), [])
        names = {e["entry"] for e in wanted}
        report["extra"] += [{"direction": direction, "type": list_type, "entry": x} for x in sorted(present - names)]
        for e in wanted:
            if e["entry"] in present:
                report["already"].append(e)
                continue
            report["to_add"].append(e)
            if apply:
                try:
                    client.lists.create(direction, list_type, entry=e["entry"], reason=e["reason"])
                    report["added"].append(e)
                except Exception as exc:  # report every failure, keep going
                    report["failed"].append({**e, "error": str(exc)[:200]})
    return report


def suppressed_entries(suppression_path, client=None):
    """Everyone we must not contact: the local opt-out file plus AgentMail's send block list."""
    entries = {r["entry"] for r in read_suppression(suppression_path)}
    if client is not None:
        entries |= current_entries(client, "send", "block")
    return entries


def is_suppressed(email, suppressed):
    email = (email or "").lower()
    return bool(email) and (email in suppressed or email.split("@")[-1] in suppressed)
