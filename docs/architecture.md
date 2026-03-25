# Architecture Overview

## Current Runtime (Phase 0 Baseline)
- **Backend:** FastAPI application served from `server.py`.
- **Frontend:** Static assets under `web/` mounted at `/`.
- **Inventory Data:** JSON category files under `data/`.
- **Session State:** In-memory + persisted order draft values in `inventory_state.json`.
- **Order Output:** Excel files generated under `orders/`.

## Request Flow (Current)
1. Client requests category and inventory endpoints.
2. API loads category JSON files and overlays in-progress quantities from `inventory_state.json`.
3. Client posts updates per item to `/api/inventory/{category}/update`.
4. Client submits order to `/api/submit_order`.
5. API collects non-zero line items and writes an Excel order file.

## Phase 0 Stabilization Additions
- Typed environment-backed settings (`app_env`, `log_level`, `app_version`).
- Request-ID middleware with structured logs and `X-Request-ID` response header.
- Operational endpoints:
  - `/health/live`
  - `/health/ready`
  - `/api/version`

## Target Direction (Future Phases)
- Move from file-backed order state toward DB-backed multi-user draft orders.
- Add authenticated user identity and write protection.
- Add robust admin controls and deployment hardening.

Phase 0 intentionally preserves existing order behavior while creating safer observability and operational baselines.
