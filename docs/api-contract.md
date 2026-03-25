# API Contract (Phase 1C Draft Submit Transaction Flow)

## Existing Functional Endpoints
- `GET /api/status`
  - Returns service status and location name.
- `GET /api/categories`
  - Returns available categories and display metadata.
- `GET /api/inventory/{category}`
  - Returns inventory items for a category with current draft quantities.
  - If bearer auth is present, quantities are loaded from that user's active DB-backed draft (`order_drafts`/`order_draft_items`).
- `POST /api/inventory/{category}/update`
  - Requires bearer auth.
  - Upserts (or removes when `qty <= 0`) one item in the authenticated user's active draft.
- `POST /api/submit_order`
  - Requires bearer auth.
  - Performs an atomic submit transaction:
    - validates active draft has items,
    - writes spreadsheet artifact to `orders/`,
    - snapshots draft into `orders` + `order_items`,
    - marks the submitted draft as non-active.
  - On export/persistence failure, DB changes are rolled back and no draft is cleared.

## Auth Semantics
- Write endpoints (`/api/inventory/{category}/update`, `/api/submit_order`) require `Authorization: Bearer <jwt>`.
- JWT verification uses `AUTH_JWT_SECRET` and `AUTH_JWT_ALGORITHM`.
- `sub` claim is required and is mapped to `users.external_id`.
- `email`, `name`, and `role` claims are optional; defaults are inferred if missing.
- Unknown users are provisioned in the `users` table on first authenticated request.

## New Operational Endpoints
- `GET /health/live`
  - Liveness probe; returns `{"status": "live"}`.
- `GET /health/ready`
  - Readiness probe with basic file checks.
- `GET /api/version`
  - Returns app version and environment from settings.

## Non-Goals in this Contract Revision
- No email delivery/retry workflow (Phase 2).
- No admin API surface changes beyond role claim scaffolding in auth context.
