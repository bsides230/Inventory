from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from db.database import create_db_engine
from db.models import Base
from server import INVENTORY_STATE, app


client = TestClient(app)


def _auth_header(subject: str, role: str = "user") -> dict[str, str]:
    token = jwt.encode(
        {"sub": subject, "email": f"{subject}@example.com", "name": subject.title(), "role": role},
        app.state.settings.auth_jwt_secret,
        algorithm=app.state.settings.auth_jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def _first_category() -> str:
    response = client.get("/api/categories")
    categories = response.json()["categories"]
    assert categories, "expected at least one inventory category in fixture data"
    return categories[0]["id"]


def setup_function() -> None:
    db_path = Path("test_auth.db")
    if db_path.exists():
        db_path.unlink()

    app.state.settings.database_url = f"sqlite:///{db_path}"
    app.state.settings.auth_jwt_secret = "test-secret-with-sufficient-length-32"
    app.state.settings.auth_jwt_algorithm = "HS256"
    engine = create_db_engine(app.state.settings.database_url)
    Base.metadata.create_all(engine)
    INVENTORY_STATE.clear()


def teardown_function() -> None:
    db_path = Path("test_auth.db")
    if db_path.exists():
        db_path.unlink()


def test_write_endpoint_rejects_anonymous_requests():
    category = _first_category()
    response = client.post(
        f"/api/inventory/{category}/update",
        json={"id": "item-1", "qty": 1, "unit": "each"},
    )
    assert response.status_code == 401


def test_authenticated_write_and_read_isolated_per_user():
    category = _first_category()
    alpha_headers = _auth_header("alpha")
    bravo_headers = _auth_header("bravo")

    items_response = client.get(f"/api/inventory/{category}", headers=alpha_headers)
    item_id = items_response.json()["items"][0]["id"]

    update_response = client.post(
        f"/api/inventory/{category}/update",
        json={"id": item_id, "qty": 5, "unit": "lb"},
        headers=alpha_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["success"] is True

    alpha_inventory = client.get(f"/api/inventory/{category}", headers=alpha_headers)
    assert alpha_inventory.status_code == 200
    alpha_items = {item["id"]: item for item in alpha_inventory.json()["items"]}
    assert alpha_items[item_id]["qty"] == 5

    bravo_inventory = client.get(f"/api/inventory/{category}", headers=bravo_headers)
    assert bravo_inventory.status_code == 200
    bravo_items = {item["id"]: item for item in bravo_inventory.json()["items"]}
    assert bravo_items[item_id]["qty"] == 0


def test_invalid_token_is_rejected():
    category = _first_category()
    response = client.post(
        f"/api/inventory/{category}/update",
        json={"id": "item-1", "qty": 1, "unit": "each"},
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
