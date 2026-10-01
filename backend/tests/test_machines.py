from tests.conftest import auth_headers


def test_list_machines_is_open_and_seeded(client):
    resp = client.get("/api/machines")
    assert resp.status_code == 200
    names = {m["name"] for m in resp.json()}
    assert names == {"Press 1", "Lathe 1"}


def test_create_machine_requires_auth(client):
    resp = client.post("/api/machines", json={"line_id": 1, "name": "New Press"})
    assert resp.status_code == 401


def test_supervisor_can_add_machine_to_own_line(client):
    resp = client.post("/api/machines", json={"line_id": 1, "name": "New Press"}, headers=auth_headers(client, 1))
    assert resp.status_code == 201
    assert resp.json()["name"] == "New Press"
    assert resp.json()["line_id"] == 1


def test_supervisor_cannot_add_machine_to_other_line(client):
    """Line 2 belongs to Supervisor B (person 4); person 1 runs Line A only."""
    resp = client.post("/api/machines", json={"line_id": 2, "name": "Sneaky"}, headers=auth_headers(client, 1))
    assert resp.status_code == 403


def test_plant_head_can_add_machine_to_any_line_in_plant(client):
    resp = client.post("/api/machines", json={"line_id": 2, "name": "Lathe 2"}, headers=auth_headers(client, 3))
    assert resp.status_code == 201
