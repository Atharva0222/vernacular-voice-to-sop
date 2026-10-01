import time

from app import auth


def test_hash_pin_roundtrip():
    stored = auth.hash_pin("1234")
    assert auth.verify_pin("1234", stored)


def test_hash_pin_uses_fresh_salt_each_time():
    assert auth.hash_pin("1234") != auth.hash_pin("1234")


def test_verify_pin_rejects_wrong_pin():
    stored = auth.hash_pin("1234")
    assert not auth.verify_pin("9999", stored)


def test_verify_pin_rejects_missing_hash():
    assert not auth.verify_pin("1234", None)
    assert not auth.verify_pin("1234", "")


def test_issue_token_roundtrips_through_current_person(client):
    token = auth.issue_token(1)
    resp = client.get("/api/sops", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_tampered_token_rejected(client):
    token = auth.issue_token(1)
    body, _, sig = token.rpartition(".")
    tampered = f"{body}.{sig[:-1]}{'0' if sig[-1] != '0' else '1'}"
    resp = client.get("/api/sops", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 401


def test_expired_token_rejected(client):
    body = f"1.{int(time.time()) - 10}"
    expired = f"{body}.{auth._sign(body)}"
    resp = client.get("/api/sops", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


def test_missing_token_is_401_not_403(client):
    """auto_error is off on the bearer scheme specifically so this stays a 401."""
    resp = client.get("/api/sops")
    assert resp.status_code == 401
