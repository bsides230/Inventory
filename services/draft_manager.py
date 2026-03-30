import json
import os
from datetime import datetime, timezone
from pathlib import Path
from file_safety import write_json_atomic, with_lock

class FileDraftManager:
    def __init__(self, drafts_dir: Path):
        self.drafts_dir = drafts_dir
        self.drafts_dir.mkdir(parents=True, exist_ok=True)

    def _get_draft_path(self, user_id: str, draft_id: int) -> Path:
        return self.drafts_dir / f"{user_id}_{draft_id}.json"

    def _get_active_draft_id_path(self, user_id: str) -> Path:
        return self.drafts_dir / f"{user_id}_active.txt"

    def _read_json(self, path: Path) -> dict:
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return None

    def _write_json(self, path: Path, data: dict):
        write_json_atomic(path, data)

    def get_all_active_drafts(self, user_id: str) -> list[dict]:
        drafts = []
        for file in self.drafts_dir.glob(f"{user_id}_*.json"):
            draft = self._read_json(file)
            if draft and draft.get("state", draft.get("status")) == "active":
                drafts.append(draft)
        drafts.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
        return drafts

    def get_active_draft(self, user_id: str) -> dict:
        active_id_path = self._get_active_draft_id_path(user_id)
        if active_id_path.exists():
            active_id = active_id_path.read_text(encoding="utf-8").strip()
            draft_path = self._get_draft_path(user_id, active_id)
            draft = self._read_json(draft_path)
            if draft and draft.get("state", draft.get("status")) == "active":
                return draft
        return None

    def get_draft(self, user_id: str, draft_id: int) -> dict:
        path = self._get_draft_path(user_id, draft_id)
        return self._read_json(path)

    def set_active_draft(self, user_id: str, draft_id: int):
        self._get_active_draft_id_path(user_id).write_text(str(draft_id), encoding="utf-8")

    def create_draft(self, user_id: str, name: str = None) -> dict:
        existing = self.get_all_active_drafts(user_id)
        draft_id = 1
        if existing:
            draft_id = max(int(d["id"]) for d in existing) + 1

        now = datetime.now(timezone.utc).isoformat()
        draft = {
            "id": str(draft_id),
            "user_id": user_id,
            "draft_name": name or f"Draft {len(existing) + 1}",
            "state": "active",
            "version": 1,
            "is_rush": False,
            "needed_by": None,
            "items": [],
            "created_at": now,
            "updated_at": now
        }
        self._write_json(self._get_draft_path(user_id, draft_id), draft)
        self.set_active_draft(user_id, draft_id)
        return draft

    def update_draft(self, user_id: str, draft_id: int, items=None, is_rush=None, needed_by=None, name=None, state=None, expected_version: int = None):
        path = self._get_draft_path(user_id, draft_id)
        lock_path = self.drafts_dir / f"{user_id}.lock"
        with with_lock(lock_path):
            draft = self._read_json(path)
            if not draft:
                return None
            if expected_version is not None and draft.get("version", 1) != expected_version:
                raise ValueError(f"Version mismatch: expected {expected_version}, got {draft.get('version', 1)}")

            if items is not None:
                draft["items"] = items
            if is_rush is not None:
                draft["is_rush"] = is_rush
            if needed_by is not None:
                draft["needed_by"] = needed_by
            if name is not None:
                draft["draft_name"] = name
            if state is not None:
                draft["state"] = state

            draft["version"] = draft.get("version", 1) + 1
            draft["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_json(path, draft)
            return draft

    def delete_draft(self, user_id: str, draft_id: int) -> bool:
        path = self._get_draft_path(user_id, draft_id)
        if path.exists():
            path.unlink()

            # Update active draft pointer if deleted
            active_id_path = self._get_active_draft_id_path(user_id)
            if active_id_path.exists() and active_id_path.read_text(encoding="utf-8").strip() == str(draft_id):
                active_id_path.unlink()
                existing = self.get_all_active_drafts(user_id)
                if existing:
                    self.set_active_draft(user_id, int(existing[0]["id"]))
            return True
        return False
