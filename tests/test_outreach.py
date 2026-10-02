import json
from datetime import datetime
from types import SimpleNamespace as NS
from zoneinfo import ZoneInfo

import pytest

import qualify
from partner_qualifier import outreach

CHI = ZoneInfo("America/Chicago")
CONFIG = json.loads((qualify.CONFIG / "outreach.json").read_text())
INBOX = CONFIG["sender_inbox"]


def page(key, items):
    return NS(**{key: items, "next_page_token": None})


class FakeDrafts:
    def __init__(self):
        self.items, self.sent, self.updated = [], [], []

    def list(self, inbox, *, limit=None, page_token=None, labels=None):
        return page("drafts", [d for d in self.items if set(labels or []) <= set(d.labels)])

    def create(self, inbox, *, to, subject, text, labels):
        draft = NS(draft_id=f"d{len(self.items)}", to=to, subject=subject, text=text, labels=list(labels))
        self.items.append(draft)
        return draft

    def send(self, inbox, draft_id, *, add_labels, remove_labels, idempotency_key):
        self.sent.append(draft_id)

    def update(self, inbox, draft_id, *, send_at, add_labels, remove_labels):
        self.updated.append((draft_id, send_at))


class FakeMessages:
    def __init__(self, messages=(), sent_today=0):
        self.messages = list(messages)
        self.sent_today = sent_today
        self.labelled = {}

    def list(self, inbox, *, limit=None, page_token=None, labels=None, after=None):
        if labels == [outreach.SENT]:
            return page("messages", [NS(labels=[outreach.SENT])] * self.sent_today)
        if labels:
            return page("messages", [m for m in self.messages if set(labels) <= set(m.labels)])
        return page("messages", self.messages)

    def get(self, inbox, message_id):
        return next(m for m in self.messages if m.message_id == message_id)

    def update(self, inbox, message_id, *, add_labels):
        self.labelled[message_id] = add_labels


def client(messages=(), sent_today=0):
    return NS(inboxes=NS(drafts=FakeDrafts(), messages=FakeMessages(messages, sent_today),
                         list=lambda limit=None, page_token=None: page("inboxes", [NS(email="terell@6cpartners.com")])))


def row(lead_id, **over):
    base = {"lead_id": lead_id, "business_name": f"Biz {lead_id}", "verdict": "MESSAGE",
            "contact": {"email": f"owner@{lead_id.lower()}.example", "email_free_mail": False, "best": "Email"},
            "email": {"status": "Draft: needs Terell's approval", "subject": "Paid jobs in Lakeview",
                      "full_text": "Hi there...\n\nTerell John", "failed": []}}
    for key, value in over.items():
        base[key] = {**base[key], **value} if isinstance(value, dict) else value
    return base


def test_inbox_plan_finds_missing():
    existing, missing = outreach.plan_inboxes(client(), CONFIG["inboxes"])
    assert [s["address"] for s in existing] == ["terell@6cpartners.com"]
    assert "partners@6cpartners.com" in [s["address"] for s in missing]
    assert all(s["domain"] != "gmail.com" for s in CONFIG["inboxes"])


def test_draft_candidates_skip_with_reasons():
    rows = [row("L1"), row("L2", verdict="VERIFY"),
            row("L3", email={"status": "Needs rewrite", "failed": ["Exactly one question"]}),
            row("L4", contact={"email": "x@gmail.com", "email_free_mail": True, "email_listed_at": ""}),
            row("L5", contact={"email": "gone@l5.example"}),
            row("L6", contact={"email": "", "best": "Phone (312) 555-0100"}),
            row("L7", email={"full_text": "Hi\n[YOUR PHONE]"})]
    ready, skipped = outreach.draft_candidates(rows, {"gone@l5.example"})
    assert [r["lead_id"] for r in ready] == ["L1"]
    why = {s["lead_id"]: s["why"] for s in skipped}
    assert "VERIFY" in why["L2"] and "Exactly one question" in why["L3"]
    assert "free-mail" in why["L4"] and "opt-out" in why["L5"]
    assert "Phone" in why["L6"] and "sender.json" in why["L7"]


