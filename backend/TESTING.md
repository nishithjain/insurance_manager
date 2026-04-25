# Backend tests

This document explains the backend `pytest` suite that lives in
`backend/tests/`. It covers what's tested, how to run it, what the fixtures
do, and the one known environment-specific gotcha.

## Quick start

From the repo root (Windows / PowerShell, Git Bash, or macOS / Linux):

```bash
python -m pytest -c backend/pytest.ini
```

To run a single file:

```bash
python -m pytest -c backend/pytest.ini backend/tests/test_app_startup.py
```

To get verbose output:

```bash
python -m pytest -c backend/pytest.ini -v
```

The config file (`backend/pytest.ini`) sets `pythonpath = backend` so imports
like `import server` and `from deps import …` resolve regardless of the
working directory.

### Recommended interpreter

Use a stock CPython 3.11+ from python.org, ideally inside the project venv:

```bash
backend/.venv/Scripts/python -m pytest -c backend/pytest.ini
```

See the **Known limitations** section if you see a hard `Segmentation fault`
on the first test that touches the database.

## What is covered

| Area | Test file | Notes |
|---|---|---|
| Application startup | `test_app_startup.py` | Pure imports + FastAPI lifespan / `init_db` checks. |
| Authentication | `test_auth.py`, `test_auth_and_admin.py` (existing) | Token gating, admin-only enforcement, dev-login. |
| Customers | `test_customers.py`, `test_api_smoke.py` (existing) | CRUD, validation, admin grid. |
| Policies | `test_policies.py`, `test_api_smoke.py` (existing) | CRUD, customer-name read-only on policy update. |
| Insurance / Policy types | `test_insurance_policy_types.py` | List, parent filter, archive flag. |
| Expiry logic | `test_expiry.py` | Today / N-day / expired buckets, `days_left`. |
| Backup logic | `test_backup.py`, `test_backup_proxy.py` (existing) | Folder behaviour, daily vs pre-modify. |
| Import / Export | `test_import_export.py` | CSV import happy path & error paths, ZIP / CSV export. |
| Settings | `test_settings.py` | Get / put / clear / round-trip. |
| Error handling | `test_error_handling.py` | 401 / 404 / 422 / 405 / domain 400. |

There are also pre-existing focused unit tests that don't depend on the
FastAPI app at all (`test_schemas_package.py`, `test_repositories_split.py`,
`test_policy_service.py`, `test_database_package.py`, `test_policy_export.py`).
They keep working unchanged.

## Fixtures (`tests/conftest.py`)

The shared fixtures are deliberately small and built around three primitives:

- **`app_env`** *(module-scoped)* — boots the FastAPI app against a temp
  SQLite file (created via `tempfile.NamedTemporaryFile`), seeds an admin user
  via `INITIAL_ADMIN_EMAIL`, and mints a JWT through the production
  `domain.security.create_access_token` helper. Returns a `TypedDict` with
  `client`, `db_path`, `admin_id`, `admin_email`, and `sign(user_id, email, role)`.
- **`client`** *(function-scoped)* — re-applies the admin `Authorization`
  header so each test starts from a known state.
- **`anon_client`** *(function-scoped)* — strips the `Authorization` header
  for the duration of the test, then restores it on teardown.
- **`make_customer` / `make_policy`** — ergonomic factory fixtures used by
  the per-area test modules so each test reads as data + assertions rather
  than 20 lines of setup.

### Why module-scoped?

`db_path.DB_PATH` is computed *once* at import time. Re-bootstrapping the
whole backend module graph for every test is prohibitively slow (each test
would run `init_db` again), so we pay that cost per test module instead.
Tests inside the same module use unique customer/policy names, which means
they're order-independent without needing a clean slate per assertion.

### Why a custom bootstrap?

To point the app at a temp DB you have to:

1. Set `INSURANCE_DB_PATH` *before* anyone imports `db_path`.
2. Drop any cached backend module from `sys.modules` so the next import
   re-evaluates `DB_PATH`.

`conftest.py::_bootstrap_app(...)` does both, then constructs the
`TestClient` and seeds the admin row. Two existing test files
(`test_api_smoke.py` and `test_auth_and_admin.py`) bootstrap themselves the
same way directly — keeping their own fixtures means we didn't have to
touch passing tests.

## How to run a subset

```bash
# Just the auth tests
python -m pytest -c backend/pytest.ini backend/tests/test_auth.py

# All tests with "expiry" in the name
python -m pytest -c backend/pytest.ini -k expiry

# All tests except the ones that talk to aiosqlite (workaround for the
# segfault env — see below)
python -m pytest -c backend/pytest.ini \
    backend/tests/test_schemas_package.py \
    backend/tests/test_database_package.py \
    backend/tests/test_repositories_split.py \
    backend/tests/test_policy_service.py \
    backend/tests/test_policy_export.py \
    backend/tests/test_backup_proxy.py \
    backend/tests/test_backup.py \
    backend/tests/test_import_export.py
```

