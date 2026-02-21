from extensions import db
from models.refresh_token import RefreshToken


def test_login_success_returns_tokens(client, create_user):
    create_user("diana")

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "diana", "password": "Password123!", "device_id": "pixel-1"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["access_token"]
    assert payload["data"]["refresh_token"]
    assert payload["data"]["expires_in"] > 0


def test_login_invalid_credentials(client, create_user):
    create_user("diana")

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "diana", "password": "WrongPassword123!"},
    )

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_refresh_rotates_token(client, create_user, app):
    create_user("diana")

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "diana", "password": "Password123!", "device_id": "pixel-1"},
    )
    first_refresh = login_response.get_json()["data"]["refresh_token"]

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh, "device_id": "pixel-1"},
    )
    assert refresh_response.status_code == 200
    second_refresh = refresh_response.get_json()["data"]["refresh_token"]
    assert second_refresh != first_refresh

    reused_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh, "device_id": "pixel-1"},
    )
    assert reused_response.status_code == 401
    assert reused_response.get_json()["error"]["code"] == "AUTH_INVALID_REFRESH"

    with app.app_context():
        revoked_tokens = RefreshToken.query.filter(RefreshToken.revoked_at.isnot(None)).count()
        assert revoked_tokens >= 1


def test_logout_revokes_refresh_token(client, create_user):
    create_user("diana")
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "diana", "password": "Password123!", "device_id": "pixel-1"},
    )
    refresh_token = login_response.get_json()["data"]["refresh_token"]

    logout_response = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 200
    assert logout_response.get_json()["data"]["revoked"] is True

    reused_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token, "device_id": "pixel-1"},
    )
    assert reused_response.status_code == 401
    assert reused_response.get_json()["error"]["code"] == "AUTH_INVALID_REFRESH"
