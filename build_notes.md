# Build Notes

## 2026-03-25T20:49:32Z — 01_PHASE_0_STABILIZE_AND_PREPARE.md
### Status
COMPLETED

### Objective
- Establish a stable baseline by adding operational documentation, environment-backed typed settings, structured request logging with request IDs, health/version endpoints, and baseline regression tests without altering core order flow behavior.

### Work Completed
- Created architecture documentation describing current file-backed runtime and forward-looking target direction.
- Created API contract documentation that captures existing functional endpoints and newly added operational endpoints.
- Added `.env.example` documenting runtime settings for environment, log level, and version.
- Updated `server.py` to load typed settings from environment (`pydantic-settings`).
- Added request middleware that injects/propagates `X-Request-ID` and emits structured lifecycle logs for request start/completion.
- Added operational endpoints: `/health/live`, `/health/ready`, `/api/version`.
- Preserved existing endpoints and order-generation flow while keeping changes additive.
- Added baseline API tests for health/version plus regression checks for existing status/categories/inventory/submit-order endpoints.
- Added test bootstrap (`tests/conftest.py`) to ensure repo-root imports work under pytest.
- Updated dependencies for testing and settings runtime (`pytest`, `requests`, `httpx`, `pydantic-settings`).

### Files Created
- `prompts/EXECUTION_STATUS.md`
- `docs/architecture.md`
- `docs/api-contract.md`
- `.env.example`
- `tests/test_api_baseline.py`
- `tests/conftest.py`
- `build_notes.md`

### Files Modified
- `server.py`
- `requirements.txt`

### Files Removed
- None

### Key Implementation Details
- Settings are loaded once from environment using `BaseSettings` with `.env` support via `SettingsConfigDict`.
- Request correlation is implemented via FastAPI HTTP middleware that reads incoming `X-Request-ID` or generates a UUID, logs with `extra={"request_id": ...}`, and mirrors the value in response headers.
- Readiness endpoint currently checks baseline filesystem prerequisites (`data/`, `categories.json`) and does not introduce DB dependency.
- Existing order APIs remain file-backed and backward-compatible in shape and behavior for this phase.

### Tests / Validation
- Added tests in `tests/test_api_baseline.py` for:
  - `/health/live`
  - `/health/ready`
  - `/api/version`
  - `/api/status` (regression)
  - `/api/categories` (regression)
  - `/api/inventory/{category}` (regression)
  - `/api/submit_order` empty state behavior (regression)
  - `X-Request-ID` response propagation
- Ran `pip install -r requirements.txt` to satisfy test/runtime dependencies.
- Ran `pytest -q tests` successfully: 8 passed.
- Ran `python -m compileall server.py tests` successfully.
- `pytest -q` at repository root fails because legacy script `test_post.py` is collected as a test module and expects external runtime context.

### Blockers / Issues
- Root-level `pytest` collection includes `test_post.py` (an integration script), causing non-baseline failure unless test invocation is scoped to `tests/`.

### Follow-Up Notes
- In Phase 1, consider adding `pytest.ini`/test discovery rules to exclude non-test utility scripts and make `pytest` from repo root deterministic.
- Future phases introducing DB/auth should extend `/health/ready` checks to include DB connectivity and dependency readiness.

### Next Recommended Prompt
- `02_PHASE_1_MULTI_USER_DATA_MODEL.md`

## 2026-03-25T21:06:39Z — 02A_PHASE_1_SCHEMA_AND_MODELS.md
### Status
COMPLETED

### Objective
- Create the Phase 1A relational data foundation by introducing database engine/session wiring, initial schema migrations, ORM models, minimal repositories, and test coverage for migration lifecycle plus draft/order CRUD.

### Work Completed
- Added a new `db` package with:
  - environment-based DB URL resolution,
  - SQLAlchemy engine/session factory helpers,
  - context-managed session lifecycle helper,
  - exports for future sub-phase use.
- Added SQLAlchemy ORM model definitions for all core Phase 1 entities:
  - `users`, `order_drafts`, `order_draft_items`, `orders`, `order_items`, `app_settings`.
- Added repository abstractions for core data access patterns needed by upcoming sub-phases:
  - `UserRepository` for creation/lookups,
  - `OrderDraftRepository` for draft creation, item upserts, and hydration,
  - `OrderRepository` for draft-to-order persistence.
- Added Alembic migration scaffold (`alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`) and first schema revision (`20260325_01`).
- Added development bootstrap script (`scripts/bootstrap_dev_db.py`) to run migrations and seed a default local dev user.
- Updated app configuration surface to include `DATABASE_URL` in server settings and `.env.example`.
- Updated dependencies to include `sqlalchemy` and `alembic`.
- Added tests that validate migration upgrade/downgrade and repository-backed CRUD behavior.

