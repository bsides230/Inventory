# API Contract (Phase 0 Baseline)

## Existing Functional Endpoints
- `GET /api/status`
  - Returns service status and location name.
- `GET /api/categories`
  - Returns available categories and display metadata.
- `GET /api/inventory/{category}`
  - Returns inventory items for a category with current draft quantities.
- `POST /api/inventory/{category}/update`
  - Updates quantity/unit for one inventory item in current draft state.
- `POST /api/submit_order`
  - Generates and saves an order spreadsheet from selected draft quantities.

## New Operational Endpoints
- `GET /health/live`
  - Liveness probe; returns `{"status": "live"}`.
- `GET /health/ready`
  - Readiness probe with basic file checks.
- `GET /api/version`
  - Returns app version and environment from settings.

## Non-Goals in this Contract Revision
- No auth semantics were added.
- No database-backed resources were introduced.
- No request/response shape changes were made for existing order APIs.
