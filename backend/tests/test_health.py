from fastapi.testclient import TestClient
from app.main import app

def test_liveness() -> None:
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_preflight_does_not_require_authentication() -> None:
    response = TestClient(app).options(
        "/api/v1/admin/users",
        headers={
            "Origin": "http://localhost:5000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type,accept,x-requested-with",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5000"
    assert "GET" in response.headers["access-control-allow-methods"]
    assert "Authorization" in response.headers["access-control-allow-headers"]
    assert "X-Requested-With" in response.headers["access-control-allow-headers"]


def test_cors_allows_flutter_chrome_random_local_port() -> None:
    response = TestClient(app).options(
        "/api/v1/admin/dashboard",
        headers={
            "Origin": "http://localhost:54831",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:54831"
