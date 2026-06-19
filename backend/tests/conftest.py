"""Test config.

Set env BEFORE any `app` import so the settings singleton + engine bind to a
throwaway SQLite file and a known shared secret, and so the background scheduler
never starts during tests. No Anthropic key / network is ever needed —
generation is monkeypatched in the tests that touch it.
"""
import os
import pathlib
import tempfile

os.environ.setdefault("API_SHARED_SECRET", "test-secret")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("AUTO_SEED_STUDENT", "false")  # keep tests deterministic

_dbfile = pathlib.Path(tempfile.gettempdir()) / "tutor_test.db"
if _dbfile.exists():
    _dbfile.unlink()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_dbfile}")

# A minimal built SPA so static-serving can be exercised in tests.
_static = pathlib.Path(tempfile.gettempdir()) / "tutor_test_static"
(_static / "assets").mkdir(parents=True, exist_ok=True)
(_static / "index.html").write_text(
    "<!doctype html><html><head><title>t</title></head><body>SPA-MARKER</body></html>"
)
os.environ.setdefault("STATIC_DIR", str(_static))

import pytest  # noqa: E402


@pytest.fixture
def db_session():
    """A clean DB + session per test (tables dropped/recreated for isolation)."""
    from app.db import SessionLocal, engine
    from app.models import Base

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
