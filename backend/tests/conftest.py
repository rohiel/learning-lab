"""Test config.

Set env BEFORE any `app` import so the settings singleton + engine bind to a
throwaway SQLite file and a known shared secret. No Anthropic key / network is
ever needed — generation is monkeypatched in the tests that touch it.
"""
import os
import pathlib
import tempfile

os.environ.setdefault("API_SHARED_SECRET", "test-secret")

_dbfile = pathlib.Path(tempfile.gettempdir()) / "tutor_test.db"
if _dbfile.exists():
    _dbfile.unlink()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_dbfile}")
