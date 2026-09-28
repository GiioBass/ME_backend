import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.services.auth_service import auth_service

def test_auth_service_hashing_and_tokens():
    password = "SuperSecretPassword123!"
    h1, salt1 = auth_service.hash_password(password)
    assert h1 and salt1
    assert auth_service.verify_password(password, salt1, h1)
    assert not auth_service.verify_password("WrongPassword", salt1, h1)

    # Token creation and validation
    player_id = f"p-{uuid.uuid4().hex[:8]}"
    player_name = "TestHero"
    token = auth_service.create_token(player_id, player_name, expires_in_seconds=60)
    assert token
    payload = auth_service.decode_token(token)
    assert payload is not None
    assert payload["sub"] == player_id
    assert payload["name"] == player_name

    # Expired token test
    expired_token = auth_service.create_token(player_id, player_name, expires_in_seconds=-10)
    assert auth_service.decode_token(expired_token) is None

def test_auth_endpoints():
    uid = uuid.uuid4().hex[:6]
    name = f"Hero_{uid}"
    pwd = "SecurePassword2026!"

    with TestClient(app) as client:
        # 1. Register with password
        res = client.post("/api/v1/auth/register", json={
            "name": name,
            "password": pwd,
            "character_class": "fighter"
        })
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["player"]["name"] == name
        assert data["token"] is not None
        assert data["player"]["stats"]["character_class"] == "fighter"

        # 2. Cannot register same name again
        res_dup = client.post("/api/v1/auth/register", json={
            "name": name,
            "password": pwd
        })
        assert res_dup.status_code == 400

        # 3. Login with wrong password
        res_fail = client.post("/api/v1/auth/login", json={
            "name": name,
            "password": "WrongPassword!"
        })
        assert res_fail.status_code == 400

        # 4. Login with correct password
        res_login = client.post("/api/v1/auth/login", json={
            "name": name,
            "password": pwd
        })
        assert res_login.status_code == 200
        assert res_login.json()["token"] is not None
        assert res_login.json()["player"]["name"] == name
