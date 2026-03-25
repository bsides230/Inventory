from fastapi.testclient import TestClient

from server import app


client = TestClient(app)


def test_health_live():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_health_ready_shape():
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert "data_dir" in data["checks"]


def test_version_endpoint():
    response = client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "environment" in data


def test_status_endpoint_regression():
    response = client.get("/api/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "online"
    assert "location" in payload


def test_categories_endpoint_regression():
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["categories"], list)


def test_inventory_endpoint_regression():
    categories = client.get("/api/categories").json()["categories"]
    if categories:
        category_id = categories[0]["id"]
        response = client.get(f"/api/inventory/{category_id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert isinstance(payload["items"], list)


def test_submit_order_with_empty_state_regression():
    response = client.post(
        "/api/submit_order",
        json={"date": "2026-03-25", "is_rush": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False


def test_request_id_header_roundtrip():
    request_id = "req-123"
    response = client.get("/health/live", headers={"X-Request-ID": request_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