def test_drafts_are_labelled_and_never_duplicated():
    c = client()
    item = outreach.draft_candidates([row("L1")], set())[0][0]
    outreach.create_draft(c, INBOX, "2026-10-02_chicago", item)
    label = outreach.lead_label("2026-10-02_chicago", "L1")
    assert label == "6c-lead-2026-10-02-chicago-l1"
    assert label in outreach.existing_lead_labels(c, INBOX)
    assert outreach.AWAITING in c.inboxes.drafts.items[0].labels


def test_send_requires_apply_respects_cap_optouts_and_window():
    c = client(sent_today=9)  # warm-up cap is 10
    for lead in ("L1", "L2", "L3"):
        outreach.create_draft(c, INBOX, "r", {"lead_id": lead, "to": f"o@{lead.lower()}.example",
                                                "subject": "s", "text": "t"})
    tuesday_10am = datetime(2026, 10, 6, 10, 0, tzinfo=CHI)
    dry = dict(outreach.send_approved(c, CONFIG, "r", ["L1", "L2", "L9"], set(), now=tuesday_10am))
    assert dry["L1"].startswith("would send") and "cap" in dry["L2"] and "no draft" in dry["L9"]
    assert c.inboxes.drafts.sent == []

    c.inboxes.messages.sent_today = 0
    done = dict(outreach.send_approved(c, CONFIG, "r", ["L1", "L3"], {"o@l3.example"}, apply=True, now=tuesday_10am))
    assert done["L1"].startswith("sent") and "opted out" in done["L3"]
    assert c.inboxes.drafts.sent == ["d0"]

    saturday = datetime(2026, 10, 10, 11, 0, tzinfo=CHI)
    later = dict(outreach.send_approved(c, CONFIG, "r", ["L2"], set(), apply=True, now=saturday))
    assert "scheduled for Mon Oct 12 09:00 AM" in later["L2"]


def test_daily_cap_after_warmup():
    cfg = {**CONFIG, "warmup_start": "2026-09-01"}
    assert outreach.daily_cap(cfg, datetime(2026, 9, 10).date()) == 10
    assert outreach.daily_cap(cfg, datetime(2026, 10, 2).date()) == 30


def msg(mid, sender, subject, text, labels=()):
    return NS(message_id=mid, thread_id="t" + mid, from_=sender, subject=subject, text=text,
              extracted_text=None, preview=text[:50], labels=list(labels))


OWN = {"6cpartners.com"}


@pytest.mark.parametrize("message,kind,suppress", [
    (msg("1", "Ana <ana@clean.example>", "Re: Paid jobs", "Sounds good, how does pricing work?\n\nOn Mon Terell wrote:\n> reply 'no thanks'"),
     "needs_terell", ""),
    (msg("2", "Bo <bo@pest.example>", "Re: Paid jobs", "No thanks, please remove me."), "opt_out", "bo@pest.example"),
    (msg("3", "Mail Delivery Subsystem <mailer-daemon@googlemail.com>", "Delivery Status Notification (Failure)",
         "Your message to gone@detail.example couldn't be delivered. From terell@6cpartners.com"), "bounce", "gone@detail.example"),
    (msg("4", "Cy <cy@x.example>", "Automatic reply: Paid jobs", "I am out of the office until Monday."), "auto_reply", ""),
])
def test_classify(message, kind, suppress):
    assert outreach.classify(message, OWN) == (kind, suppress)


def test_triage_skips_own_and_already_triaged_and_labels():
    msgs = [msg("1", "Ana <ana@clean.example>", "Re: hi", "Interested!"),
            msg("2", "Terell <terell@6cpartners.com>", "hi", "outbound"),
            msg("3", "Bo <bo@x.example>", "Re: hi", "stop emailing me", labels=[outreach.TRIAGED])]
    c = client(messages=msgs)
    results = outreach.triage(c, [INBOX], OWN, apply=True)
    assert [r["message_id"] for r in results] == ["1"]
    assert c.inboxes.messages.labelled["1"] == [outreach.TRIAGED, "6c-needs-terell"]
