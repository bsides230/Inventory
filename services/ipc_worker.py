import json
import logging
import time
from pathlib import Path
import shutil
import os
import sys

# Add the parent directory to sys.path so we can import from server
sys.path.append(str(Path(__file__).parent.parent))

from server import build_email_service
from services.order_manager import FileOrderManager
from file_safety import append_jsonl

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

IPC_INBOX = Path("ipc/inbox")
IPC_PROCESSING = Path("ipc/processing")
IPC_DONE = Path("ipc/done")
IPC_FAILED = Path("ipc/failed")

ORDERS_DIR = Path("orders")
EVENTS_LOG = Path("logs/events.jsonl")

for d in [IPC_INBOX, IPC_PROCESSING, IPC_DONE, IPC_FAILED, ORDERS_DIR, ORDERS_DIR / "flags"]:
    d.mkdir(parents=True, exist_ok=True)

def process_event(event_file: Path):
    processing_file = IPC_PROCESSING / event_file.name
    try:
        shutil.move(str(event_file), str(processing_file))
    except FileNotFoundError:
        return # Someone else grabbed it

    with open(processing_file, "r") as f:
        event = json.load(f)

    logger.info(f"Processing event {event['event_id']} of type {event['event_type']}")

    if event["event_type"] == "email_send":
        payload = event["payload"]
        order_id = payload["order_id"]

        email_service = build_email_service()
        delivery = email_service.send_order_email(
            order_id=order_id,
            location=payload["location"],
            date=payload["date"],
            is_rush=payload["is_rush"],
            needed_by=payload["needed_by"],
            export_path=Path(payload["export_path"]),
        )

        # Transition state flag
        flag_path = ORDERS_DIR / "flags" / f"{order_id}.state"
        if delivery.status == "sent":
            flag_path.write_text("emailed", encoding="utf-8")
            shutil.move(str(processing_file), str(IPC_DONE / processing_file.name))
        else:
            flag_path.write_text("email_failed", encoding="utf-8")
            shutil.move(str(processing_file), str(IPC_FAILED / processing_file.name))

        # Log transition
        append_jsonl(EVENTS_LOG, {
            "timestamp": event["timestamp"],
            "event_id": event["event_id"],
            "order_id": order_id,
            "status": delivery.status,
            "attempts": delivery.attempts,
            "error": delivery.error
        })

        # Update order delivery status
        order_manager = FileOrderManager(ORDERS_DIR)
        # We need the user_id to update the order. Let's find the order file.
        # It's <user_id>_<order_id>.json in orders/submitted
        submitted_dir = ORDERS_DIR / "submitted"
        user_id = None
        for f in submitted_dir.glob(f"*_{order_id}.json"):
            user_id = f.name.replace(f"_{order_id}.json", "")
            break

        if user_id:
            order_manager.update_delivery_status(
                user_id=user_id,
                order_id=order_id,
                status=delivery.status,
                attempts=delivery.attempts,
                error=delivery.error
            )
        else:
            logger.warning(f"Order file for {order_id} not found to update delivery status.")

    else:
        logger.warning(f"Unknown event type: {event['event_type']}")
        shutil.move(str(processing_file), str(IPC_FAILED / processing_file.name))


def recover_processing():
    for f in IPC_PROCESSING.glob("*.json"):
        logger.info(f"Recovering stranded event {f.name}")
        shutil.move(str(f), str(IPC_INBOX / f.name))

def run_worker():
    logger.info("Starting IPC worker...")
    recover_processing()

    while True:
        try:
            events = sorted(IPC_INBOX.glob("*.json"))
            if events:
                for event_file in events:
                    process_event(event_file)
            else:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Worker stopped.")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            time.sleep(5)

if __name__ == "__main__":
    run_worker()
