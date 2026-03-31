import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from file_safety import write_json_atomic, with_lock

class FileOrderManager:
    def __init__(self, orders_dir: Path):
        self.orders_dir = orders_dir / "submitted"
        self.orders_dir.mkdir(parents=True, exist_ok=True)

    def _get_order_path(self, user_id: str, order_id: str) -> Path:
        return self.orders_dir / f"{user_id}_{order_id}.json"

    def _read_json(self, path: Path) -> dict:
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return None

    def _write_json(self, path: Path, data: dict):
        write_json_atomic(path, data)

    def create_order(self, user_id: str, draft: dict, export_filename: str = None, location_pin: str = None, location_name: str = None) -> dict:
        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        order = {
            "id": order_id,
            "user_id": user_id,
            "location_pin": location_pin,
            "location_name": location_name,
            "is_rush": draft.get("is_rush", False),
            "needed_by": draft.get("needed_by"),
            "export_filename": export_filename,
            "delivery_status": "pending",
            "delivery_attempts": 0,
            "delivery_error": None,
            "delivered_at": None,
            "items": draft.get("items", []),
            "submitted_at": now
        }

        path = self._get_order_path(user_id, order_id)
        self._write_json(path, order)
        return order

    def update_delivery_status(self, user_id: str, order_id: str, status: str, attempts: int, error: str = None) -> dict:
        path = self._get_order_path(user_id, order_id)
        lock_path = self.orders_dir / f".{user_id}_{order_id}.lock"
        with with_lock(lock_path):
            order = self._read_json(path)
            if not order:
                return None
            order["delivery_status"] = status
            order["delivery_attempts"] = attempts
            order["delivery_error"] = error
            if status == "sent":
                order["delivered_at"] = datetime.now(timezone.utc).isoformat()
            self._write_json(path, order)
            return order

    def get_orders(self) -> list:
        orders = []
        for file in self.orders_dir.glob("*.json"):
            order = self._read_json(file)
            if order:
                orders.append(order)
        orders.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
        return orders

    def update_order(self, user_id: str, order_id: str, items: list) -> dict:
        path = self._get_order_path(user_id, order_id)
        lock_path = self.orders_dir / f".{user_id}_{order_id}.lock"
        with with_lock(lock_path):
            order = self._read_json(path)
            if not order:
                return None
            order["items"] = items
            # Recalculate total if amounts are present
            total_amount = sum(float(item.get("amount", 0.0) or 0.0) for item in items)
            order["total_amount"] = total_amount
            self._write_json(path, order)
            return order

    def delete_order(self, user_id: str, order_id: str) -> bool:
        path = self._get_order_path(user_id, order_id)
        lock_path = self.orders_dir / f".{user_id}_{order_id}.lock"
        with with_lock(lock_path):
            order = self._read_json(path)
            if not order:
                return False

            # Remove the JSON file
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass

            # Remove the export filename if it exists
            export_filename = order.get("export_filename")
            if export_filename:
                # Could be in orders or orders/saved
                parent_dir = self.orders_dir.parent
                export_path = parent_dir / export_filename
                saved_path = parent_dir / "saved" / export_filename
                try:
                    export_path.unlink(missing_ok=True)
                    saved_path.unlink(missing_ok=True)
                except Exception:
                    pass

            # Remove the state flag file
            flags_dir = self.orders_dir.parent / "flags"
            flag_path = flags_dir / f"{order_id}.state"
            try:
                flag_path.unlink(missing_ok=True)
            except Exception:
                pass

            return True

    def get_item_frequencies(self, user_id: str = None) -> dict:
        frequencies = {}
        # Simple scan
        for file in self.orders_dir.glob("*.json"):
            if user_id and not file.name.startswith(f"{user_id}_"):
                continue

            # The user_id might be a substring or pin_ prefix in the file name,
            # let's extract the actual user_id from the JSON
            order = self._read_json(file)
            if not order:
                continue

            uid = order.get("user_id")
            if user_id and uid != user_id:
                continue

            if uid not in frequencies:
                frequencies[uid] = {}

            for item in order.get("items", []):
                i_id = item.get("item_id")
                frequencies[uid][i_id] = frequencies[uid].get(i_id, 0) + 1

        return frequencies
