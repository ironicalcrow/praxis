"""
Test bootstrap for the PRAXIS backend.

Everything in this module runs *before* any `app.*` import, because importing the
application has side effects at module scope:

  * `app.core.config`   -> instantiates `Settings()`, which requires ~20 env vars
  * `app.core.session`  -> calls `create_engine(settings.DATABASE_URL)`
  * `app.core.supabase` -> calls `create_client(...)` twice
  * `app.modules.CV.cv` -> `import easyocr` (pulls in torch, ~10s)

So the order below is load-bearing: env first, module stubs second, app import last.
"""

import os
import sys
import tempfile
import types
from pathlib import Path

import pytest

# ── Paths ──────────────────────────────────────────────────────────────────────
# `backend/` so `import main` / `import app.*` resolve; this directory so
# `import helpers` resolves without needing an __init__.py.
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
BACKEND_ROOT = REPO_ROOT / "backend"

for p in (str(BACKEND_ROOT), str(TESTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


# ── Environment ────────────────────────────────────────────────────────────────
# os.environ wins over the .env file that pydantic-settings would otherwise read,
# so no real credential is ever loaded during a test run.
_TMP_DB = Path(tempfile.mkdtemp(prefix="praxis-tests-")) / "test.db"

FAKE_ENV = {
    "LLM_API_KEY": "test-llm-key",
    "LLM_BASE_URL": "https://llm.invalid/v1",
    "LLM_MODEL": "test-model",
    "CHATBOT_API_KEY": "test-chatbot-key",
    "CHATBOT_BASE_URL": "https://chatbot.invalid/v1",
    "CHATBOT_LLM_MODEL": "test-chat-model",
    "EMBEDDING_API_KEY": "test-embed-key",
    "EMBEDDING_BASE_URL": "https://embed.invalid/v1",
    "EMBEDDING_MODEL": "test-embed-model",
    "EMBEDDING_DIMENSIONS": "8",
    "JSEARCH_API_KEYS": "key-a,key-b",
    "JSEARCH_API_HOST": "jsearch.invalid",
    "JSEARCH_URL": "https://jsearch.invalid/search",
    "JSEARCH_DETAIL_URL": "https://jsearch.invalid/job-details",
    "SUPABASE_URL": "https://test.supabase.invalid",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
    "SUPABASE_STORAGE_BUCKET": "test-cvs",
    # check_same_thread=false: TestClient drives the app from a worker thread.
    "DATABASE_URL": f"sqlite:///{_TMP_DB}?check_same_thread=false",
    "REDIS_URL": "redis://127.0.0.1:1",
}
os.environ.update(FAKE_ENV)

# Optional fallback creds must be absent, or provider-fallback code paths engage.
for _k in list(os.environ):
    if "FALLBACK" in _k:
        os.environ.pop(_k)


# ── Module stubs ───────────────────────────────────────────────────────────────
def _stub(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


class _StubOCRReader:
    def __init__(self, *a, **kw): ...
    def readtext(self, *a, **kw):
        return []


_stub("easyocr", Reader=_StubOCRReader)
_stub("fitz", open=lambda *a, **kw: [])
_stub("docx", Document=lambda *a, **kw: types.SimpleNamespace(paragraphs=[]))


class _StubSupabaseAuth:
    """Individual tests patch `get_user` when they need an authenticated identity."""

    def get_user(self, token):
        raise NotImplementedError("patch supabase.auth.get_user in your test")

    def sign_up(self, *a, **kw):
        raise NotImplementedError("patch supabase.auth.sign_up in your test")

    def sign_in_with_password(self, *a, **kw):
        raise NotImplementedError("patch supabase.auth.sign_in_with_password")

    def sign_out(self, *a, **kw):
        return None


class _StubSupabaseClient:
    def __init__(self, *a, **kw):
        self.auth = _StubSupabaseAuth()
        self.storage = types.SimpleNamespace()


_stub(
    "supabase",
    create_client=lambda *a, **kw: _StubSupabaseClient(),
    Client=_StubSupabaseClient,
)

_arq = _stub("arq", cron=lambda *a, **kw: None)
_stub("arq.connections", RedisSettings=type("RedisSettings", (), {}), ArqRedis=object)
_arq.connections = sys.modules["arq.connections"]


# ── Application import (must come after everything above) ──────────────────────
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401  registers every model on Base.metadata
from app.core.session import Base, SessionLocal, engine, get_db  # noqa: E402
from app.modules.auth.dependency import get_current_user  # noqa: E402
from main import app as fastapi_app  # noqa: E402

from helpers import FakeUser  # noqa: E402

# Tables this suite touches. Created explicitly rather than via
# `Base.metadata.create_all()` because unrelated models (resumes, jobs) carry
# pgvector `Vector` columns that SQLite cannot compile.
SCHEMA_TABLES = [
    "users",
    "roadmaps",
    "roadmap_phases",
    "roadmap_milestones",
    "goals",
    "notifications",
]


@pytest.fixture(scope="session", autouse=True)
def _schema():
    tables = [Base.metadata.tables[name] for name in SCHEMA_TABLES]
    Base.metadata.create_all(bind=engine, tables=tables)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables(_schema):
    """Truncate after each test so ordering never leaks state."""
    yield
    with engine.begin() as conn:
        for name in reversed(SCHEMA_TABLES):
            conn.exec_driver_sql(f"DELETE FROM {name}")


@pytest.fixture(autouse=True)
def _no_real_redis(monkeypatch):
    """
    `create_and_publish` fires from BackgroundTasks on several routes. Its Redis
    publish is best-effort and already wrapped in try/except, but letting it
    attempt a real connection costs a timeout per test.
    """
    class _FakePubSub:
        async def subscribe(self, *a, **kw):
            return None

        async def unsubscribe(self, *a, **kw):
            return None

        async def aclose(self):
            return None

        async def listen(self):
            """
            Yields nothing and returns. The WS manager's listener task then falls
            straight through to its `finally` instead of blocking forever, which
            keeps test teardown deterministic.
            """
            return
            yield  # pragma: no cover - makes this an async generator

    class _FakeAsyncRedis:
        async def publish(self, *a, **kw):
            return 0

        async def aclose(self):
            return None

        async def delete(self, *a, **kw):
            return 0

        def pubsub(self):
            return _FakePubSub()

        async def scan_iter(self, *a, **kw):  # pragma: no cover - generator shim
            return
            yield

    import redis.asyncio as aioredis

    monkeypatch.setattr(aioredis, "from_url", lambda *a, **kw: _FakeAsyncRedis())
    return _FakeAsyncRedis()


@pytest.fixture
def db():
    """A session bound to the same engine the app uses."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user(db):
    from app.modules.auth.models import User

    u = User(
        id="11111111-1111-4111-8111-111111111111",
        name="Test User",
        username="testuser",
        email="test@example.com",
    )
    db.add(u)
    db.commit()
    return FakeUser(id=u.id, email=u.email)


@pytest.fixture
def other_user(db):
    """A second identity, for asserting ownership scoping."""
    from app.modules.auth.models import User

    u = User(
        id="22222222-2222-4222-8222-222222222222",
        name="Other User",
        username="otheruser",
        email="other@example.com",
    )
    db.add(u)
    db.commit()
    return FakeUser(id=u.id, email=u.email)


def _make_client(current_user=None) -> TestClient:
    """
    NOTE: deliberately not used as a context manager. Entering the context runs
    the app's startup event, which calls `Base.metadata.create_all()` over every
    model — including the pgvector ones SQLite cannot create.
    """
    fastapi_app.dependency_overrides[get_db] = lambda: SessionLocal()
    if current_user is not None:
        fastapi_app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(fastapi_app)


@pytest.fixture
def client(user):
    """Authenticated client for `user`."""
    c = _make_client(current_user=user)
    yield c
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def as_user(client):
    """
    Switch the identity `client` authenticates as, mid-test.

    There is deliberately no second `other_client` fixture: dependency overrides
    live on the single shared `fastapi_app`, so two clients cannot hold different
    identities at once — the last fixture to resolve would silently win.
    """
    def _switch(u):
        fastapi_app.dependency_overrides[get_current_user] = lambda: u
        return client

    return _switch


@pytest.fixture
def anon_client():
    """No auth override — exercises the real HTTPBearer / get_current_user path."""
    c = _make_client(current_user=None)
    yield c
    fastapi_app.dependency_overrides.clear()
