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

_dbfile = pathlib.Path(tempfile.gettempdir()) / "tutor_test.db"
if _dbfile.exists():
    _dbfile.unlink()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_dbfile}")

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
