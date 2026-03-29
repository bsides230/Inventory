from pathlib import Path

from fastapi.testclient import TestClient

from server import InMemoryRateLimiter, app, settings


client = TestClient(app)


def test_rate_limit_guard_returns_429_when_threshold_exceeded():
    original_limiter = app.state.rate_limiter
    app.state.rate_limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)

    try:
        first = client.get("/health/live")
        second = client.get("/health/live")
    finally:
        app.state.rate_limiter = original_limiter

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "Rate limit exceeded"


def test_request_size_guard_returns_413_for_large_payload():
    original_limit = settings.max_request_body_bytes
    settings.max_request_body_bytes = 32

    try:
        response = client.post(
            "/api/submit_order",
            json={"date": "X" * 100, "is_rush": False},
        )
    finally:
        settings.max_request_body_bytes = original_limit

    assert response.status_code == 413
    assert response.json()["detail"] == "Request body too large"


def test_compose_and_proxy_artifacts_exist_with_expected_services():
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")
    caddy_text = Path("Caddyfile").read_text(encoding="utf-8")

    for service_name in ["api:", "proxy:", "backup_worker:"]:
        assert service_name in compose_text

    assert "reverse_proxy" in caddy_text
    assert "{$APP_DOMAIN}" in caddy_text
