# API Contract (Phase 1B Auth Write Protection)

## Existing Functional Endpoints
- `GET /api/status`
  - Returns service status and location name.
- `GET /api/categories`
  - Returns available categories and display metadata.
- `GET /api/inventory/{category}`
  - Returns inventory items for a category with current draft quantities.
  - If bearer auth is present, quantities are scoped to the authenticated user (`sub` claim).
- `POST /api/inventory/{category}/update`
  - Requires bearer auth.
  - Updates quantity/unit for one inventory item in the authenticated user's draft state.
- `POST /api/submit_order`
  - Requires bearer auth.
  - Generates and saves an order spreadsheet from selected quantities in the authenticated user's draft state.

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
- No final transactional draft-to-order database submit flow yet (Phase 1C).
- No admin API surface changes beyond role claim scaffolding in auth context.
