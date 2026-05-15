# Kids Reading Tracker — Copilot Instructions

## Project Purpose

Kids Reading Tracker is a family-oriented reading management application. Parents can create
accounts, add child profiles (or child accounts for kids 13+), and track each person's
reading activity. Books are organized into shelves: **Currently Reading**, **Want to Read**,
**Read**, and **Did Not Finish**. Books can be discovered by scanning an ISBN barcode or by
entering one manually; metadata is automatically imported from Open Library.

The goal is to make reading feel rewarding and organized for children while giving parents
visibility into what everyone in the family is reading.

---

## Repository Structure

This is an **Nx monorepo** managed with npm workspaces.

```
kids-reading-tracker/
├── apps/
│   ├── api/          # Django REST API (Python, uv)
│   ├── web/          # Parent/child web app (React + Vite + Bootstrap)
│   ├── admin/        # Internal admin dashboard (React + Vite)
│   └── mobile/       # React Native mobile app (Expo SDK 54)
└── packages/
    └── api-types/    # Shared TypeScript types generated from the API schema
```

### `apps/api` — Django API

- **Runtime**: Python, managed with `uv`. All Django commands use `uv run manage.py …`.
- **Auth**: JWT via `rest_framework_simplejwt`. Web clients use HttpOnly cookie auth;
  mobile uses `Authorization: Bearer <token>` headers.
  The custom `CookieOrBearerJWTAuthentication` class handles both.
- **Apps**:
  - `core` — Custom `User` model (roles: `parent` / `child`), `ChildProfile`,
    `SocialAccount`, auth views (register, login, logout, me, token refresh,
    Google/Apple OAuth stubs), child profile/account management views.
  - `catalog` — `Author`, `Book` models. `openlibrary.py` fetches book metadata by ISBN.
    `services.py` contains `get_or_import_book()`.
  - `library` — `ShelfEntry` (user ↔ book ↔ shelf), `ReadingSession`.
    Shelf views allow listing, adding by ISBN, moving, and removing books.
- **Database**: SQLite in development (`db.sqlite3`).
- **API schema**: `drf_spectacular` — schema available at `/api/schema/`.

### `apps/web` — Web Frontend

- React 19 + TypeScript + Vite
- Bootstrap 5 for styling
- State-based routing (no React Router) — a `page` state variable drives the active view
- Auth persisted in HttpOnly cookies set by the API
- Key views: Login/Register, Library (shelf tabs + book cards), Add Book (ISBN entry)

### `apps/admin` — Admin Dashboard

- React 19 + TypeScript + Vite
- Separate Vite app for internal tooling; shares the same API

### `apps/mobile` — Mobile App

- Expo SDK ~54, React Native 0.81.5, `newArchEnabled: true`
- State-based routing (`type Screen = 'library' | 'add-book'`) — no `react-navigation`
- Auth persisted in `@react-native-async-storage/async-storage`
- `src/api/client.ts` — authenticated fetch wrapper; `API_BASE` must be updated to the
  host machine's LAN IP (e.g. `http://192.168.x.x:8000`) when building for a physical device
- Key screens: `LoginScreen`, `LibraryScreen`, `AddBookScreen` (camera barcode scanner)

### `packages/api-types`

- TypeScript types generated from the OpenAPI schema.
- Regenerate with `npm run generate:types` from the repo root.

---

## Development Workflow

### Starting all services

```bash
# From repo root — starts API + web + admin concurrently
npm run dev

# Mobile only
npm run dev:mobile
```

### Running the API alone

```bash
cd apps/api
uv run manage.py runserver
```

### Creating migrations

```bash
cd apps/api
uv run manage.py makemigrations
uv run manage.py migrate
```

---

## Testing Requirements

> **Testing is a required part of every change to the API.** Follow these rules without
> exception whenever new API code is written or modified.

### Rule 1 — Write tests for every new model

When a new Django model is added to any app in `apps/api`, write tests in that app's
`tests.py` that verify:

- The model can be created with valid data.
- All required fields enforce their constraints (blank, null, unique).
- The `__str__` method returns a meaningful, non-empty string.
- Any custom methods (e.g. `set_pin` / `check_pin` on `ChildProfile`) behave correctly.
- Relationships (ForeignKey, ManyToMany) work as expected in both directions.
- Any `Meta` ordering is applied correctly.

### Rule 2 — Write tests for every new view / API endpoint

When a new DRF view or URL is added, write `APITestCase` tests in that app's `tests.py`
that verify:

