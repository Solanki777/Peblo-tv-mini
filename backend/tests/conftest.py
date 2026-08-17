"""Shared test fixtures.

Tests run against an in-memory SQLite database, not the Postgres the app
uses in dev/prod. That's a deliberate trade-off documented in the
README: nothing in the schema or queries is Postgres-specific (no
JSONB, arrays, or Postgres-only functions), so SQLite is fast and needs
no external service in CI. What it does NOT cover is Postgres-specific
behaviour (e.g. exact error codes on a constraint violation under
concurrent load) - if that ever mattered, these fixtures would swap to
a real Postgres via testcontainers instead.

Tables are created directly from the SQLAlchemy models
(Base.metadata.create_all), not via Alembic - these tests are exercising
application logic, not the migration chain itself.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session, tmp_path, monkeypatch):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Route artwork/catalog storage at a throwaway directory per test so
    # tests never touch (or depend on) the real dev `storage/` folder,
    # and can't leak state between tests.
    monkeypatch.setattr("app.config.STORAGE_ROOT", str(tmp_path / "storage"))

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _register_and_login(client: TestClient, username: str, password: str) -> str:
    client.post("/auth/register", json={"username": username, "password": password})
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def editor_token(client) -> str:
    return _register_and_login(client, "editor1", "editorpass123")


@pytest.fixture()
def admin_token(client, db_session) -> str:
    # No API path creates an admin (by design - see app/api/auth.py).
    # Register normally, then promote directly in the test DB, mirroring
    # what seed/seed.py does for real via a direct DB write.
    from app.models.user import User

    _register_and_login(client, "admin1", "adminpass123")
    user = db_session.query(User).filter(User.username == "admin1").first()
    user.role = "admin"
    db_session.commit()

    resp = client.post(
        "/auth/login", json={"username": "admin1", "password": "adminpass123"}
    )
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_image_bytes(width: int, height: int, fmt: str = "PNG", noisy: bool = False) -> bytes:
    """A real, decodable image at exactly width x height.

    `noisy=True` fills it with random per-pixel data instead of a solid
    colour, so it doesn't compress away to nothing - used for the
    "file exceeds the size ceiling" test case (a solid-colour PNG at
    even a large resolution compresses to a few hundred bytes, so it
    can't exercise that check).
    """
    import os

    if noisy:
        img = Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))
    else:
        img = Image.new("RGB", (width, height), (200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()