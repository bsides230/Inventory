# API Contract (Phase 3 Public Deployment)

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
  - Triggers post-submit email delivery with XLSX attachment and retry policy.
  - Returns delivery metadata: `delivery_status`, `delivery_attempts`, `delivery_error`.

## Auth Semantics
- Write endpoints (`/api/inventory/{category}/update`, `/api/submit_order`) require `Authorization: Bearer <jwt>`.
- JWT verification uses `AUTH_JWT_SECRET` and `AUTH_JWT_ALGORITHM`.
- `sub` claim is required and is mapped to `users.external_id`.
- `email`, `name`, and `role` claims are optional; defaults are inferred if missing.
- Unknown users are provisioned in the `users` table on first authenticated request.

## Email Delivery Configuration
- Recipients are loaded from `config/order_recipients.txt`.
  - One email per line.
  - Blank lines and `#` comments are ignored.
  - Invalid emails fail validation.
- Recipient list is reloaded automatically when file contents change.
- SMTP settings are configured via environment:
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_SENDER_EMAIL`.
- Retry and failure controls:
  - `EMAIL_RETRY_ATTEMPTS`
  - `EMAIL_RETRY_DELAY_SECONDS`
  - `EMAIL_DEAD_LETTER_LOG`

## Order Delivery Audit Fields
- `orders.delivery_status`: `pending` | `sent` | `failed`
- `orders.delivery_attempts`: number of attempts made for most recent send.
- `orders.delivery_error`: final error when send fails.
- `orders.delivered_at`: timestamp for successful send.

## New Operational Endpoints
- `GET /health/live`
  - Liveness probe; returns `{"status": "live"}`.
- `GET /health/ready`
  - Readiness probe with basic file checks.
- `GET /api/version`
  - Returns app version and environment from settings.

## Deployment Security Controls
- CORS allow-list comes from `CORS_ALLOWED_ORIGINS` (comma-separated list).
- Body-size protection rejects oversized write payloads with `413 Request body too large`.
- In-memory per-IP rate limiter rejects excessive traffic with `429 Rate limit exceeded`.
