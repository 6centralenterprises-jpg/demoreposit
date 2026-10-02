"""Partner outreach through AgentMail: inboxes, drafts, approved sends and reply triage.

Everything is shown first and only happens with --apply. The one exception
is opt-outs: when someone asks to stop, they are blocked right away.
Drafts, labels and sent mail live in AgentMail, so nothing depends on this
container surviving.

Labels used on messages and drafts:
  6c-outreach            every first-contact draft and the message it becomes
  6c-awaiting-approval   draft written, not yet approved by Terell
  6c-lead-<run>-<id>     ties a draft to its lead so it is never drafted twice
  6c-sent                sent after approval (counts toward the daily cap)
  6c-triaged, 6c-<kind>  reply already sorted, and how
"""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import email_lists

OUTREACH = "6c-outreach"
AWAITING = "6c-awaiting-approval"
SENT = "6c-sent"
TRIAGED = "6c-triaged"


def lead_label(run_id, lead_id):
    return f"6c-lead-{re.sub(r'[^a-z0-9]+', '-', run_id.lower())}-{lead_id.lower()}"


def _pages(fetch, key):
    token = None
    while True:
        page = fetch(token)
        yield from getattr(page, key)
        token = page.next_page_token
        if not token:
            return


# --- Inboxes -----------------------------------------------------------------

def plan_inboxes(client, wanted):
    """Split the configured inboxes into (existing, missing) by address."""
    have = {i.email.lower() for i in _pages(lambda t: client.inboxes.list(limit=100, page_token=t), "inboxes")}
    existing, missing = [], []
    for spec in wanted:
        address = f"{spec['username']}@{spec['domain']}".lower()
        (existing if address in have else missing).append({**spec, "address": address})
    return existing, missing


def create_inbox(client, spec):
    from agentmail.inboxes.types import CreateInboxRequest
    return client.inboxes.create(request=CreateInboxRequest(
        username=spec["username"], domain=spec["domain"], display_name=spec["display_name"]))


# --- Drafts ------------------------------------------------------------------

def draft_candidates(rows, suppressed):
    """Audited partners whose email passed every check, with a usable address.

    Returns (ready, skipped); each skipped item says why, so nothing silently drops.
    """
    ready, skipped = [], []
    for r in rows:
        contact, email = r.get("contact") or {}, r.get("email") or {}
        to = (contact.get("email") or "").lower()
        why = ""
        if r.get("verdict") != "MESSAGE":
            why = f"verdict is {r.get('verdict')}, not MESSAGE"
        elif not email.get("status", "").startswith("Draft"):
            why = f"email {email.get('status', 'missing')}: {', '.join(email.get('failed') or []) or 'no body'}"
        elif not to:
            why = f"no email address (best contact: {contact.get('best', 'none')})"
        elif contact.get("email_free_mail") and not contact.get("email_listed_at"):
            why = "free-mail address not publicly listed as the business contact"
        elif email_lists.is_suppressed(to, suppressed):
            why = "on the opt-out list"
        elif "[YOUR" in email.get("full_text", ""):
            why = "signature still has placeholders: fill in config/sender.json"
        if why:
            skipped.append({"lead_id": r["lead_id"], "business_name": r["business_name"], "why": why})
        else:
            ready.append({"lead_id": r["lead_id"], "business_name": r["business_name"], "to": to,
                          "subject": email["subject"], "text": email["full_text"]})
    return ready, skipped


def existing_lead_labels(client, inbox):
    """Lead labels already used by a draft or a sent message, so no one is drafted twice."""
    labels = set()
    for item in _pages(lambda t: client.inboxes.drafts.list(inbox, limit=100, page_token=t, labels=[OUTREACH]), "drafts"):
        labels.update(l for l in item.labels if l.startswith("6c-lead-"))
    for item in _pages(lambda t: client.inboxes.messages.list(inbox, limit=100, page_token=t, labels=[OUTREACH]), "messages"):
        labels.update(l for l in item.labels if l.startswith("6c-lead-"))
    return labels


def create_draft(client, inbox, run_id, item):
    return client.inboxes.drafts.create(
        inbox, to=[item["to"]], subject=item["subject"], text=item["text"],
        labels=[OUTREACH, AWAITING, lead_label(run_id, item["lead_id"])])


# --- Sending -----------------------------------------------------------------

def daily_cap(config, today):
    start = config.get("warmup_start")
    if not start:
        return config["daily_cap_warmup"]
    days = (today - datetime.fromisoformat(start).date()).days
    return config["daily_cap_warmup"] if days < config["warmup_days"] else config["daily_cap"]


def in_window(now, window):
    return now.weekday() in window["days"] and window["start_hour"] <= now.hour < window["end_hour"]


def next_window_open(now, window):
    day = now
    for _ in range(8):
        opens = day.replace(hour=window["start_hour"], minute=0, second=0, microsecond=0)
        if day.weekday() in window["days"] and opens > now:
            return opens
        day = (day + timedelta(days=1)).replace(hour=0, minute=0)
    raise ValueError("send_window has no open days")


