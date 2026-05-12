"""
Shared pytest fixtures for Peregrine backend tests.

Run from project root:
    pip install -r tests/requirements.txt
    pytest tests/ -v
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Make backend/api importable without a package install
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "api"))


@pytest.fixture(scope="session")
def client():
    """Synchronous test client — auth disabled (no PEREGRINE_API_KEY set)."""
    from main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="session")
def authed_client(monkeypatch_session):
    """Test client with API key auth enabled."""
    import os
    import importlib
    os.environ["PEREGRINE_API_KEY"] = "test-secret"
    import auth
    importlib.reload(auth)
    from main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    del os.environ["PEREGRINE_API_KEY"]
    importlib.reload(auth)


@pytest.fixture(scope="session")
def monkeypatch_session():
    """Session-scoped monkeypatch (needed for authed_client)."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()
