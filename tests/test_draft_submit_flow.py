from pathlib import Path

import jwt
from fastapi.testclient import TestClient
import json

from server import app, DRAFTS_DIR, ORDERS_DIR

client = TestClient(app)


def _auth_header(subject: str) -> dict[str, str]:
    token = jwt.encode(
        {"sub": subject, "email": f"{subject}@example.com", "name": subject.title(), "role": "user"},
        app.state.settings.auth_jwt_secret,
        algorithm=app.state.settings.auth_jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def _first_category_and_item() -> tuple[str, str]:
    categories_response = client.get("/api/categories")
    categories = categories_response.json()["categories"]
    assert categories, "expected category fixture data"
    category_id = categories[0]["id"]
    inventory_response = client.get(f"/api/inventory/{category_id}")
    items = inventory_response.json()["items"]
    assert items, "expected item fixture data"
    return category_id, items[0]["id"]


def setup_function() -> None:
    app.state.settings.auth_jwt_secret = "test-secret-with-sufficient-length-32"
    app.state.settings.auth_jwt_algorithm = "HS256"
    if DRAFTS_DIR.exists():
        for f in DRAFTS_DIR.glob("*"):
            if f.is_file():
                f.unlink()
    if ORDERS_DIR.exists():
        for f in ORDERS_DIR.rglob("*"):
            if f.is_file():
                f.unlink()

def teardown_function() -> None:
    if DRAFTS_DIR.exists():
        for f in DRAFTS_DIR.glob("*"):
            if f.is_file():
                f.unlink()
    if ORDERS_DIR.exists():
        for f in ORDERS_DIR.rglob("*"):
            if f.is_file():
                f.unlink()
    ipc_inbox = Path("ipc/inbox")
    if ipc_inbox.exists():
        for f in ipc_inbox.glob("*"):
            if f.is_file():
                f.unlink()

def run_ipc_worker_once():
    # Helper to run the worker processing synchronously for tests
    from services.ipc_worker import process_event
    ipc_inbox = Path("ipc/inbox")
    events = list(ipc_inbox.glob("*.json"))
    for event_file in events:
        process_event(event_file)

def test_submit_is_isolated_per_user_and_clears_only_submitter_draft():
    category, item_id = _first_category_and_item()
    alpha = _auth_header("alpha")
    bravo = _auth_header("bravo")

    assert client.post(
        f"/api/inventory/{category}/update",
        json={"id": item_id, "qty": 3, "unit": "each"},
        headers=alpha,
    ).status_code == 200
    assert client.post(
        f"/api/inventory/{category}/update",
        json={"id": item_id, "qty": 7, "unit": "each"},
        headers=bravo,
    ).status_code == 200

    submit = client.post(
        "/api/submit_order",
        json={"date": "2026-03-25", "is_rush": False},
        headers=alpha,
    )
    assert submit.status_code == 200
    assert submit.json()["success"] is True

    alpha_inventory = client.get(f"/api/inventory/{category}", headers=alpha).json()["items"]
    bravo_inventory = client.get(f"/api/inventory/{category}", headers=bravo).json()["items"]
    alpha_qty = {item["id"]: item["qty"] for item in alpha_inventory}[item_id]
    bravo_qty = {item["id"]: item["qty"] for item in bravo_inventory}[item_id]
    assert alpha_qty == 0
    assert bravo_qty == 7


def test_submit_rolls_back_if_export_fails(monkeypatch):
    category, item_id = _first_category_and_item()
    alpha = _auth_header("alpha")
    assert client.post(
        f"/api/inventory/{category}/update",
        json={"id": item_id, "qty": 2, "unit": "lb"},
        headers=alpha,
    ).status_code == 200

    def fail_export(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr("pandas.DataFrame.to_excel", fail_export)

    submit = client.post(
        "/api/submit_order",
        json={"date": "2026-03-25", "is_rush": False},
        headers=alpha,
    )
    assert submit.status_code == 200
    assert submit.json()["success"] is False

    assert len(list((ORDERS_DIR / "submitted").glob("*.json"))) == 0
    active_drafts = 0
    for file in DRAFTS_DIR.glob("alpha_*.json"):
        with open(file, "r") as f:
            d = json.load(f)
            if d.get("state", d.get("status")) == "active":
                active_drafts += 1
    assert active_drafts == 1

    alpha_inventory = client.get(f"/api/inventory/{category}", headers=alpha).json()["items"]
    alpha_qty = {item["id"]: item["qty"] for item in alpha_inventory}[item_id]
    assert alpha_qty == 2


def test_end_to_end_draft_update_then_submit_lifecycle():
    category, item_id = _first_category_and_item()
    alpha = _auth_header("alpha")

    update = client.post(
        f"/api/inventory/{category}/update",
        json={"id": item_id, "qty": 5, "unit": "each"},
        headers=alpha,
    )
    assert update.status_code == 200

    before_submit = client.get(f"/api/inventory/{category}", headers=alpha).json()["items"]
    assert {item["id"]: item["qty"] for item in before_submit}[item_id] == 5

    submit = client.post(
        "/api/submit_order",
        json={"date": "2026-03-25", "is_rush": True, "needed_by": "Noon"},
        headers=alpha,
    )
    assert submit.status_code == 200
    payload = submit.json()
    assert payload["success"] is True
    assert payload["filename"].endswith(".xlsx")

    # Run IPC worker
    run_ipc_worker_once()

    assert len(list((ORDERS_DIR / "submitted").glob("*.json"))) == 1

    after_submit = client.get(f"/api/inventory/{category}", headers=alpha).json()["items"]
    assert {item["id"]: item["qty"] for item in after_submit}[item_id] == 0


def test_submit_persists_local_artifact_when_email_delivery_fails(monkeypatch):
    category, item_id = _first_category_and_item()
    alpha = _auth_header("alpha")

    assert client.post(
        f"/api/inventory/{category}/update",
        json={"id": item_id, "qty": 1, "unit": "each"},
        headers=alpha,
    ).status_code == 200

    class FailingDeliveryService:
        def send_order_email(self, **kwargs):
            from services.email_delivery import EmailDeliveryResult

            return EmailDeliveryResult(status="failed", attempts=3, error="smtp down")

    import services.ipc_worker
    monkeypatch.setattr(services.ipc_worker, "build_email_service", lambda: FailingDeliveryService())

    submit = client.post(
        "/api/submit_order",
        json={"date": "2026-03-25", "is_rush": False},
        headers=alpha,
    )
    payload = submit.json()
    assert submit.status_code == 200
    assert payload["success"] is True
    assert payload["delivery_status"] == "pending"
    assert Path("orders", payload["filename"]).exists()

    run_ipc_worker_once()

    order_files = list((ORDERS_DIR / "submitted").glob("*.json"))
    assert len(order_files) == 1
    with open(order_files[0], "r") as f:
        saved_order = json.load(f)
        assert saved_order is not None
        assert saved_order.get("delivery_status") == "failed"