def sent_today(client, inbox, now):
    """Sent since midnight plus approved drafts still waiting to go out (counted conservatively)."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sent = sum(1 for _ in _pages(lambda t: client.inboxes.messages.list(
        inbox, limit=100, page_token=t, labels=[SENT], after=midnight), "messages"))
    scheduled = sum(1 for _ in _pages(lambda t: client.inboxes.drafts.list(
        inbox, limit=100, page_token=t, labels=[SENT]), "drafts"))
    return sent + scheduled


def find_draft(client, inbox, run_id, lead_id):
    label = lead_label(run_id, lead_id)
    page = client.inboxes.drafts.list(inbox, limit=10, labels=[label])
    return page.drafts[0] if page.drafts else None


def send_approved(client, config, run_id, lead_ids, suppressed, apply=False, now=None):
    """Send (or schedule) the drafts Terell approved by lead id. Returns one line per lead."""
    inbox, window = config["sender_inbox"], config["send_window"]
    now = now or datetime.now(ZoneInfo(window["timezone"]))
    room = daily_cap(config, now.date()) - sent_today(client, inbox, now)
    report = []
    for lead_id in lead_ids:
        draft = find_draft(client, inbox, run_id, lead_id)
        if draft is None:
            report.append((lead_id, "no draft found (run `drafts --apply` first)"))
            continue
        to = (draft.to or [""])[0]
        if email_lists.is_suppressed(to, suppressed):
            report.append((lead_id, f"{to} opted out: not sent"))
            continue
        if room <= 0:
            report.append((lead_id, "daily cap reached: approve again tomorrow"))
            continue
        room -= 1
        if in_window(now, window):
            if apply:
                client.inboxes.drafts.send(inbox, draft.draft_id, add_labels=[SENT], remove_labels=[AWAITING],
                                           idempotency_key=draft.draft_id)
            report.append((lead_id, f"{'sent' if apply else 'would send now'} to {to}"))
        else:
            at = next_window_open(now, window)
            if apply:
                client.inboxes.drafts.update(inbox, draft.draft_id, send_at=at, add_labels=[SENT],
                                             remove_labels=[AWAITING])
            report.append((lead_id, f"{'scheduled' if apply else 'would schedule'} for {at:%a %b %d %I:%M %p} to {to}"))
    return report


# --- Reply triage ------------------------------------------------------------

OPT_OUT_RE = re.compile(
    r"\b(unsubscribe|remove me|take me off|opt(ed)? out|no thanks|no thank you|not interested|"
    r"stop (emailing|contacting|messaging|sending)|please stop|don'?t (email|contact|message) (me|us)|"
    r"do not (email|contact|message) (me|us))\b", re.I)
BOUNCE_FROM_RE = re.compile(r"mailer-daemon|postmaster|mail delivery", re.I)
BOUNCE_SUBJECT_RE = re.compile(r"undeliver|delivery (status|failure|has failed)|returned mail|failure notice", re.I)
AUTO_REPLY_RE = re.compile(r"out of (the )?office|auto(matic)?[- ]?reply|away from (the )?office|on vacation", re.I)
QUOTE_START_RE = re.compile(r"^(>|On .+ wrote:|-+ ?Original Message ?-+|From: )", re.I | re.M)
ADDRESS_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def sender_address(from_field):
    found = ADDRESS_RE.findall(from_field or "")
    return found[-1].lower() if found else ""


def newest_text(body):
    """The reply above any quoted earlier email."""
    match = QUOTE_START_RE.search(body or "")
    return (body[:match.start()] if match else body or "").strip()


def classify(message, own_domains):
    """Sort one inbound message: opt_out, bounce, auto_reply or needs_terell.

    Returns (kind, address to suppress or ""). The newest text only is checked
    for opt-out wording, so our own quoted email (which has an opt-out line)
    never triggers it.
    """
    sender = sender_address(message.from_)
    subject = message.subject or ""
    body = message.extracted_text or message.text or message.preview or ""
    if BOUNCE_FROM_RE.search(message.from_ or "") or BOUNCE_SUBJECT_RE.search(subject):
        candidates = {a.lower() for a in ADDRESS_RE.findall(body)
                      if a.split("@")[-1].lower() not in own_domains and not BOUNCE_FROM_RE.search(a)}
        return ("bounce", candidates.pop()) if len(candidates) == 1 else ("bounce_unclear", "")
    if AUTO_REPLY_RE.search(subject) or AUTO_REPLY_RE.search(body[:300]):
        return "auto_reply", ""
    if OPT_OUT_RE.search(subject) or OPT_OUT_RE.search(newest_text(body)):
        return "opt_out", sender
    return "needs_terell", ""


def inbound_untriaged(client, inbox):
    for item in _pages(lambda t: client.inboxes.messages.list(inbox, limit=100, page_token=t), "messages"):
        if TRIAGED in item.labels or sender_address(item.from_) == inbox.lower():
            continue
        yield client.inboxes.messages.get(inbox, item.message_id)


def triage(client, inboxes, own_domains, apply=False):
    """Sort new replies. With apply=True, label them and return opt-outs to block."""
    results = []
    for inbox in inboxes:
        for msg in inbound_untriaged(client, inbox):
            kind, suppress = classify(msg, own_domains)
            results.append({"inbox": inbox, "message_id": msg.message_id, "thread_id": msg.thread_id,
                            "from": msg.from_, "subject": msg.subject or "", "kind": kind, "suppress": suppress,
                            "preview": (msg.extracted_text or msg.preview or "")[:400].strip()})
            if apply:
                client.inboxes.messages.update(inbox, msg.message_id, add_labels=[TRIAGED, f"6c-{kind.replace('_', '-')}"])
    return results
