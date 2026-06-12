"""Health endpoint tests. DB connectivity is monkeypatched so these run without Postgres."""

from fastapi.testclient import TestClient

import app.main as main
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_health_ok(monkeypatch):
    monkeypatch.setattr(main, "ping", lambda: True)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db"] == "up"
    assert "version" in body


def test_health_degraded_when_db_down(monkeypatch):
    def boom():
        raise RuntimeError("no db")

    monkeypatch.setattr(main, "ping", boom)
    resp = client.get("/health")
    assert resp.status_code == 503
    assert resp.json()["db"] == "down"


def test_unknown_agent_404():
    assert client.post("/jobs/not_a_real_agent").status_code == 404


def test_known_agent_501():
    assert client.post("/jobs/script_writer").status_code == 501
