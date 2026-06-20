from fastapi.testclient import TestClient

from app.main import app, inject_app_config


def test_inject_app_config():
    out = inject_app_config("<html><head></head><body></body></html>", "/api", "sekret")
    assert "window.__APP_CONFIG__" in out
    assert '"apiSecret": "sekret"' in out
    assert '"apiBase": "/api"' in out
    assert out.count("</head>") == 1  # injected before the single </head>


def test_spa_served_with_injected_config():
    with TestClient(app) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "SPA-MARKER" in r.text                 # the built index.html body
        assert "window.__APP_CONFIG__" in r.text      # runtime config injected
        assert "test-secret" in r.text                # API_SHARED_SECRET from env

        # the JSON API still works alongside the SPA
        assert client.get("/api/health").json() == {"status": "ok"}
