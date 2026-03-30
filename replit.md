# Falcones Pizza Inventory & Ordering System

## Overview

A Progressive Web Application (PWA) for managing restaurant inventory and submitting orders at Falcones Pizza locations. Staff members browse inventory categories, add items to a draft order, and submit the order (which is emailed to configured recipients as an Excel attachment).

The system is currently in an active migration from a database-backed architecture to a fully file-backed runtime. The backend is FastAPI (Python), the frontend is a vanilla JS SPA served as static files, and all persistent state lives in local files (JSON drafts, JSONL event logs, XLSX order exports).

**Current state:** File-only backend is the active runtime. No database is required or used. Draft orders, submitted orders, and IPC events are all stored as files on disk.

---

## User Preferences

Preferred communication style: Simple, everyday language.

---

## System Architecture

### Backend

- **Framework:** FastAPI (`server.py`) served via Uvicorn (dev) or Gunicorn (prod).
- **Settings:** Typed environment-backed config using `pydantic-settings` (`BaseSettings`). All settings load from environment variables or a `.env` file. Key settings include `AUTH_JWT_SECRET`, `SMTP_*`, `CORS_ALLOWED_ORIGINS`, `MAX_REQUEST_BODY_BYTES`, and `ORDER_RECIPIENTS_FILE`.
- **Middleware:**
  - Request ID injection/propagation via `X-Request-ID` header with structured logging.
  - CORS middleware with configurable allowed origins.
  - Request body size enforcement (returns 413 if exceeded).
  - In-memory rate limiter (`InMemoryRateLimiter`) returning 429 when threshold exceeded.

### File-Backed Persistence (No Database)

All runtime state is stored on disk using crash-safe helpers in `file_safety.py`:

- `write_json_atomic(path, payload)` — writes to a temp file then atomically renames to avoid partial writes.
- `append_jsonl(path, payload)` — append-only event log writes.
- `with_lock(lock_path)` — `flock`-based exclusive lock for mutual exclusion during writes.

**Key directories and files:**

| Path | Purpose |
|---|---|
| `data/*.json` | Inventory items per category (generated from `item master/Master.xlsx`) |
| `categories.json` | Category metadata (icon, color, labels in EN/ES) |
| `drafts/<user_id>_<draft_id>.json` | Per-user active draft orders with optimistic concurrency (`version` field) |
| `orders/submitted/<order_id>.json` | Finalized submitted orders |
| `orders/flags/<order_id>.state` | State flag file for each order (`submitted`, `emailed`, `email_failed`) |
| `ipc/inbox/`, `ipc/processing/`, `ipc/done/`, `ipc/failed/` | File-based IPC queue for async email delivery |
| `logs/events.jsonl` | Append-only event/transition log |
| `logs/order_email_dead_letter.log` | Failed email delivery payloads |
| `config/order_recipients.txt` | Email recipients, one per line, `#` comments allowed |
| `config/locations.txt` | PIN → location name mappings |
| `config/admin_password.txt` | Admin panel password |

### Service Layer (`services/`)

- **`FileDraftManager`** — CRUD for per-user draft orders stored as JSON files. Uses optimistic concurrency via `version` integers and file locking.
- **`FileOrderManager`** — Creates and updates submitted order records in `orders/submitted/`.
- **`OrderEmailDeliveryService`** — Sends order emails with XLSX attachments via SMTP. Supports configurable retries and dead-letter logging.
- **`RecipientConfigStore`** — Lazy-reloading recipient list that detects file changes via `(mtime_ns, size)` signature comparison.
- **`ipc_worker.py`** — Long-running worker that polls `ipc/inbox/` for `email_send` events, moves them through processing states, and triggers email delivery.

### Authentication

- **JWT-based** using `PyJWT`. Tokens are verified against `AUTH_JWT_SECRET` and `AUTH_JWT_ALGORITHM`.
- `get_optional_authenticated_user` — extracts user from Bearer token if present, returns `None` if missing or invalid.
- `get_required_authenticated_user` — raises HTTP 401 if no valid token.
- Write endpoints (`/api/inventory/{category}/update`, `/api/submit_order`) require authentication.
- Read endpoints (categories, inventory browse) are public.
- Admin panel uses a separate password-based login that issues its own JWT.

### Inventory Data Pipeline

