# Tests

HTTP-layer tests for the PRAXIS backend. They live here at the **repo root**, not
under `backend/`, because they drive the app from the outside through
`TestClient`.

## Running them

From the repo root:

```bash
make test-install    # one time — installs pytest into backend/.venv
make test            # whole suite
make test-bugs       # only the bug reproductions
make test-cov        # coverage for goals / roadmap / notifications
```

Or directly, if you prefer:

```bash
backend/.venv/bin/pytest
backend/.venv/bin/pytest tests/api/test_goals_routes.py -v
backend/.venv/bin/pytest -k "trailing_slash" -v
```

`pytest.ini` at the repo root sets `testpaths = tests`, so a bare `pytest` finds
this directory with no arguments.

## Layout

```
tests/
├── conftest.py                          # env bootstrap, fixtures, module stubs
├── helpers.py                           # FakeUser + row builders
├── api/
│   ├── test_goals_routes.py             # goals/route.py        — 6 endpoints, 51 tests
│   ├── test_roadmap_routes.py           # roadmap/route.py      — 6 endpoints, 37 tests
│   ├── test_notifications_routes.py     # notifications REST    — 4 endpoints, 36 tests
│   └── test_notifications_ws.py         # /ws/notifications     — 17 tests
├── schemas/
│   └── test_module_schemas.py           # Pydantic contracts    — 46 tests
└── flows/
    └── test_roadmap_to_goals_flow.py    # cross-module journeys — 10 tests
```

197 tests. `goals/route.py`, `roadmap/route.py`, and `notifications/route.py` are
each at 100% statement coverage.

## Markers

| Marker | Meaning |
|---|---|
| `api` | Drives a router through `TestClient` |
| `ws` | WebSocket test |
| `flow` | Spans several endpoints |
| `bug` | Reproduces an entry in [`../BUG_REPORT.md`](../BUG_REPORT.md) |

### Why `bug` tests are `xfail`

A run reports something like:

```
175 passed, 22 xfailed in 3.1s
```

Those 22 are the confirmed bugs. Each test asserts the behaviour the endpoint
**should** have, and carries `@pytest.mark.xfail(strict=True)` because it does
not have it yet:

```python
@pytest.mark.bug
@pytest.mark.xfail(strict=True, reason="GOALS-01: exclude_none strips explicit nulls")
def test_target_date_can_be_cleared(self, client, db, user):
    r = client.patch(f"/api/goals/{goal.id}", json={"target_date": None})

    assert r.json()["target_date"] is None      # what it SHOULD do
```

This buys three things:

- the assertion reads as a **spec**, not as an endorsement of the current
  behaviour
- the bug count is **visible in the output** instead of hidden inside a green
  "197 passed"
- `strict=True` means fixing the bug turns the test into an `XPASS`, which fails
  the build — so nobody fixes a bug and leaves a stale test behind

**When you fix a bug:** the run fails with `[XPASS(strict)]`. Delete the `xfail`
marker (keep `@pytest.mark.bug` or drop it, your call) and mark the entry
resolved in [`../BUG_REPORT.md`](../BUG_REPORT.md).

Every `bug` test names its id (`GOALS-01`, …) in both its docstring and the
`reason=` string.

## Fixtures

| Fixture | Gives you |
|---|---|
| `client` | `TestClient` authenticated as `user` |
| `anon_client` | No auth override — for asserting 401/403 |
| `as_user(u)` | Switches which identity `client` authenticates as |
| `db` | SQLAlchemy session on the same engine the app uses |
| `user` / `other_user` | Two seeded users, for ownership scoping |

There is deliberately **no** second `other_client` fixture. Dependency overrides
live on the single shared `app` object, so two clients cannot hold different
identities at once — whichever fixture resolved last would silently win, and the
first client would quietly act as the wrong user. Use `as_user()` instead.

## Two things about the harness worth knowing

**Heavy imports are stubbed.** `conftest.py` puts fake `easyocr`, `fitz`, `docx`,
`supabase`, and `arq` modules into `sys.modules` before the app is imported.
`easyocr` alone pulls in torch and costs ~10s. With the stubs the suite runs in
well under a second. If you write a test that genuinely needs one of these, patch
it in the test rather than removing the stub.

**Only six tables are created**, listed in `SCHEMA_TABLES` — not
`Base.metadata.create_all()`. The `resumes` and `jobs` models use pgvector
`Vector` columns, which have no SQLite compiler and blow up at `create_all`. Add
a table name to `SCHEMA_TABLES` if a new test needs one, as long as it has no
vector column.

## Adding a file

1. Drop it in `tests/api/` (or `tests/flows/`, `tests/schemas/`).
2. Set `pytestmark = pytest.mark.api` at module level.
3. Group by endpoint in classes — `TestCreateGoal`, `TestListGoals`, …
4. Per endpoint cover: happy path, `anon_client` rejection, 422 on a bad payload,
   404 on unknown *and* on another user's row, and the exact status code
   (201/204 are easy to get wrong).
5. Put bug reproductions in a `TestKnownBugs` class, marked `@pytest.mark.bug`.
