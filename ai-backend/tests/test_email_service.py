"""Regression coverage for secrets in development-mode email logging."""

from app.services import email_service


class _RecordingLogger:
    def __init__(self):
        self.calls = []

    def info(self, message, *args):
        self.calls.append((message, args))


def test_development_email_log_never_contains_recipient_or_message_body(monkeypatch):
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "")
    recording_logger = _RecordingLogger()
    monkeypatch.setattr(email_service, "logger", recording_logger)

    recipient = "reset-recipient@example.test"
    subject = "إعادة تعيين كلمة المرور"
    secret_token = "synthetic-password-reset-token-never-log"
    body = (
        "https://frontend.example.test/reset-password"
        f"?token={secret_token}"
    )

    email_service.send_email(recipient, subject, body)

    assert len(recording_logger.calls) == 1
    message, args = recording_logger.calls[0]
    rendered_log = " ".join([message, *(str(value) for value in args)])

    assert "DEV MODE" in message
    assert subject in rendered_log
    assert recipient not in rendered_log
    assert secret_token not in rendered_log
    assert body not in rendered_log