- **Authentication**: unauthenticated requests receive `401` or `403`.
- **Authorization**: users can only access their own data; cross-user access returns `403`
  or `404`.
- **Happy path**: a valid request returns the expected status code and response shape.
- **Validation errors**: invalid or missing fields return `400` with a useful message.
- **Edge cases**: duplicates, non-existent PKs, and boundary conditions.

Use `APITestCase` from `rest_framework.test` and generate JWT tokens with
`rest_framework_simplejwt.tokens.RefreshToken` (see existing tests for the helper pattern).

### Rule 3 — Run the full test suite after every change

After writing new tests (or making any change to `apps/api`), always run the full suite:

```bash
cd apps/api
uv run manage.py test
```

All tests must pass before the work is considered complete. If an existing test breaks,
diagnose and fix it — do not delete or skip tests to make the suite green.

### Rule 4 — Test file conventions

- Tests live in `apps/api/<app_name>/tests.py`.
- Group tests into `TestCase` / `APITestCase` subclasses by the object being tested
  (e.g. `UserModelTest`, `LoginViewTest`).
- Use descriptive method names: `test_<scenario>_<expected_outcome>`.
- Keep shared setup in `setUp` or module-level factory helpers (see `make_parent` /
  `make_child` in `core/tests.py` for the established pattern).
- Avoid hitting real external services — patch `openlibrary` calls with `unittest.mock`.

---

## Frontend Testing (web & admin)

### Framework

Both `apps/web` and `apps/admin` use **Vitest** (test runner) + **React Testing Library**
(component rendering) + **jsdom** (browser environment).

Run the tests:

```bash
# From inside the app directory:
npm test          # single run
npm run test:watch  # watch mode

# Or from the repo root:
npm test --workspace=apps/web
npm test --workspace=apps/admin
```

### Rule 1 — Write tests for every new component

When a new React component is added to `apps/web` or `apps/admin`, create a
`<ComponentName>.test.tsx` co-located next to the source file that verifies:

- The component renders without crashing.
- All meaningful visible states (loading, empty, populated, error) are covered.
- User interactions (clicks, form submissions) trigger the correct callbacks or
  state changes.

### Rule 2 — Write tests for every new page

When a new page component is added, write tests that verify:

- **Unauthenticated / authenticated rendering differences** (use `vi.mock` on
  `AuthContext` to control the `useAuth` return value).
- **Form validation**: required fields, client-side error messages.
- **Happy-path submission**: correct API function is called with correct arguments
  and navigation occurs on success.
- **API error handling**: error messages are shown in an `alert` role element.
- **In-flight state**: submit button is disabled while a request is pending.

### Rule 3 — Run the full suite after every change

After writing or modifying any component in `apps/web` or `apps/admin`, run:

```bash
npm test --workspace=apps/web
npm test --workspace=apps/admin
```

All tests must pass before the work is considered complete.

### Test file conventions

- Test files live next to their source: `src/components/Foo.test.tsx`,
  `src/pages/BarPage.test.tsx`.
- Use `vi.mock()` for module-level mocks (API modules, `AuthContext`, `useNavigate`).
  Partial mocks of `react-router-dom` use the `importOriginal` pattern to preserve
  `MemoryRouter`, `Link`, and other runtime exports.
- Prefer `getByRole` / `getByLabelText` over `getByTestId` — query by what the user
  sees and interacts with.
- When a query is ambiguous (e.g. two buttons with similar text), use `within()` to
  scope to a container, or use an exact string name instead of a regex.
- Do not test Bootstrap show/hide behaviour — Bootstrap JS is not loaded in jsdom.
  Dropdown items are always in the DOM; click them directly (use `within` scoped to
  `.dropdown-menu` if needed).

---

## General Code Conventions

### Python / Django

- Follow PEP 8; use type hints on new functions.
- All database queries go through the ORM — no raw SQL unless absolutely necessary.
- Keep business logic in `services.py` (or a similarly named module), not in views.
- Views are thin: validate input → call service → return response.
- Use `uv run` for all Python tooling (`uv run manage.py`, `uv run pytest`, etc.).

### TypeScript (web, admin, mobile)

- Strict mode is enabled in all TypeScript configs — do not use `any`.
- Fetch calls go through the centralized API client (`src/api/client.ts` in web/mobile)
  rather than calling `fetch` directly in components.
- State-based routing is the established pattern; do not introduce a router library
  unless explicitly requested.

### General

- Do not introduce new dependencies without a clear justification.
- Do not leave debug logging, commented-out code, or `TODO` stubs in committed code.
- Keep commits focused — one logical change per task.
