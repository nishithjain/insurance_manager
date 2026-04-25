# Insurance Manager

A small, self-hostable insurance-management system for an agent or a small
agency. It lets you manage customers, policies, expiry tracking and
renewal follow-ups, monthly insurer statements, and reports — from a web
UI on the desktop and a read-only companion app on Android.

The backend is a FastAPI service backed by SQLite, the web UI is a React /
Tailwind / Radix app, and the Windows installer wraps both into a single
service so the whole thing runs as a Windows Service after one click.

---

## Table of contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [How to run the backend](#how-to-run-the-backend)
- [How to run the frontend](#how-to-run-the-frontend)
- [How to run the Android app](#how-to-run-the-android-app)
- [Database](#database)
- [Testing](#testing)
- [Build, installer, and Windows service](#build-installer-and-windows-service)
- [API overview](#api-overview)
- [Important business concepts](#important-business-concepts)
- [Roles and permissions](#roles-and-permissions)
- [Troubleshooting](#troubleshooting)
- [Contributing / development notes](#contributing--development-notes)
- [License](#license)

---

## Features

The features below are all implemented in the current codebase; nothing
on this list is aspirational.

- **Customer management** — create, list, search, view, update, delete
  customers; an admin-only grid (`/admin/customers`) with policy counts.
- **Policy management** — full CRUD with a detailed bundle endpoint
  (`/api/policies/{id}/detail`) that returns the policy plus its linked
  customer and resolved insurance/policy type.
- **Expiring policy tracking** — windows for *today*, *next N days* and
  *expired*, with `days_left` calculated server-side. Reminder summary
  buckets feed the dashboard.
- **Renewal contact workflow** — PATCH endpoints for policy contact
  status, payment status (PENDING → CASH/CHEQUE/ONLINE/TRANSFER), and
  renewal resolution.
- **Recent / dashboard statistics** — `/api/statistics/dashboard` and
  `/api/sync/*` for the home screen and the Android snapshot.
- **Monthly statement import** — CSV upload at `/api/import/statement-csv`
  with preview, a per-month summary, and "materialize to policies" flow.
- **CSV / ZIP export** — `/api/export/policies-csv` and the
  `/api/export/full-data-zip` bundle for backups and audits.
- **Two-level Insurance Type / Policy Type taxonomy** — see
  [Important business concepts](#important-business-concepts).
- **Google Sign-In + JWT auth** — `/api/auth/google` verifies a Google ID
  token and returns a backend JWT. Optional `ALLOW_DEV_AUTH=true`
  enables `/api/auth/dev-login` for local web development.
- **Admin user management** — role-gated CRUD under `/api/users` with
  guards that prevent locking the system out (the last active admin can't
  be demoted, deactivated, or deleted).
- **App settings** — `/api/settings` for the backup folder and other
  per-deployment values.
- **Pre-modify and daily SQLite backups** — automatic, configurable folder.
- **Read-only Android companion** — Kotlin / Jetpack Compose app at
  `insurance-android/` for browsing customers, policies, and expiry
  reminders on a phone, including call / WhatsApp shortcuts.
- **Windows service + Inno Setup installer** — one-click install that
  registers `InsuranceBackendService` and serves the bundled frontend
  from `frontend_dist/`.

---

## Tech stack

| Layer | Stack |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn, aiosqlite, Pydantic v2, PyJWT, google-auth, python-dotenv |
| Database | SQLite (single file at `backend/insurance.db`) |
| Web frontend | React 18 (CRA via Craco), Tailwind CSS, Radix UI, react-router v7, axios, Yarn |
| Android app | Kotlin, Jetpack Compose, Hilt + KSP |
| Service / packaging | PyInstaller (`scripts/build_service_exe.bat`), Inno Setup 6 (`installer/InsuranceManagerBackend.iss`) |
| Tests | pytest + FastAPI `TestClient` + temporary SQLite |

The repository ships with a small toolbelt of `.bat` helpers under
`scripts/` for the common Windows workflows.

---

## Project structure

Top-level layout (only the folders that actually exist are shown):

```
Insurance_new/
├── backend/                 # FastAPI service + SQLite + tests
│   ├── server.py            # Composition root (mounts /api routers)
│   ├── routers/             # HTTP layer (auth, customers, policies, …)
│   ├── services/            # Business logic (policy, auth, backup, …)
│   ├── repositories/        # SQL + row → schema mappers
│   ├── domain/              # Constants, security helpers, value objects
│   ├── database/            # Schema, migrations, seeds, connection proxy
│   ├── schemas/             # Pydantic request/response models
│   ├── tests/               # pytest suite (TestClient + temp SQLite)
│   ├── insurance.db         # Default SQLite file (overridable, see below)
│   ├── pytest.ini           # Test config (pythonpath = backend)
│   ├── requirements.txt     # Backend Python deps
│   └── TESTING.md           # Long-form test docs
│
├── frontend/                # React + Tailwind + Radix UI web app
│   ├── src/
│   │   ├── pages/           # Dashboard, CustomerManagement, …
│   │   ├── components/
│   │   ├── auth/            # Google Sign-In + token storage
│   │   └── hooks/, lib/, utils/
│   ├── package.json         # CRA via Craco
│   ├── craco.config.js
│   └── env.txt              # Sample .env shown to operators
│
├── insurance-android/       # Kotlin / Jetpack Compose companion
│   ├── app/                 # Compose UI module
│   ├── build.gradle.kts
│   └── gradle.properties
│
├── scripts/                 # Windows helper scripts
│   ├── recreate_venv.bat
│   ├── run_backend.bat
│   ├── build_frontend.bat
│   ├── build_service_exe.bat
│   ├── build_installer.bat
│   ├── service.bat          # install/status/start/stop/restart/uninstall
│   └── windows_service.py   # PyInstaller entry for the Windows service
│
├── installer/               # Inno Setup script + icon
│   └── InsuranceManagerBackend.iss
│
├── config/                  # Runtime config consumed by the service
│   └── backend_service_config.json
│
├── assets/                  # Images used by the installer / docs
├── README.md                # You are here
└── requirements.txt         # Convenience pointer at backend deps
```

---

## Prerequisites

| Tool | Version | Used for | Notes |
|---|---|---|---|
| Python | 3.11+ (3.13 also supported) | Backend, tests, service build | Use the official python.org build, not a vendor-patched fork. |
| Node.js / Yarn 1 | Node 18+ / Yarn 1.22+ | Frontend dev + production build | `package.json` pins Yarn 1.22. `npm` works too but the lockfile is `yarn.lock`. |
| Android Studio | Hedgehog or newer | Android app | Only required if you want to build / run the companion. |
| Inno Setup 6 | 6.x | Generating the Windows installer | Skip if you don't need the `.exe` installer. |
| Windows admin shell | — | Installing the Windows service | `scripts/service.bat install` requires elevation. |

A current Python on PATH (`py -3` or `python`) is enough — `scripts/recreate_venv.bat` will provision the project venv at `.venv/` and install all backend requirements.

---

## Configuration

Real configuration is loaded from environment variables and small JSON
files. The repo ships **no real secrets** — anything that looks secret in
the examples below is a placeholder.

### Backend (`backend/.env`)

| Variable | Purpose |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 **Web** Client ID (also used by the frontend and Android). |
| `AUTH_JWT_SECRET` | 32+ byte random string used to sign backend JWTs. **Required for production.** |
| `AUTH_JWT_ALGORITHM` | Optional. Defaults to `HS256`. |
| `AUTH_JWT_LIFETIME_MIN` | Optional. Session lifetime in minutes. Defaults to `720` (12 hours). |
| `INITIAL_ADMIN_EMAIL` | Seeds the very first admin on a fresh `app_users` table. |
| `INITIAL_ADMIN_NAME` | Optional display name for the seeded admin. |
| `ALLOW_DEV_AUTH` | When `true`, enables `POST /api/auth/dev-login`. **Set `false` in production.** |
| `INSURANCE_DB_PATH` | Optional. Override the SQLite file location. Defaults to `backend/insurance.db`. |
| `CORS_ORIGINS` | Comma-separated list of allowed web origins. |

> Treat `AUTH_JWT_SECRET` and `GOOGLE_CLIENT_ID` like passwords. Don't
> commit `backend/.env`. Rotate the secret if it leaks.

### Frontend (`frontend/.env`)

A starter is shown in `frontend/env.txt`:

| Variable | Purpose |
|---|---|
| `REACT_APP_BACKEND_URL` | Base URL of the backend API. |
| `REACT_APP_GOOGLE_CLIENT_ID` | Same OAuth 2.0 Web Client ID used by the backend. |
| `WDS_SOCKET_PORT` | Optional. Use `443` when serving CRA dev through a tunnel. |

### Android (`insurance-android/gradle.properties` or `~/.gradle/gradle.properties`)

```properties
GOOGLE_WEB_CLIENT_ID=<same OAuth 2.0 Web Client ID>
```

`local.properties` (auto-generated by Android Studio) holds your SDK
path and is git-ignored.

### Service (`config/backend_service_config.json`)

The Windows service reads this file at startup:

```json
{
  "host": "127.0.0.1",
  "port": 8000,
  "app": "server:app",
  "log_level": "info",
  "frontend_enabled": true,
  "frontend_dist_path": "frontend_dist"
}
```

When `frontend_enabled` is `true` the FastAPI app additionally serves the
built React app from `frontend_dist/`, so a single port serves both.

### First-time auth setup

1. Google Cloud Console → **APIs & Services → Credentials → Create OAuth
   client ID** → Application type **Web application**. Add your web
   origin (e.g. `http://localhost:3000`) to "Authorized JavaScript origins".
2. Copy the Client ID into `GOOGLE_CLIENT_ID`,
   `REACT_APP_GOOGLE_CLIENT_ID`, and `GOOGLE_WEB_CLIENT_ID`.
3. Pick a strong `AUTH_JWT_SECRET`:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
4. Set `INITIAL_ADMIN_EMAIL` to your own Gmail. The first backend boot
   will log `Seeded initial admin app_user '...'`.
5. Sign in with that Gmail in the web UI and use the **User management**
   page to add more users.

#### Detailed Google OAuth setup

This project uses Google Sign-In for both the web app and the Android
read-only app. Google returns an ID token to the client; the backend
verifies that token against the configured OAuth 2.0 Web Client ID and
then issues the app's JWT.

##### Create or select a Google Cloud project

1. Open https://console.cloud.google.com/.
2. Create a new project or select the existing Insurance Manager project.
3. Go to **APIs & Services**.

##### Configure the OAuth consent screen

1. Open **APIs & Services** -> **OAuth consent screen**.
2. Choose **External** unless you are deploying only inside a Google
   Workspace organization.
3. Fill the required app details:
   - App name: `Insurance Manager`
   - User support email
   - Developer contact email
4. Save and continue through the remaining consent-screen steps.

##### Create the Web OAuth client

1. Open **APIs & Services** -> **Credentials**.
2. Click **Create Credentials** -> **OAuth client ID**.
3. Choose application type **Web application**.
4. Add every frontend origin that will load Google Sign-In under
   **Authorized JavaScript origins**. These values must match exactly,
   including protocol and port:

   ```text
   http://localhost:3000
   http://localhost:5173
   http://127.0.0.1:8000
   http://<YOUR-LAN-IP>:8000
   https://your-domain.com
   ```

5. If you later add a server-side OAuth callback flow, add matching
   **Authorized redirect URIs** such as:

   ```text
   http://localhost:8000/auth/google/callback
   http://<YOUR-LAN-IP>:8000/auth/google/callback
   https://your-domain.com/auth/google/callback
   ```

   The current app login uses Google ID tokens through
   `POST /api/auth/google`, so the JavaScript origins are the important
   entries for fixing `origin_mismatch`.

6. Save the Web Client ID. Use this same Web Client ID in the backend,
   frontend, and Android app.

##### Create the Android OAuth client

1. In **Credentials**, click **Create Credentials** -> **OAuth client ID**.
2. Choose application type **Android**.
3. Enter the Android package name, for example:

   ```text
   com.insurancemanager.app
   ```

4. Add the SHA-1 certificate fingerprint. In Android Studio, open
   **Gradle** -> **app** -> **Tasks** -> **android** -> **signingReport**,
   then copy the SHA-1 from the debug or release variant you are using.

The Android OAuth client registers the app with Google, but the Android
code still sends tokens for the Web Client ID. Set
`GOOGLE_WEB_CLIENT_ID` to the Web Client ID, not the Android Client ID.

##### Configure the app

Backend `backend/.env`:

```dotenv
GOOGLE_CLIENT_ID=<web OAuth client ID>
AUTH_JWT_SECRET=<strong random secret>
INITIAL_ADMIN_EMAIL=<your Gmail address>
```

Frontend `frontend/.env`:

```dotenv
REACT_APP_GOOGLE_CLIENT_ID=<same web OAuth client ID>
```

Android `insurance-android/gradle.properties` or
`~/.gradle/gradle.properties`:

```properties
GOOGLE_WEB_CLIENT_ID=<same web OAuth client ID>
```

For local-only development without Google Sign-In, you can enable the
dev login endpoint:

```dotenv
ALLOW_DEV_AUTH=true
```

Set `ALLOW_DEV_AUTH=false` or remove it in production.

##### Finish setup and test

1. Pick a strong `AUTH_JWT_SECRET`:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
2. Set `INITIAL_ADMIN_EMAIL` to your own Gmail. The first backend boot
   will log `Seeded initial admin app_user '...'`.
3. Restart the backend after editing `backend/.env`.
4. Restart the frontend after editing `frontend/.env`.
5. Rebuild the Android app after editing `gradle.properties`.
6. Sign in with that Gmail in the web UI and use the **User management**
   page to add more users.

##### Common Google Sign-In issues

| Error | Fix |
|---|---|
| `Error 400: origin_mismatch` | Add the exact web origin shown in the browser address bar to the Web Client's **Authorized JavaScript origins**. Include the port. |
| `Authentication is not configured` | Set `GOOGLE_CLIENT_ID` in `backend/.env`, set `AUTH_JWT_SECRET`, then restart the backend. |
| Google button says Sign-In is not configured | Set `REACT_APP_GOOGLE_CLIENT_ID` in `frontend/.env`, then restart the frontend. |
| Android login fails with invalid client ID | Set `GOOGLE_WEB_CLIENT_ID` to the Web Client ID, not the Android Client ID, then rebuild. |
| SHA-1 mismatch on Android | Add the SHA-1 for the debug or release certificate actually used to build the app. |

---

## How to run the backend

The repo expects a venv at the **repo root** (`./.venv/`).

```bash
# One-time setup (creates .venv\ at the repo root and installs backend deps)
scripts\recreate_venv.bat

# Start the API on http://127.0.0.1:8000 (auto-reload)
scripts\run_backend.bat
```

Equivalent manual commands if you don't want to use the helpers:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt

cd backend
python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

The API root is `http://127.0.0.1:8000/api/` and a health probe lives at
`http://127.0.0.1:8000/api/health`.

---

## How to run the frontend

```bash
cd frontend
yarn install        # or: npm install
yarn start          # http://localhost:3000  (CRA dev server via craco)
```

Production build (writes static files into `frontend/build/`, which the
installer copies to `frontend_dist/`):

```bash
cd frontend
yarn build
```

---

## How to run the Android app

The Android module is optional. To run it:

1. Open `insurance-android/` in Android Studio (Hedgehog or newer).
2. Let Gradle sync and download dependencies.
3. Set `GOOGLE_WEB_CLIENT_ID` in `insurance-android/gradle.properties`
   (or `~/.gradle/gradle.properties`).
4. Confirm the backend URL the app will hit. By default the app talks to
   the same backend you've configured for the web UI; check the
   `app/src/main/java/com/...` configuration if you need to point it
   somewhere else.
5. Pick the `app` run configuration → run on an emulator or a connected
   device.

The Android app is a **read-only companion** — you can browse customers,
policies and expiring lists, and tap to call / WhatsApp a customer, but
all writes happen through the web UI.

---

## Database

- The default SQLite file is `backend/insurance.db`. Override the
  location with `INSURANCE_DB_PATH=...`.
- Schema, migrations, and seed data are applied **automatically on
  startup** by `database.init_db()` — the file is created if missing,
  reference data (insurance categories, policy types, payment statuses)
  is seeded if empty, and idempotent migrations bring older databases up
  to date.
- A bootstrap admin row is seeded from `INITIAL_ADMIN_EMAIL` the first
  time `app_users` has no active admins.
- Two rolling backups can be configured via the **Settings** page in the
  web UI:
  - `insurance_pre_modify_backup.db` is replaced before the first
    write of each request.
  - `insurance_daily_backup.db` is replaced at most once per calendar
    day, also before a write.
  Leave the folder blank to disable backups. Backup failures are logged
  but never block normal operation.
- For routine operation you should not have to edit the database
  manually.

### Clear application data

`backend\clear_all_data.bat` deletes application rows while keeping the
database schema and reference tables intact. By default it targets the
repo database at `backend\insurance.db`:

```powershell
& ".\backend\clear_all_data.bat"
```

To clear data from an installed copy, stop the Windows service first,
pass the installed database path with `--db`, then start the service
again. Run PowerShell as Administrator when the app is installed under
`C:\Program Files`.

```powershell
& "C:\Program Files\InsuranceManagerBackend\service.bat" stop
& ".\backend\clear_all_data.bat" --db "C:\Program Files\InsuranceManagerBackend\backend\insurance.db"
& "C:\Program Files\InsuranceManagerBackend\service.bat" start
```

In PowerShell, use `&` before quoted `.bat` paths when passing arguments.

---

## Testing

The test suite lives under `backend/tests/` and uses temporary SQLite
files; it never touches the real `backend/insurance.db`.

Run the full suite from the repo root:

```bash
python -m pytest -c backend/pytest.ini
```

Other recipes:

```bash
# Verbose
python -m pytest -c backend/pytest.ini -v

# A single file
python -m pytest -c backend/pytest.ini backend/tests/test_policies.py

# Match a name
python -m pytest -c backend/pytest.ini -k expiry
```

Long-form test docs (fixtures, scoping, environment quirks) live in
[`backend/TESTING.md`](backend/TESTING.md).

---

## Build, installer, and Windows service

All build helpers live under `scripts/`. They assume a working venv at
`.venv/` (created by `scripts/recreate_venv.bat`).

### Build the Windows installer

A single command produces the Inno Setup `.exe`:

```bash
scripts\build_installer.bat
```

That script:

1. Calls `scripts/build_service_exe.bat` (PyInstaller) to package the
   backend into `dist/InsuranceBackendService/InsuranceBackendService.exe`.
2. Calls `scripts/build_frontend.bat` to run `yarn build` and stage
   `frontend/build/` into `frontend_dist/`.
3. Runs `ISCC.exe installer/InsuranceManagerBackend.iss` to produce
   `installer_output/InsuranceManagerBackendSetup.exe`.

You need **Inno Setup 6** installed (the script auto-detects it under
`Program Files (x86)\Inno Setup 6\` or on `PATH`).

### Manage the Windows service

After installing, manage the service through the dispatcher (run as
Administrator):

```bash
scripts\service.bat install     :: Register InsuranceBackendService (auto-start)
scripts\service.bat status      :: Show current state
scripts\service.bat start       :: Start the service
scripts\service.bat stop        :: Stop the service
scripts\service.bat restart     :: Stop, then start
scripts\service.bat uninstall   :: Remove the service
```

The service reads `config/backend_service_config.json` for host, port,
log level, and whether to serve the bundled frontend.

---

## API overview

All endpoints are mounted under `/api/`. The list below is a summary of
the actual routers in `backend/routers/` — see the files for full
signatures.

| Area | File | Notable endpoints |
|---|---|---|
| System | `routers/system.py` | `GET /api/`, `GET /api/health` |
| Auth | `routers/auth.py` | `POST /api/auth/google`, `POST /api/auth/dev-login`, `GET /api/auth/me`, `POST /api/auth/logout` |
| Admin users | `routers/app_users.py` | `GET/POST /api/users`, `GET/PUT/DELETE /api/users/{id}`, `PUT /api/users/{id}/status` |
| Customers | `routers/customers.py` | `GET/POST /api/customers`, `GET/PUT/DELETE /api/customers/{id}`, plus `GET/PUT /api/admin/customers[/{id}]` |
| Policies | `routers/policies.py` | `GET/POST /api/policies`, `GET/PUT/DELETE /api/policies/{id}`, `GET /api/policies/{id}/detail`, `PATCH /api/policies/{id}/{contact|payment|renewal-resolution}` |
| Renewals | `routers/renewals.py` | `GET /api/renewals/reminders`, `GET /api/renewals/expiring-list` |
| Insurance / policy types | `routers/types.py` | `GET /api/insurance-types`, `GET /api/policy-types` (filterable by `insurance_type_id`) |
| Settings | `routers/settings.py` | `GET/PUT /api/settings` |
| Statements (CSV import) | `routers/statements.py` | `POST /api/import/statement-csv`, `GET /api/import/statement-lines/summary`, `GET /api/statement-lines`, `POST /api/import/statement-lines` |
| Exports | `routers/exports.py` | `GET /api/export/policies-csv`, `GET /api/export/full-data-zip` |
| Sync / dashboard | `routers/sync.py` | `POST /api/sync/generate-snapshot`, `GET /api/sync/status`, `GET /api/statistics/dashboard` |

Every endpoint except `/api/health`, the public auth endpoints, and the
site root requires a backend JWT in `Authorization: Bearer ...`.
Admin-only endpoints (notably everything under `/api/users` and the
`/api/admin/...` grids) additionally require `role = "admin"`.

---

## Important business concepts

### Insurance Type vs Policy Type

The system models the insurance taxonomy in two layers, surfaced through
two dropdowns in the policy form:

- **Insurance Type** — the high-level *line of business*. The seed data
  ships these five categories:

  | Insurance Type |
  |---|
  | Motor |
  | Health |
  | Life |
  | Travel |
  | Property |

- **Policy Type** — the specific plan / variant under that line of
  business. The seeded combinations are:

  | Insurance Type | Policy Type |
  |---|---|
  | Motor | Comprehensive |
  | Motor | Third Party |
  | Motor | Own Damage |
  | Health | Individual |
  | Health | Family Floater |
  | Health | Group Policy |
  | Life | Term Plan |
  | Life | Endowment Plan |
  | Life | ULIP |
  | Travel | Domestic Travel |
  | Travel | International Travel |
  | Property | Home Insurance |
  | Property | Commercial Property |

The backend exposes both lists at `/api/insurance-types` and
`/api/policy-types`. The Policy Type list accepts an
`insurance_type_id` query parameter so the UI can narrow the dropdown.

**UI relationship.** Pick the Insurance Type first, then the Policy Type
field re-populates with only the variants that belong to that line of
business.

### Customer name read-only on policy update

Updating a policy is allowed to refresh customer-side details (phone,
address, etc.) when permitted by the schema, but the **customer's name
is treated as read-only on policy updates**. To rename a customer, edit
the customer through `PUT /api/customers/{id}` (or
`PUT /api/admin/customers/{id}`).

---

## Roles and permissions

There are two roles: `admin` and `user`.

- **`admin`** — full access to every API and every page in the web UI,
  including the **User management** page (`/admin/users`) and the
  admin-only customer grid (`/admin/customers`).
- **`user`** — sees the day-to-day pages (Dashboard, Customers,
  Policies, Statements, etc.) but cannot manage users or hit
  `/api/admin/...` endpoints. The web UI hides admin routes from regular
  users.

Safety guards built into the admin user service:

- The last active admin **cannot** be demoted, deactivated, or deleted.
- Disabled users are rejected at login and on every subsequent request,
  so an existing JWT for a disabled user stops working immediately.
- Identity is authoritative via Google — the backend never stores
  passwords.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `python` is not recognized | Install Python 3.11+ from python.org and tick "Add to PATH", or set `PYTHON_FOR_VENV` and re-run `scripts/recreate_venv.bat`. |
| `No .venv found` when running `scripts/run_backend.bat` | Run `scripts/recreate_venv.bat` first to create `.venv/` and install requirements. |
| `ModuleNotFoundError: uvicorn` | The active interpreter isn't the project venv. Activate `.venv\Scripts\activate.bat` or use `scripts/run_backend.bat`. |
| `yarn` not found | Install Node 18+ and Yarn 1 (`npm install -g yarn`). `npm install` works too but the project ships `yarn.lock`. |
| Login returns "Authentication is not configured" | `GOOGLE_CLIENT_ID` and/or `AUTH_JWT_SECRET` aren't set in `backend/.env`. Restart the backend after editing the file. |
| Android app can't reach the backend | Check `REACT_APP_BACKEND_URL` / the Android build's server URL and confirm the device can hit the host (use the LAN IP, not `127.0.0.1`, on a real device). Also check `GOOGLE_WEB_CLIENT_ID`. |
| `sqlite3.OperationalError: unable to open database file` | The configured path doesn't exist or isn't writable. Either unset `INSURANCE_DB_PATH` (default is `backend/insurance.db`) or point it at a writable folder. |
| Pre-modify / daily backups aren't appearing | Open the **Settings** page and configure a writable folder for `database_backup_folder`. Backup failures are logged in the backend log. |
| pytest segfaults | A vendor-patched Python build (e.g. an in-repo `bmcpython`) is being picked up. Run `unset PYTHONHOME EM_PYTHON_HOME PYTHONPATH` before invoking pytest from a stock CPython. See [`backend/TESTING.md`](backend/TESTING.md). |
| Installer build fails with "Inno Setup Compiler was not found" | Install Inno Setup 6, or add `ISCC.exe` to `PATH`. |

---

## Contributing / development notes

- Keep **backend**, **frontend**, and **Android** changes in separate
  commits where possible — they have different reviewers and different
  CI requirements.
- Don't commit secrets. `backend/.env`, `frontend/.env`, and
  `local.properties` are git-ignored on purpose.
- Yarn is the canonical package manager for the frontend. Don't mix
  `package-lock.json` and `yarn.lock` — keep `yarn.lock`.
- The backend is organised in Clean-Architecture layers
  (`routers/` → `services/` → `repositories/` → `database/`), and the
  domain rules live in `domain/`. New endpoints should keep routers thin
  and put SQL in repositories, business logic in services.
- Add tests under `backend/tests/`. The shared fixtures
  (`app_env`, `client`, `make_customer`, `make_policy`) make most cases
  one-liners — see existing files for the pattern.
- Run the full suite before opening a PR:
  ```bash
  python -m pytest -c backend/pytest.ini
  ```

---

## License

A `LICENSE` file is not present in this repository — license is **not
specified**. If you intend to publish or redistribute the project,
add an explicit license file first.