### Files Created
- `db/__init__.py`
- `db/database.py`
- `db/models.py`
- `db/repositories.py`
- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/20260325_01_create_multi_user_schema.py`
- `scripts/bootstrap_dev_db.py`
- `tests/test_db_migrations.py`
- `tests/test_db_models.py`

### Files Modified
- `server.py`
- `.env.example`
- `requirements.txt`
- `prompts/EXECUTION_STATUS.md`
- `build_notes.md`

### Files Removed
None

### Key Implementation Details
- Database connectivity is currently environment-driven via `DATABASE_URL` with a default local SQLite path (`sqlite:///./inventory.db`).
- SQLite-specific engine/session behavior is handled centrally (`check_same_thread=False`) so tests and dev runtime can share helpers.
- Alembic runtime pulls DB URL from environment, enabling isolated temporary DB migration tests.
- Draft item storage enforces uniqueness per draft and inventory item (`uq_order_draft_item`) to support upsert semantics.
- Repository flow captures lifecycle transition from active draft to submitted order by cloning draft items into `order_items` and flipping draft status.
- This phase intentionally does not rewrite API endpoints or enforce authentication; it is strictly foundational.

### Tests / Validation
- Added migration smoke test:
  - `tests/test_db_migrations.py` verifies `upgrade head` creates expected tables and `downgrade base` returns to `alembic_version` only.
- Added model/repository CRUD test:
  - `tests/test_db_models.py` validates user creation, draft create+item upsert, order creation from draft, and draft status transition.
- Ran `pip install -r requirements.txt` to install migration/ORM dependencies.
- Ran `pytest -q tests` successfully: 10 passed.
- Ran `python -m compileall db scripts/bootstrap_dev_db.py alembic tests` successfully.
- Observed Alembic deprecation warning about `path_separator`; non-blocking for current functionality.

### Blockers / Issues
- Parent `02_PHASE_1_MULTI_USER_DATA_MODEL.md` remains decomposed by design; execution proceeds via `02A` → `02B` → `02C` to satisfy one-prompt-per-PR scope discipline.
- Root-level `pytest -q` still includes legacy `test_post.py`; scoped test invocation remains `pytest -q tests`.

### Follow-Up Notes
- For Phase 1B, wire auth identity to `users.external_id` and enforce write ownership against draft/order user IDs.
- Consider adding Alembic `path_separator = os` in `alembic.ini` to remove deprecation warnings in CI logs.
- Keep API behavior backward-compatible during 1B/1C, introducing DB-backed draft flow incrementally rather than replacing all file-backed endpoints at once.

### Next Recommended Prompt
- `02B_PHASE_1_AUTH_AND_WRITE_PROTECTION.md`

## 2026-03-25T21:25:02Z — 02B_PHASE_1_AUTH_AND_WRITE_PROTECTION.md
### Status
COMPLETED

### Objective
- Implement request-time authentication identity propagation and enforce write protection so only authenticated users can mutate ordering draft/order state.

### Work Completed
- Added a dedicated auth module (`db/auth.py`) that:
  - validates bearer JWT tokens,
  - extracts identity claims,
  - provisions/updates corresponding rows in the `users` table,
  - stores authenticated user context on `request.state`.
- Extended app settings with JWT config (`AUTH_JWT_SECRET`, `AUTH_JWT_ALGORITHM`) and attached settings to `app.state` so dependencies can resolve auth/DB config consistently.
- Updated inventory state handling in `server.py` to support per-user state buckets keyed by authenticated `sub`, while preserving backward compatibility for legacy flat state files by auto-migrating loaded shape in memory.
- Enforced auth on write endpoints:
  - `POST /api/inventory/{category}/update`
  - `POST /api/submit_order`
- Updated read endpoint behavior for `GET /api/inventory/{category}` to return quantities scoped to authenticated user context when auth is provided.
- Updated API contract documentation to describe write-protection semantics and expected JWT claims.
- Added auth protection and isolation tests plus adjusted baseline test expectations for unauthenticated submit behavior.

### Files Created
- `db/auth.py`
- `tests/test_auth_write_protection.py`

### Files Modified
- `server.py`
- `.env.example`
- `requirements.txt`
- `docs/api-contract.md`
- `tests/test_api_baseline.py`
- `prompts/EXECUTION_STATUS.md`
- `build_notes.md`

### Files Removed
None

