import io


def _login(client, username: str, password: str = "Password123!") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password, "device_id": f"{username}-device"},
    )
    assert response.status_code == 200
    return response.get_json()["data"]["access_token"]


def _auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def test_create_and_list_palettes(client, create_user):
    create_user("diana")
    access_token = _login(client, "diana")

    create_response = client.post(
        "/api/v1/palettes",
        json={"name": "Sunset", "colors": ["#AA2200", "#CC4400", "#EE6600"]},
        headers=_auth_headers(access_token),
    )
    assert create_response.status_code == 201
    assert create_response.get_json()["data"]["name"] == "Sunset"

    list_response = client.get("/api/v1/palettes?limit=10", headers=_auth_headers(access_token))
    assert list_response.status_code == 200
    data = list_response.get_json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == "Sunset"


def test_palette_name_conflict(client, create_user):
    create_user("diana")
    access_token = _login(client, "diana")

    payload = {"name": "Brand", "colors": ["#112233", "#445566", "#778899"]}
    first = client.post("/api/v1/palettes", json=payload, headers=_auth_headers(access_token))
    assert first.status_code == 201

    second = client.post("/api/v1/palettes", json=payload, headers=_auth_headers(access_token))
    assert second.status_code == 409
    assert second.get_json()["error"]["code"] == "PALETTE_NAME_CONFLICT"


def test_palette_access_ownership(client, create_user):
    create_user("diana")
    create_user("kate")

    diana_token = _login(client, "diana")
    kate_token = _login(client, "kate")

    created = client.post(
        "/api/v1/palettes",
        json={"name": "Private", "colors": ["#123456", "#654321", "#ABCDEF"]},
        headers=_auth_headers(diana_token),
    )
    palette_id = created.get_json()["data"]["id"]

    forbidden = client.delete(f"/api/v1/palettes/{palette_id}", headers=_auth_headers(kate_token))
    assert forbidden.status_code == 403
    assert forbidden.get_json()["error"]["code"] == "FORBIDDEN"


def test_upload_validation_rejects_non_image(client):
    response = client.post(
        "/api/v1/upload",
        data={"image": (io.BytesIO(b"not-an-image"), "bad.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_export_json_success(client):
    response = client.post(
        "/api/v1/export?format=json",
        json={"colors": ["#112233", "#445566", "#778899"]},
    )
    assert response.status_code == 200
    assert response.headers.get("Content-Disposition", "").startswith("attachment;")
