"""Tests for transaction-aware audit logging."""
import logging

from app.audit import log_event, log_event_to_logger


class FakeSession:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_log_event_with_deferred_commit_does_not_emit_success_log_after_rollback(caplog):
    db = FakeSession()

    with caplog.at_level(logging.INFO, logger="app.audit"):
        log_event(
            db,
            "account_deleted",
            "حذف حساب: user@example.test",
            42,
            commit=False,
        )

    db.rollback()

    assert len(db.added) == 1
    assert db.commits == 0
    assert db.rollbacks == 1
    assert "account_deleted" not in caplog.text


def test_deferred_audit_log_is_emitted_only_when_explicitly_requested(caplog):
    db = FakeSession()

    with caplog.at_level(logging.INFO, logger="app.audit"):
        log_event(db, "account_deleted", "حذف حساب: user@example.test", 42, commit=False)
        assert "account_deleted" not in caplog.text

        db.commit()
        log_event_to_logger("account_deleted", "حذف حساب: user@example.test")

    assert db.commits == 1
    assert caplog.text.count("account_deleted") == 1


def test_default_log_event_commits_and_emits_log(caplog):
    db = FakeSession()

    with caplog.at_level(logging.INFO, logger="app.audit"):
        log_event(db, "profile_updated", "تحديث الملف الشخصي", 42)

    assert db.commits == 1
    assert "profile_updated" in caplog.text
