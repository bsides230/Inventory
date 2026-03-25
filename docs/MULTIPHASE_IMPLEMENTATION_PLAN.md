# Ordering Platform Finalization & Scale Plan (Multi-Phase)

## 1) Executive Summary
This application already has a working FastAPI + static-web foundation, but it is currently framed like a single-session inventory tool rather than a multi-user ordering service. To make it reliable for many users creating orders from phones, the core upgrade path is:

1. Move from inventory-first shared runtime state to a database-backed ordering workflow.
2. Add production-grade auth, role controls, and admin APIs.
3. Add server-side email delivery with a text-config fallback now, and admin-managed config later.
4. Deploy behind a real HTTPS web server and maintain proper observability/backups.
5. Keep/installable PWA behavior for iPhone and Android (no native app required).

This document turns that into a practical execution plan for a coding agent.

---

## 2) Current-State Findings (What must be fixed first)

### 2.1 Shared global draft-order state will break multi-user behavior
The current API stores all in-progress line items in one global `inventory_state.json` map (`INVENTORY_STATE`) and updates by item id only, without user/session separation. In a multi-user scenario, users will overwrite each other and clear each other’s carts on submit. `submit_order` also clears global state after one order succeeds. This is the biggest functional blocker for web deployment. 

### 2.2 Order “submission” writes only local Excel files
Current submit flow creates an `.xlsx` file in `orders/` and returns success; there is no email dispatch, no guaranteed delivery workflow, and no queue/retry strategy.

### 2.3 Authentication appears unfinished/inconsistent
There are wizard/auth toggle messages about username/PIN, but no active auth enforcement in `server.py` endpoints. This is risky once publicly hosted.

### 2.4 Config and ordering data storage are file-local only
Port, location, catalog categories, flags, and draft-order runtime state are local files. This is okay for prototype setup but fragile for concurrent access, backups, and cloud deployment.

### 2.5 PWA baseline exists, but production hardening is incomplete
A manifest and service worker are present, which is good for add-to-home-screen. However, to work reliably as an installable web app for many users, HTTPS hosting, caching/version policy, and update flow need hardening.

---

## 3) Target Ordering-System Behavior

### Must-have behavior
- Multiple users can create and submit orders concurrently without data collision.
- The system centers on draft orders, order review, and submission lifecycle states.
- Orders are persisted server-side with clear status lifecycle and auditability.
- Submission sends order output to configured email recipient(s).
- Recipient can be edited quickly via simple text file now.
- Later: admin panel can edit recipients, order catalog metadata, and English/Spanish master lists.
- App is publicly reachable over HTTPS (no Tailscale requirement).
- App is installable as a PWA on Android/iPhone.

### Nice-to-have behavior
- CSV/XLSX + PDF attachment options.
- Duplicate-order protection and confirmation IDs.
- Audit trail (who changed what, when).

---

## 4) Recommended Ordering-System Architecture (Practical + Incremental)

- **Backend**: FastAPI (keep).
- **Database**: PostgreSQL (preferred) for users, draft orders, submitted orders, line items, and config.
- **Async jobs**: small queue/worker (RQ/Celery/Arq) or background task for email retries.
- **Email**: SMTP provider (SES, SendGrid, Mailgun, or company SMTP).
- **Frontend**: current static app kept; progressively add auth/admin screens.
- **Deployment**: Docker + reverse proxy (Nginx/Caddy) + TLS (Let’s Encrypt).
- **Hosting**: any VPS/cloud (Render, Fly.io, Railway, DigitalOcean, AWS ECS/EC2, etc.).

---

## 5) Multi-Phase Implementation Plan

## Phase 0 — Stabilize & Prepare (1–3 days)
**Goal:** make the current codebase safe to evolve.

### Tasks
1. Create `/docs/architecture.md` and `/docs/api-contract.md` for current + target flows.
2. Add `.env` support and typed settings module (pydantic settings).
3. Add structured logging with request IDs.
4. Add health endpoints (`/health/live`, `/health/ready`) and version endpoint.
5. Add baseline tests for existing endpoints.

### Exit criteria
- CI can run lint + tests.
- Environment variables documented.
- No behavior change yet.

---

## Phase 1 — Multi-User Data Model (Core Fix) (3–7 days)
**Goal:** remove shared global-state risk.

### Data model (minimum)
- `users` (id, email/username, role, password hash/pin hash, active)
- `sessions` or JWT claims
- `draft_orders` (id, user_id, location_id, created_at, updated_at)
- `draft_order_items` (draft_order_id, item_id, qty, unit)
- `orders` (id, user_id, status, submitted_at, needed_by, rush, output_file_path)
- `order_items` (order_id, item snapshot fields)
- `settings` (key/value; include email recipient fallback)

### API changes
- Replace legacy inventory-update endpoints with authenticated draft-order writes centered on order creation.
- Replace global in-memory state with per-user draft retrieval.
- Make `submit_order` atomic transaction:
  - validate draft
  - create order + order_items snapshot
  - clear only that user’s draft

### Exit criteria
- Two users can edit at once without collisions.
- One user submitting does not reset another user’s work.

---

## Phase 2 — Email Delivery + Text File Config (2–4 days)
**Goal:** satisfy your immediate output requirement.