### Key Implementation Details
- JWT verification is currently symmetric (`HS256` default) and uses environment-backed settings.
- `sub` claim is mandatory and mapped to `users.external_id`; `email`, `name`, and `role` are optional with defaults.
- Role data is captured in the in-request auth context (`AuthenticatedUser.role`) as scaffolding for later admin boundary work.
- Existing file-backed draft persistence remains in place for this phase, but draft quantities are now partitioned per authenticated user to eliminate cross-user contamination for write/read routes.
- The migration remains intentionally non-transactional for submit and does not yet replace submit flow with DB-backed atomic draft-to-order transition (deferred to 02C).

### Tests / Validation
- Added tests:
  - `tests/test_auth_write_protection.py`
    - anonymous write denied,
    - invalid token denied,
    - user draft isolation on update/read routes.
- Updated baseline regression expectation:
  - unauthenticated `/api/submit_order` now returns HTTP 401.
- Ran `pip install -r requirements.txt`.
- Ran `pytest -q tests` with passing result (13 passed).
- Ran `pytest -q tests/test_auth_write_protection.py` after JWT secret-length tweak (3 passed).
- Ran `python -m compileall server.py db tests` successfully.

### Blockers / Issues
- Root-level `pytest -q` still collects legacy `test_post.py`; scoped invocation `pytest -q tests` remains recommended.

### Follow-Up Notes
- Phase 1C should replace this interim per-user file state with full DB-backed draft lifecycle and atomic submit transaction.
- Consider introducing JWT expiry/audience checks and key rotation strategy in Phase 6 security hardening.
- If legacy unauthenticated write clients still exist, they must be updated to send bearer auth before deployment.

### Next Recommended Prompt
- `02C_PHASE_1_DRAFT_ORDER_FLOW.md`

## 2026-03-25T21:34:25Z — 02C_PHASE_1_DRAFT_ORDER_FLOW.md
### Status
COMPLETED

### Objective
- Finalize Phase 1C by replacing file-backed per-user draft state with relational draft flow, implementing atomic submit transaction behavior, and validating isolation/rollback semantics.

### Work Completed
- Removed legacy `inventory_state.json` in-memory bucket logic from `server.py` and switched draft reads/writes to DB-backed repositories.
- Added helper methods in `OrderDraftRepository` to get/create active drafts per user and remove items when quantity is set to zero.
- Updated `GET /api/inventory/{category}` to hydrate `qty`/`unit` values from authenticated user's active draft items.
- Updated `POST /api/inventory/{category}/update` to validate category+item existence and persist draft item updates in `order_draft_items`.
- Reworked `POST /api/submit_order` into a transactional flow that:
  - loads active draft with items,
  - writes spreadsheet artifact,
  - snapshots into `orders`/`order_items`,
  - marks draft as submitted,
  - removes partial artifact and preserves draft when an exception occurs.
- Added dedicated Phase 1C tests for:
  - multi-user submit isolation,
  - rollback behavior when export fails,
  - end-to-end draft update → submit lifecycle.
- Updated API contract documentation to reflect final Phase 1C semantics and removed outdated “not implemented yet” note.

### Files Created
- `tests/test_draft_submit_flow.py`

### Files Modified
- `server.py`
- `db/repositories.py`
- `tests/test_auth_write_protection.py`
- `docs/api-contract.md`
- `prompts/EXECUTION_STATUS.md`
- `build_notes.md`

### Files Removed
- None

### Key Implementation Details
- Draft state now exists only in DB rows (`order_drafts`, `order_draft_items`) for authenticated users; no shared cross-user mutation path remains.
- Submit transaction uses one DB session context so order snapshot persistence is rolled back if spreadsheet generation fails.
- Artifact cleanup (`filepath.unlink`) is performed when submit fails after path creation to avoid stale partial files.
- Backward compatibility for unauthenticated reads is maintained (`qty=0` default), while write endpoints remain auth-protected.

### Tests / Validation
- Ran `pip install -r requirements.txt` to ensure runtime/test dependencies were present.
- Ran `pytest -q tests` and validated all suites including new Phase 1C tests.
- Ran `python -m compileall server.py db tests` to validate syntax/import integrity.

### Blockers / Issues
- Root-level `pytest -q` still collects legacy `test_post.py`; scoped invocation `pytest -q tests` remains required.

### Follow-Up Notes
- Phase 2 should consume `orders.export_filename` + persisted order snapshot for email delivery and retry orchestration.
- Consider adding explicit DB transaction tests around order persistence exceptions (beyond export failure) when email queueing is introduced.

### Next Recommended Prompt
- `03_PHASE_2_EMAIL_DELIVERY_AND_TEXT_CONFIG.md`