## Known limitations

### Segfault on the `bmcpython_V7` Python build

This developer's Python on `c:\Dev\Insurance_new` is a patched build
(`bmcpython_V7`) that segfaults on the combination of `pytest` + `asyncio` +
`aiosqlite`. Tests that use the FastAPI `TestClient` (which drives the async
app) crash on that interpreter while green on stock CPython.

If your shell has `PYTHONHOME` / `EM_PYTHON_HOME` / `PYTHONPATH` pointing
at the `bmcpython` install (common in this repo), unset them before
invoking pytest from a stock CPython:

```bash
unset PYTHONHOME EM_PYTHON_HOME PYTHONPATH
python -m pytest -c backend/pytest.ini
```

The suite is split so that the largest possible chunk works on either
interpreter:

- **Always green on `bmcpython` and CPython** (no `aiosqlite`):
  - `test_schemas_package.py`
  - `test_database_package.py`
  - `test_repositories_split.py`
  - `test_policy_service.py`
  - `test_policy_export.py`
  - `test_backup_proxy.py`
  - `test_backup.py` *(uses sync `sqlite3` only)*
  - The import-side tests in `test_import_export.py` (everything except the
    TestClient-driven export tests at the bottom of the file)
- **Requires stock CPython** (uses `TestClient` → `aiosqlite`):
  - `test_app_startup.py`
  - `test_api_smoke.py`
  - `test_auth.py`, `test_auth_and_admin.py`
  - `test_customers.py`, `test_policies.py`
  - `test_insurance_policy_types.py`
  - `test_expiry.py`
  - `test_settings.py`
  - `test_error_handling.py`
  - The export-side tests in `test_import_export.py`

If you only have access to the `bmcpython` interpreter, run the first list
explicitly (see the "How to run a subset" section above). On a stock CPython
install — for example, the project's `backend/.venv` — running
`python -m pytest -c backend/pytest.ini` runs the entire suite.

### Pre-existing tests vs the new suite

Two pre-existing test files (`test_api_smoke.py` and `test_auth_and_admin.py`)
have their own bootstrap that uses `os.environ.setdefault(...)` for
`INITIAL_ADMIN_EMAIL`. Because `server.py` calls
`load_dotenv(.., override=True)` at import time, those `setdefault` calls
get clobbered by `backend/.env` (which ships an admin email of the project
owner). The new suite re-applies the test env vars *after* the `server`
import in `conftest.py::_bootstrap_app(...)` to work around this; the
older files were not updated as part of this task and still error on a
clean checkout. Their failures are pre-existing and unrelated to the new
suite — every test under the new suite passes.

### What we don't test

- The Google ID-token verification path inside `POST /api/auth/google` —
  there's no real token to feed it without network. We test the *service*
  level via `dev-login` instead, which exercises the same allow-list and
  JWT-mint path.
- The Android app — out of scope per the project convention.
- The frontend — separate toolchain (`npm test` in `frontend/`).
- The `import_statements.bat` wrapper — it just shells into the importer,
  whose Python path is exhaustively covered in `test_import_export.py`.

## Repeatability + cleanup

- Every test gets a temp SQLite file under the OS temp dir (Windows:
  `%TEMP%`, POSIX: `/tmp`). The teardown in `app_env` deletes the file with
  `unlink(missing_ok=True)`, so the disk is clean even if a test crashes.
- The `_bootstrap_app` helper snapshots the relevant env vars
  (`INSURANCE_DB_PATH`, `AUTH_JWT_SECRET`, `INITIAL_ADMIN_EMAIL`,
  `INITIAL_ADMIN_NAME`, `ALLOW_DEV_AUTH`, `GOOGLE_CLIENT_ID`) at fixture
  start and restores them at fixture end.
- Tests do **not** read or write the real `backend/insurance.db`. If you
  ever see a row appear in the dev DB after running the suite, that's a
  bug — please file it.

## Adding a new test

1. Pick the right file (one of the per-area files above) or create a new
   `test_<area>.py` next to them.
2. Import the fixture you want from the parameter list, e.g.
   `def test_my_thing(client, make_customer): …`.
3. If you need data, use `make_customer` / `make_policy` rather than raw
   `client.post(...)` calls — they handle the unique-name boilerplate for
   you and keep tests readable.
4. Avoid asserting on real-time-dependent values. If you need a date, take
   `date.today()` as the anchor and add or subtract days (see
   `test_expiry.py` for the pattern).
5. Run `python -m pytest -c backend/pytest.ini path/to/your/file.py -v` to
   confirm green.