### Tasks
1. Add config file `config/order_recipients.txt` (one email per line, `#` comments allowed).
2. Add parser + validation at startup and refresh endpoint or periodic reload.
3. On submit, generate attachment(s): at least XLSX (current), optionally CSV.
4. Send email with subject/body template including location/date/rush/needed-by and order id.
5. Add retry policy + dead-letter logging when email fails.
6. Keep local file export as backup artifact.

### Exit criteria
- Updating recipient file changes delivery without redeploy.
- Failed email attempts are visible and retryable.

---

## Phase 3 — Public Deployment (No Tailscale) (2–5 days)
**Goal:** secure internet access.

### Tasks
1. Containerize app (API + worker + db + proxy in compose for first release).
2. Put behind Nginx/Caddy with TLS cert automation.
3. Set production domain and CORS policy to your real domain(s) only.
4. Add rate limiting and request size guards.
5. Add backups for DB + generated order files.

### Exit criteria
- Accessible via public HTTPS URL.
- Reliable restart and persistence.
- No dependency on Tailscale.

---

## Phase 4 — PWA Hardening for iPhone/Android (2–4 days)
**Goal:** smooth “downloadable web app” experience.

### Tasks
1. Finalize manifest (name, short_name, icons, display, theme/background).
2. Improve service worker caching strategy:
   - static assets cache-first with versioning
   - API network-first with graceful offline message
3. Add install prompt UX for Android + iOS add-to-home-screen instructions.
4. Add app update flow (new version detection, refresh prompt).

### Exit criteria
- Installable on modern Android browsers and Safari iOS add-to-home-screen flow.
- No broken UI when offline (clear message if submission requires network).

---

## Phase 5 — Admin Panel & Master List Management (5–10 days)
**Goal:** remove manual file editing over time.

### Admin features
- Manage recipient email list (replaces txt once approved).
- Upload/replace English & Spanish master files.
- Preview diff before publish (added/removed/renamed items).
- Category label/icon/color editor.
- Trigger safe re-index/rebuild of item catalog.

### Data safety
- Version master lists and keep rollback snapshot.
- Validate sheet structure before accepting upload.

### Exit criteria
- Non-technical admin can update catalog and recipients through UI.
- Rollback available for bad uploads.

---

## Phase 6 — Security/Compliance/Operations (parallel + ongoing)

### Security
- Real authentication + password reset flow.
- RBAC (`user`, `manager`, `admin`).
- CSRF strategy (if cookie auth), secure headers, strict CORS.
- Secrets in environment/secret manager (not repo files).

### Operations
- Metrics: requests, order submit success/failure, email success/failure.
- Alerting: repeated email failures, high error rates.
- Runbooks for common incidents.

---

## 6) Proposed Backlog for the Coding Agent (Ordered)

1. Introduce settings module + `.env.example`.
2. Add SQLAlchemy/Alembic + PostgreSQL schema for users/draft_orders/orders/order_items/settings.
3. Implement auth (session or JWT) and protect write endpoints.
4. Refactor draft-order update/submit flows to DB transactions.
5. Add recipient text file parser and outbound email service.
6. Add order status tracking and retry queue.
7. Write migration scripts and seed script.
8. Add automated tests (unit + API integration).
9. Add Docker + reverse proxy config and deploy docs.
10. Add PWA hardening + install UX.
11. Build admin panel for recipients/master-list updates.

---

## 7) Acceptance Criteria (What “done properly” means)

- **Concurrency:** 20+ simultaneous users can create/submit orders with no cross-user contamination.
- **Reliability:** ≥99% successful submissions in normal operation, with retry for transient email failures.
- **Security:** authenticated writes; admin-only config changes.
- **Usability:** installable web app behavior on Android/iPhone; mobile-first UX preserved.
- **Maintainability:** documented deploy, backup/restore, and upgrade path.

---

## 8) Immediate Risks & Mitigations

1. **Risk:** Email provider rejects attachments or rate limits.
   - **Mitigation:** queue + retries + fallback local archive + alerting.
2. **Risk:** Master list upload introduces invalid format.
   - **Mitigation:** strict validation + preview + rollback.
3. **Risk:** Public endpoint abuse.
   - **Mitigation:** auth, rate limiting, WAF/reverse-proxy controls.
4. **Risk:** Data loss from file-only storage.
   - **Mitigation:** DB persistence + backups.

---

## 9) Practical Launch Strategy

- **Release 1 (MVP public):** Phases 0–3 + minimal auth + email via txt config.
- **Release 2 (mobile polish):** Phase 4.
- **Release 3 (admin tooling):** Phase 5.
- **Release 4 (scale/hardening):** Phase 6 ongoing improvements.

This gets you public multi-user ordering quickly without waiting for the full admin panel.

---

## 10) Mapping to Existing Code (Why this plan is necessary)

- Current state writes inventory quantities to a shared file/in-memory state (`inventory_state.json` + `INVENTORY_STATE`) and updates via `/api/inventory/{category}/update`.
- Order submit currently writes an Excel file to `orders/` and clears shared state.
- Frontend already supports order flow and PWA basics (manifest + service worker registration), so we can preserve UI while upgrading backend architecture.
- There is no implemented email output path yet, and auth messaging in wizard does not match enforced API behavior.

