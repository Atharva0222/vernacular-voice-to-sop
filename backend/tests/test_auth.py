import jwt
import psycopg

from tests.conftest import _pg_dsn


def test_valid_token_resolves_to_the_right_person(client, auth_headers):
    resp = client.get("/api/me", headers=auth_headers(2))
    assert resp.status_code == 200
    assert resp.json() == {"name": "Demo Manager", "role": "manager"}


def test_tampered_token_rejected(client, auth_headers):
    token = auth_headers(2)["Authorization"].removeprefix("Bearer ")
    body, _, sig = token.rpartition(".")
    # Flip a character in the *middle* of the signature, not the last one: base64url has no
    # padding on an (unpadded) JWT signature, but the final character of a byte string whose
    # length isn't a multiple of 3 still carries a few unused low bits - flipping only those
    # can decode to the exact same bytes, so a last-character flip is flaky by construction
    # (hit this for real: ES256 signatures here are 64 bytes, 64 % 3 == 1). A middle character
    # always carries a full 6 bits of real signature data, so this is deterministic.
    mid = len(sig) // 2
    flipped = "0" if sig[mid] != "0" else "1"
    tampered = f"{body}.{sig[:mid]}{flipped}{sig[mid + 1 :]}"
    resp = client.get("/api/me", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 401


def test_expired_token_rejected(client, auth_headers, monkeypatch):
    """A real expired-but-validly-signed token can't be minted in a test (Supabase holds the
    signing key, not us), so this checks the wiring instead: when verification reports
    expiry, current_person() must turn that into a 401 - PyJWT's own expiry check is already
    well-tested upstream and isn't what this test is for."""

    def _raise_expired(*args, **kwargs):
        raise jwt.ExpiredSignatureError("token expired")

    monkeypatch.setattr(jwt, "decode", _raise_expired)
    resp = client.get("/api/me", headers=auth_headers(2))
    assert resp.status_code == 401


def test_missing_token_is_401_not_403(client):
    """auto_error is off on the bearer scheme specifically so this stays a 401."""
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_unknown_profile_rejected(client, auth_headers):
    """A genuine Supabase session with no matching `profiles` row (never provisioned as staff,
    or since removed) must not resolve to anyone. Deletes through a separate autocommitted
    connection, not the `conn` fixture - that one only commits at test teardown, which would be
    too late for this request to see it."""
    headers = auth_headers(2)
    with psycopg.connect(_pg_dsn(), autocommit=True) as admin:
        admin.execute("DELETE FROM profiles WHERE employee_id = 2")
    resp = client.get("/api/me", headers=headers)
    assert resp.status_code == 401
