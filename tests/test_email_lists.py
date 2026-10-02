from argparse import Namespace
from types import SimpleNamespace

import pytest

import qualify
from partner_qualifier import email_lists


class FakeLists:
    """Stands in for client.lists: two-entry pages so pagination is exercised."""

    def __init__(self, existing=()):
        self.store = {}
        for direction, list_type, entry in existing:
            self.store.setdefault((direction, list_type), []).append(entry)
        self.created = []

    def list(self, direction, list_type, *, limit=None, page_token=None):
        entries = sorted(self.store.get((direction, list_type), []))
        start = int(page_token or 0)
        page = entries[start:start + 2]
        token = str(start + 2) if start + 2 < len(entries) else None
        return SimpleNamespace(entries=[SimpleNamespace(entry=e) for e in page], next_page_token=token)

    def create(self, direction, list_type, *, entry, reason=None):
        if entry == "broken.example":
            raise RuntimeError("400 bad entry")
        self.store.setdefault((direction, list_type), []).append(entry)
        self.created.append((direction, list_type, entry, reason))


def fake_client(existing=()):
    return SimpleNamespace(lists=FakeLists(existing))


def test_clean_entry_refuses_free_mail_domains_and_junk():
    assert email_lists.clean_entry(" Owner@Biz.Example ") == ("owner@biz.example", "")
    assert email_lists.clean_entry("ourbrand.com") == ("ourbrand.com", "")
    assert "free-mail" in email_lists.clean_entry("gmail.com")[1]
    assert "not an email" in email_lists.clean_entry("not an email")[1]
    assert email_lists.clean_entry("someone@gmail.com")[1] == ""  # a full Gmail address is fine


def test_desired_entries_builds_each_list(tmp_path):
    config = {"own_domains": ["ourbrand.com", "gmail.com"], "own_addresses": ["us@gmail.com"],
              "blocked_senders": ["spam.example", {"entry": "x@spam2.example", "reason": "Phishing"}],
              "restrict_send_to_approved_partners": False}
    supp = tmp_path / "s.jsonl"
    email_lists.add_suppression(supp, "Stop@Biz.Example", "Replied no thanks", "reply")
    entries, problems = email_lists.desired_entries(config, email_lists.read_suppression(supp),
                                                    [("p@partner.example", "Partner Co")])
    got = {(e["direction"], e["type"], e["entry"]) for e in entries}
    assert got == {("receive", "allow", "ourbrand.com"), ("receive", "allow", "us@gmail.com"),
                   ("receive", "block", "spam.example"), ("receive", "block", "x@spam2.example"),
                   ("send", "block", "stop@biz.example"), ("reply", "block", "stop@biz.example")}
    assert len(problems) == 1 and "gmail.com" in problems[0]  # bare free-mail domain refused
    assert next(e for e in entries if e["direction"] == "send")["reason"].startswith("Opt-out ")


def test_partners_only_added_when_restricted_and_never_if_opted_out(tmp_path):
    supp = tmp_path / "s.jsonl"
    email_lists.add_suppression(supp, "gone@partner.example", "no thanks")
    partners = [("p@partner.example", "Partner Co"), ("gone@partner.example", "Gone Co"), ("", "No Email")]
    config = {"restrict_send_to_approved_partners": True}
    entries, _ = email_lists.desired_entries(config, email_lists.read_suppression(supp), partners)
    allow = [e["entry"] for e in entries if (e["direction"], e["type"]) == ("send", "allow")]
    assert allow == ["p@partner.example"]


def test_add_suppression_is_idempotent(tmp_path):
    supp = tmp_path / "s.jsonl"
    assert email_lists.add_suppression(supp, "a@b.example", "no")
    assert email_lists.add_suppression(supp, "A@B.example", "no") is None
    with pytest.raises(ValueError):
        email_lists.add_suppression(supp, "yahoo.com", "no")
    assert len(email_lists.read_suppression(supp)) == 1


def test_sync_dry_run_then_apply_never_deletes():
    client = fake_client([("receive", "allow", "ourbrand.com"), ("receive", "allow", "old.example"),
                          ("receive", "allow", "a.example"), ("receive", "allow", "b.example")])
    entries = [{"direction": "receive", "type": "allow", "entry": "ourbrand.com", "reason": "own"},
               {"direction": "send", "type": "block", "entry": "stop@biz.example", "reason": "opt-out"},
               {"direction": "receive", "type": "block", "entry": "broken.example", "reason": "spam"}]
    dry = email_lists.sync(client, entries)
    assert [e["entry"] for e in dry["to_add"]] == ["broken.example", "stop@biz.example"]
    assert client.lists.created == []
    assert {e["entry"] for e in dry["extra"]} == {"old.example", "a.example", "b.example"}  # found across pages

    done = email_lists.sync(client, entries, apply=True)
    assert [e["entry"] for e in done["added"]] == ["stop@biz.example"]
    assert done["failed"][0]["error"] == "400 bad entry"
    assert "old.example" in client.lists.store[("receive", "allow")]  # left alone


def test_prepare_marks_opted_out_leads_do_not_contact(tmp_path, monkeypatch, leads):
    supp = tmp_path / "suppression.jsonl"
    target = leads["L0001"]["email"]
    email_lists.add_suppression(supp, target, "no thanks")
    monkeypatch.setattr(qualify, "SUPPRESSION", supp)
    monkeypatch.setattr(qualify, "RUNS", tmp_path / "runs")
    monkeypatch.delenv("AGENTMAIL_API_KEY", raising=False)
    qualify.cmd_prepare(Namespace(file=str(qualify.ROOT / "tests/fixtures/sample_igleads.csv"),
                                  market="Chicago, IL", run="t", batch_size=5, limit=None))
    out = {l["lead_id"]: l for l in qualify.load_jsonl(tmp_path / "runs/t/leads.jsonl")}
    assert out["L0001"]["screen"] == "skip_opted_out"
    from partner_qualifier.rubric import score
    assert score(out["L0001"], None, "Chicago, IL")["verdict"] == "DO NOT CONTACT"


@pytest.fixture
def leads():
    from partner_qualifier.normalize import normalize, read_rows
    rows = read_rows(qualify.ROOT / "tests/fixtures/sample_igleads.csv")
    return {l["lead_id"]: l for l in normalize(rows, "Chicago, IL")}