Inventory data originates from `item master/Master.xlsx`. Each sheet tab becomes a category; each row is an item with English (col A) and Spanish (col B) names. The `update_inventory_data.py` script converts the Excel file to per-category JSON files under `data/`. Category metadata (icons, colors, labels) is stored and updated in `categories.json`.

### Frontend

- Vanilla JavaScript SPA under `web/` served as static files by FastAPI.
- PWA with `web/manifest.json` and `web/sw.js` service worker.
- Service worker uses two cache strategies: `STATIC_CACHE` for assets, `API_CACHE` for API responses.
- Supports install prompts (`beforeinstallprompt`), offline banners, and update notifications.
- Admin panel at `web/admin.html` / `web/admin.js` — separate login flow, protected by admin password JWT.
- Styling via Tailwind CSS (CDN) and a custom `web/style.css`.
- Bilingual UI (English/Spanish) driven by API-provided labels.

### API Endpoints (Key)

| Endpoint | Auth | Description |
|---|---|---|
| `GET /health/live` | None | Liveness check |
| `GET /health/ready` | None | Readiness check (verifies `data/`, `categories.json`, write access) |
| `GET /api/version` | None | Returns app version and environment |
| `GET /api/status` | None | Service status and location name |
| `GET /api/categories` | None | Category list with metadata |
| `GET /api/inventory/{category}` | Optional | Items with draft quantities overlaid |
| `POST /api/inventory/{category}/update` | Required | Upsert/remove item in active draft |
| `POST /api/submit_order` | Required | Submit draft → write order file → enqueue email IPC event |
| `POST /api/admin/login` | None (password) | Returns admin JWT |
| `POST /api/admin/upload-master` | Admin JWT | Upload new `Master.xlsx` and rebuild inventory |

### Deployment

- **Dev:** `python server.py` (port from `port.txt`, default 5000).
- **Prod:** Gunicorn with 2 workers; Caddy reverse proxy handles HTTPS and domain routing via `Caddyfile`.
- **Backup:** `scripts/backup.sh` archives `config/`, `data/`, `drafts/`, `orders/`, `ipc/`, `logs/` on a configurable schedule.
- **Data integrity:** `scripts/data_integrity_check.py` validates draft `version` fields and order/flag file consistency.

### Draft Lifecycle

```
active → submitting → submitted → (emailed | email_failed)
                    ↘ abandoned
```

Optimistic concurrency: every draft write checks and increments `version`; stale updates are rejected.

### Order/Email IPC Flow

1. `POST /api/submit_order` writes order JSON + XLSX, then drops an `email_send` event into `ipc/inbox/`.
2. `ipc_worker.py` picks up the event, moves it to `ipc/processing/`, sends the email, then moves to `ipc/done/` or `ipc/failed/`.
3. On worker restart, stale `ipc/processing/` events are requeued.

---

## External Dependencies

### Python Packages

| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn` / `gunicorn` | ASGI servers |
| `pydantic` / `pydantic-settings` | Data validation and typed settings |
| `pandas` / `openpyxl` | Excel file parsing and generation |
| `PyJWT` | JWT encoding/decoding for auth |
| `python-multipart` | File upload support |
| `pytest` / `httpx` / `requests` | Testing |

### Frontend (CDN)

- **Tailwind CSS** — utility-first CSS framework loaded from CDN.
- **Lucide Icons** — icon library loaded from CDN (`unpkg.com/lucide`).
- **Google Fonts** — Inter, Playfair Display, JetBrains Mono.

### SMTP Email

- Configurable via `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_SENDER_EMAIL` environment variables.
- Default dev config points to `localhost:1025` (mailhog/mailpit pattern).
- No external email SaaS is hard-wired; any SMTP server works.

### Reverse Proxy

- **Caddy** — handles HTTPS termination and reverse proxy to FastAPI in production. Configuration in `Caddyfile`. Domain configured via `APP_DOMAIN` environment variable.

### No Database

The system explicitly has **no database dependency** at runtime. A previous architecture used SQLAlchemy + SQLite/PostgreSQL + Alembic, but this was removed. The `deprecated/` directory contains historical artifacts from that era. If a database is added in the future, the `Settings.database_url` field (`sqlite:///./inventory.db` default) is already defined but not actively used.