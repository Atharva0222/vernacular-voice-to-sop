def test_login_succeeds_with_correct_pin(client):
    resp = client.post("/api/login", json={"person_id": 1, "pin": "1111"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Demo Supervisor"
    assert body["role"] == "supervisor"
    assert body["token"]


def test_login_rejects_wrong_pin(client):
    resp = client.post("/api/login", json={"person_id": 1, "pin": "0000"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "wrong id or PIN"


def test_login_rejects_unknown_person_with_same_message(client):
    """Same message as a wrong PIN, so valid ids can't be discovered by guessing."""
    resp = client.post("/api/login", json={"person_id": 999, "pin": "0000"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "wrong id or PIN"


def test_login_is_rate_limited_against_brute_force(client):
    """The route is capped at 10/minute per client; the 11th attempt in a burst is rejected."""
    statuses = [client.post("/api/login", json={"person_id": 1, "pin": "wrong"}).status_code for _ in range(11)]
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
