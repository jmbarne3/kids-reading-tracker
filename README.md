# Kids Reading Tracker

A monorepo application for tracking children's reading progress. Parents can manage child profiles, log books, and monitor reading habits across web and mobile interfaces.

---

## Application Stack

This project is a monorepo managed with [Nx](https://nx.dev) and npm workspaces. It contains four apps and one shared package:

| App / Package | Path | Technology |
|---|---|---|
| REST API | `apps/api` | Django 5.2, Django REST Framework, SQLite |
| Web app | `apps/web` | React 19, TypeScript, Vite |
| Admin app | `apps/admin` | React 19, TypeScript, Vite |
| Mobile app | `apps/mobile` | React Native, Expo 54 |
| Shared API types | `packages/api-types` | TypeScript, openapi-typescript |

### API (`apps/api`)

Built with **Django 5.2** and **Django REST Framework**. Key libraries include:

- `djangorestframework-simplejwt` — JWT authentication stored in HttpOnly cookies
- `django-cors-headers` — CORS support for local development
- `drf-spectacular` — auto-generates an OpenAPI schema, which powers the shared TypeScript types
- `google-auth` / `pyjwt` — Google and Apple social sign-in support
- Open Library API integration for book data lookups (no account required)

The database is SQLite for development. The API serves a custom `User` model that supports parent and child roles, as well as lightweight `ChildProfile` records for younger children who do not need their own login.

### Web & Admin (`apps/web`, `apps/admin`)

Both are standalone **React 19 + TypeScript** single-page applications bundled with **Vite**. They share no runtime code but both consume the types generated from the API schema.

### Mobile (`apps/mobile`)

A **React Native** app bootstrapped with **Expo** (SDK 54). It uses `expo-camera` for any scan/capture features. You can run it in the Expo Go client during development, or produce native builds for iOS and Android.

### Shared Types (`packages/api-types`)

TypeScript types are generated directly from the live API's OpenAPI schema using `openapi-typescript`. Re-generate them any time the API changes by running the `generate:types` script (the API must be running first).

---

## System Prerequisites

Install the following tools before setting up the project:

### Required

| Tool | Version | Purpose | Install |
|---|---|---|---|
| [Node.js](https://nodejs.org) | 20 LTS or later | Web, Admin, and Mobile apps | `brew install node` or [nodejs.org](https://nodejs.org) |
| [Python](https://www.python.org) | 3.11 or later | Django API | `brew install python` or [python.org](https://www.python.org) |
| [uv](https://docs.astral.sh/uv/) | Latest | Python dependency and virtual-env management for the API | `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

### Required for mobile development

| Tool | Purpose | Install |
|---|---|---|
| [Expo CLI](https://docs.expo.dev/more/expo-cli/) | Run and build the Expo app | `npm install -g expo-cli` |
| [Xcode](https://developer.apple.com/xcode/) *(macOS only)* | iOS simulator and native builds | Mac App Store |
| [Android Studio](https://developer.android.com/studio) | Android emulator and native builds | [developer.android.com](https://developer.android.com/studio) |

> You can skip the iOS/Android tooling if you only plan to use the **Expo Go** app on a physical device.

---

## First-Time Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd kids-reading-tracker
```

### 2. Install Node.js dependencies

From the repo root, install all npm workspace dependencies at once:

```bash
npm install
```

### 3. Set up the Python API

`uv` handles the Python virtual environment and dependencies automatically. Run the following from the repo root (or from `apps/api`):

```bash
cd apps/api
uv sync          # creates .venv and installs all Python dependencies
```

### 4. Configure environment variables

The API reads a few optional environment variables. Create a `.env` file inside `apps/api/` if you need to enable social login:

```dotenv
# apps/api/.env

# Required for Google Sign-In
GOOGLE_CLIENT_ID=your-google-client-id

# Required for Apple Sign-In
APPLE_APP_ID=your-apple-app-bundle-or-service-id
```

These can be left blank if you are only using username/password authentication locally.

### 5. Run database migrations

```bash
# from apps/api/
uv run manage.py migrate
```

### 6. Create a superuser (optional)

```bash
# from apps/api/
uv run manage.py createsuperuser
```

### 7. Generate shared TypeScript types

The types package pulls its schema from a running API instance. Start the API first, then in a second terminal:

```bash
# Terminal 1 — start the API
cd apps/api && uv run manage.py runserver

# Terminal 2 — generate types
npm run generate:types
```

You only need to redo this step when the API models or endpoints change.

---

## Running the Apps

### Start everything (API + Web + Admin) simultaneously

```bash
npm run dev
```

This runs all three services concurrently via `concurrently`. Individual scripts are also available:

```bash
npm run dev:api      # Django API on http://localhost:8000
npm run dev:web      # Web app on http://localhost:5173 (default Vite port)
npm run dev:admin    # Admin app on http://localhost:5174 (default Vite port)
npm run dev:mobile   # Expo / React Native (opens Metro bundler)
```

### Mobile

```bash
npm run dev:mobile
```

Follow the Metro bundler prompts to open the app in the Expo Go client on a physical device, or press `i` for the iOS simulator or `a` for the Android emulator.

---

## Project Scripts Reference

| Command | Description |
|---|---|
| `npm run dev` | Start API, web, and admin apps together |
| `npm run dev:api` | Start Django API only |
| `npm run dev:web` | Start web app only |
| `npm run dev:admin` | Start admin app only |
| `npm run dev:mobile` | Start Expo mobile app |
| `npm run generate:types` | Regenerate TypeScript types from the API schema (API must be running) |

---

## Notes

- **SQLite** is used as the database in development. No database server setup is required.
- The Django `SECRET_KEY` in `settings.py` is intentionally insecure for development. Replace it before deploying to any shared environment.
- `CORS_ALLOW_ALL_ORIGINS = True` is set for local development only. Restrict this before any production deployment.
- JWT tokens are stored in HttpOnly cookies. `AUTH_COOKIE_SECURE` is set to `False` locally; set it to `True` when running over HTTPS.
