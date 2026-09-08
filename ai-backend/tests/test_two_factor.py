import pyotp


def _register_and_login(client, email="twofa@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_setup_returns_secret_and_qr_code(client):
    token = _register_and_login(client)
    response = client.post("/auth/2fa/setup", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()["secret"]) > 0
    assert len(response.json()["qr_code_base64"]) > 0


def test_enable_with_correct_code_succeeds(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    setup = client.post("/auth/2fa/setup", headers=headers)
    secret = setup.json()["secret"]
    response = client.post("/auth/2fa/enable", json={"totp_code": pyotp.TOTP(secret).now()}, headers=headers)
    assert response.status_code == 200


def test_enable_with_wrong_code_fails(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/auth/2fa/setup", headers=headers)
    response = client.post("/auth/2fa/enable", json={"totp_code": "000000"}, headers=headers)
    assert response.status_code == 401


def test_login_with_2fa_enabled_requires_code(client):
    token = _register_and_login(client, "needs2fa@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    setup = client.post("/auth/2fa/setup", headers=headers)
    secret = setup.json()["secret"]
    client.post("/auth/2fa/enable", json={"totp_code": pyotp.TOTP(secret).now()}, headers=headers)
    no_code = client.post("/auth/login", json={"email": "needs2fa@example.com", "password": "StrongPass123"})
    assert no_code.status_code == 428
    good = client.post("/auth/login", json={"email": "needs2fa@example.com", "password": "StrongPass123", "totp_code": pyotp.TOTP(secret).now()})
    assert good.status_code == 200
    bad = client.post("/auth/login", json={"email": "needs2fa@example.com", "password": "StrongPass123", "totp_code": "000000"})
    assert bad.status_code == 401


def test_disable_two_factor(client):
    token = _register_and_login(client, "disable2fa@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    setup = client.post("/auth/2fa/setup", headers=headers)
    secret = setup.json()["secret"]
    client.post("/auth/2fa/enable", json={"totp_code": pyotp.TOTP(secret).now()}, headers=headers)
    relogin = client.post("/auth/login", json={"email": "disable2fa@example.com", "password": "StrongPass123", "totp_code": pyotp.TOTP(secret).now()})
    assert relogin.status_code == 200
    fresh_token = client.cookies.get("access_token")
    response = client.post("/auth/2fa/disable", json={"totp_code": pyotp.TOTP(secret).now()}, headers={"Authorization": f"Bearer {fresh_token}"})
    assert response.status_code == 200
    assert client.post("/auth/login", json={"email": "disable2fa@example.com", "password": "StrongPass123"}).status_code == 200


def test_2fa_endpoints_require_authentication(client):
    assert client.post("/auth/2fa/setup", json={}).status_code == 401
