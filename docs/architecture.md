# Architecture Overview

## Current Runtime (Phase 0 Baseline)
- **Backend:** FastAPI application served from `server.py`.
- **Frontend:** Static assets under `web/` mounted at `/`.
- **Inventory Data:** JSON category files under `data/`.
- **Session State:** File-backed order drafts per user session in `drafts/` using explicit state flags and optimistic concurrency locking.
- **Order Output:** Excel files generated under `orders/`.

## Request Flow (Current)
1. Client requests category and inventory endpoints.
2. API loads category JSON files and overlays in-progress quantities from the user's active file draft in `drafts/`.
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

The backend now relies solely on file managers (FileDraftManager, FileOrderManager) without any database. Async tasks such as email delivery are handled by an IPC worker polling `ipc/inbox`.
