# Insurance App

Backend (FastAPI + SQLite) • Web (React / CRA) • Android (Jetpack Compose).

## Authentication & Authorization

Access to every `/api/*` endpoint (except `/api/health` and the public auth
endpoints themselves) is gated by a **Google Sign-In → backend JWT** flow.

- Admins pre-approve Gmail addresses in the `app_users` table through the
  **User management** page on the web (`/admin/users`).
- Users (web or Android) sign in with Google; the backend verifies the Google
  ID token and issues a short-lived JWT only if the email is in `app_users`
  and the row is active.
- Two roles: `admin` and `user`. Admin-only endpoints live under
  `/api/users` and the web UI hides admin-only routes for regular users.

### Required environment variables

Configure these in `backend/.env` (or the process environment):

| Variable                | Purpose                                                                                     |
|-------------------------|---------------------------------------------------------------------------------------------|
| `GOOGLE_CLIENT_ID`      | OAuth 2.0 **Web** Client ID. Must match the frontend/Android client IDs used to sign in.    |
| `AUTH_JWT_SECRET`       | 32+ byte random string used to sign backend JWTs. **Required for production.**              |
| `AUTH_JWT_ALGORITHM`    | Optional; defaults to `HS256`.                                                              |
| `AUTH_JWT_LIFETIME_MIN` | Optional; session lifetime in minutes. Defaults to `720` (12h).                             |
| `INITIAL_ADMIN_EMAIL`   | Seeds the very first admin on an empty `app_users` table. Safe to leave set after bootstrap.|
| `INITIAL_ADMIN_NAME`    | Optional display name for the seeded admin.                                                 |

Frontend (`frontend/.env`):

| Variable                      | Purpose                                                         |
|-------------------------------|-----------------------------------------------------------------|
| `REACT_APP_GOOGLE_CLIENT_ID`  | Same OAuth 2.0 Web Client ID used by the backend.               |
| `REACT_APP_BACKEND_URL`       | Base URL of the API (already existed).                          |

Android (Gradle properties; set in `~/.gradle/gradle.properties` or
`insurance-android/gradle.properties`):

```
GOOGLE_WEB_CLIENT_ID=<same OAuth 2.0 Web Client ID>
```

### First-time setup

1. **Google Cloud console** → `APIs & Services` → `Credentials` → **Create
   OAuth client ID** → Application type **Web application**. Add your web
   origin to "Authorized JavaScript origins" (e.g. `http://localhost:3000`).
2. Copy the **Client ID** into all three places above (backend
   `GOOGLE_CLIENT_ID`, frontend `REACT_APP_GOOGLE_CLIENT_ID`, Android
   `GOOGLE_WEB_CLIENT_ID`).
3. Set `AUTH_JWT_SECRET` to a long random value (`python -c "import secrets;
   print(secrets.token_urlsafe(48))"`).
4. Set `INITIAL_ADMIN_EMAIL` to your own Gmail address so the first admin is
   seeded automatically on the first backend boot.
5. Start the backend. The first startup will log:
   `Seeded initial admin app_user 'you@gmail.com'.`
6. Open the web UI, sign in with that Gmail account, then use
   **User management** to add more users.

### Security notes

- Passwords are not stored; identity is authoritative via Google.
- Disabled users (`is_active = false`) are rejected at login and on every
  subsequent request (their existing JWTs fail the principal check).
- The service protects against locking yourself out: the last active admin
  cannot be demoted, deactivated, or deleted until another admin exists.
- Hard deletes of admins are supported but blocked when they would leave
  zero active admins.

## Running locally

```bash
# Backend
cd backend
../.venv/Scripts/python -m uvicorn server:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend
yarn start

# Android
# Open insurance-android/ in Android Studio and run the `app` configuration.
```

## Tests

```bash
cd backend
../.venv/Scripts/python -m pytest tests/
```
