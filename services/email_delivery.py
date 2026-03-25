from __future__ import annotations

import json
import logging
import smtplib
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path

from services.recipients import RecipientConfigStore

logger = logging.getLogger(__name__)


@dataclass
class EmailDeliveryResult:
    status: str
    attempts: int
    error: str | None = None


@dataclass
class SmtpEmailClient:
    host: str
    port: int
    username: str | None
    password: str | None
    use_tls: bool

    def send(self, *, sender: str, recipients: list[str], message: EmailMessage) -> None:
        with smtplib.SMTP(self.host, self.port, timeout=10) as client:
            if self.use_tls:
                client.starttls()
            if self.username and self.password:
                client.login(self.username, self.password)
            client.send_message(message, from_addr=sender, to_addrs=recipients)


@dataclass
class OrderEmailDeliveryService:
    recipient_store: RecipientConfigStore
    smtp_client: SmtpEmailClient
    sender_email: str
    max_attempts: int
    retry_delay_seconds: float
    dead_letter_log_path: Path

    def send_order_email(
        self,
        *,
        order_id: int,
        location: str,
        date: str,
        is_rush: bool,
        needed_by: str | None,
        export_path: Path,
    ) -> EmailDeliveryResult:
        recipients = self.recipient_store.get_recipients()
        message = self._build_message(
            recipients=recipients,
            order_id=order_id,
            location=location,
            date=date,
            is_rush=is_rush,
            needed_by=needed_by,
            export_path=export_path,
        )

        attempts = 0
        last_error: str | None = None
        while attempts < self.max_attempts:
            attempts += 1
            try:
                self.smtp_client.send(sender=self.sender_email, recipients=recipients, message=message)
                return EmailDeliveryResult(status="sent", attempts=attempts)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                logger.error(
                    "Order email send failed order_id=%s attempt=%s/%s error=%s",
                    order_id,
                    attempts,
                    self.max_attempts,
                    last_error,
                )
                if attempts >= self.max_attempts:
                    break
                time.sleep(self.retry_delay_seconds)

        self._write_dead_letter(order_id=order_id, recipients=recipients, error=last_error or "unknown")
        return EmailDeliveryResult(status="failed", attempts=attempts, error=last_error)

    def _build_message(
        self,
        *,
        recipients: list[str],
        order_id: int,
        location: str,
        date: str,
        is_rush: bool,
        needed_by: str | None,
        export_path: Path,
    ) -> EmailMessage:
        message = EmailMessage()
        rush_prefix = "URGENT " if is_rush else ""
        message["Subject"] = f"{rush_prefix}Order #{order_id} - {location} - {date}"
        message["From"] = self.sender_email
        message["To"] = ", ".join(recipients)
        body_lines = [
            f"Location: {location}",
            f"Order ID: {order_id}",
            f"Date: {date}",
            f"Rush: {'yes' if is_rush else 'no'}",
            f"Needed By: {needed_by or '-'}",
            f"Attachment: {export_path.name}",
        ]
        message.set_content("\n".join(body_lines))
        attachment_bytes = export_path.read_bytes()
        message.add_attachment(
            attachment_bytes,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=export_path.name,
        )
        return message

    def _write_dead_letter(self, *, order_id: int, recipients: list[str], error: str) -> None:
        self.dead_letter_log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "order_id": order_id,
            "recipients": recipients,
            "error": error,
        }
        with self.dead_letter_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
