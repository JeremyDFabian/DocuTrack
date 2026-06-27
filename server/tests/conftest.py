# server/tests/conftest.py
"""Shared pytest fixtures.

Tests run against an isolated, throwaway SQLite database and ephemeral keys so
they never touch a developer's real data. Configuration is set here (at import
time) BEFORE `server.app` is imported, because the app builds its engine and
reads config at import. The setup is guarded so it runs once even if pytest
imports this module under more than one name.
"""
import os
import tempfile

if not os.environ.get("DOCUTRACK_TEST_ENV"):
    os.environ["DOCUTRACK_TEST_ENV"] = "1"
    _TEST_DIR = tempfile.mkdtemp(prefix="docutrack_test_")
    os.environ["DATABASE_PATH"] = os.path.join(_TEST_DIR, "test.db")
    os.environ["SECRET"] = "test-secret-not-for-production"
    os.environ["MASTER_KEY"] = "test-master-key-not-for-production"
    os.environ.setdefault("ALLOWED_ORIGINS", "http://testserver")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    # Imported lazily so the env above is applied first.
    from server.app import app
    with TestClient(app) as c:  # `with` triggers startup seeding of demo users
        yield c


@pytest.fixture(autouse=True)
def _reset_login_throttle():
    """Keep the in-memory login throttle from bleeding across tests."""
    from server import app as appmod
    appmod._login_attempts.clear()
    yield
    appmod._login_attempts.clear()
