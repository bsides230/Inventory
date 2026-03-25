from pathlib import Path

from services.email_delivery import OrderEmailDeliveryService, SmtpEmailClient
from services.recipients import RecipientConfigStore


class FlakySmtpClient(SmtpEmailClient):
    def __init__(self, failures_before_success: int):
        super().__init__(host="localhost", port=1025, username=None, password=None, use_tls=False)
        self.failures_before_success = failures_before_success
        self.attempts = 0

    def send(self, *, sender: str, recipients: list[str], message):
        self.attempts += 1
        if self.attempts <= self.failures_before_success:
            raise RuntimeError("transient smtp error")


def _build_service(tmp_path: Path, smtp_client: SmtpEmailClient, attempts: int = 3) -> OrderEmailDeliveryService:
    recipient_path = tmp_path / "order_recipients.txt"
    recipient_path.write_text("ops@example.com\n")
    export = tmp_path / "order.xlsx"
    export.write_bytes(b"xlsx")

    return OrderEmailDeliveryService(
        recipient_store=RecipientConfigStore(recipient_path),
        smtp_client=smtp_client,
        sender_email="inventory@example.com",
        max_attempts=attempts,
        retry_delay_seconds=0,
        dead_letter_log_path=tmp_path / "dead_letter.log",
    )


def test_email_delivery_retries_and_succeeds(tmp_path):
    smtp_client = FlakySmtpClient(failures_before_success=2)
    service = _build_service(tmp_path, smtp_client, attempts=3)

    export = tmp_path / "order.xlsx"
    result = service.send_order_email(
        order_id=10,
        location="Falcones Pizza",
        date="2026-03-25",
        is_rush=False,
        needed_by=None,
        export_path=export,
    )

    assert result.status == "sent"
    assert result.attempts == 3
    assert result.error is None


def test_email_delivery_logs_dead_letter_after_final_failure(tmp_path):
    smtp_client = FlakySmtpClient(failures_before_success=10)
    service = _build_service(tmp_path, smtp_client, attempts=2)

    export = tmp_path / "order.xlsx"
    result = service.send_order_email(
        order_id=11,
        location="Falcones Pizza",
        date="2026-03-25",
        is_rush=True,
        needed_by="8AM",
        export_path=export,
    )

    assert result.status == "failed"
    assert result.attempts == 2
    assert service.dead_letter_log_path.exists()
