# Database & Persistence Audit — Falcones Pizza Inventory

## Executive Summary

The app has **two parallel persistence systems**:

1. **SQLAlchemy ORM → SQLite (dev) / PostgreSQL (prod):** Used exclusively for user identity, order drafts, and submitted order records.
2. **Plain flat files:** Used for everything else — inventory item data, category config, email settings, location config, admin password, branding, UI labels, and order export artifacts (XLSX).

**What is unnecessary for a rebuild toward file-only:**
- The entire `db/` package (models, repositories, database, auth)
- The `alembic/` migration chain
- PostgreSQL container and `backup_worker` service in `docker-compose.yml`
- `psycopg2-binary` dependency
- JWT-based auth (the only reason users exist in the DB)

**What must be rebuilt:**
- Draft storage (currently DB-backed per-user state)
- Order submission record (currently written to DB + XLSX)
- User identity tracking (currently a DB table seeded by JWT claims)

**What is already file-based and can be kept as-is:**
- All of `data/*.json` (inventory items)
- All of `config/*.txt` / `config/*.json` (settings, recipients, labels, branding)
- `categories.json`
- XLSX order export artifacts
- Dead-letter log

---

## 1. Persistence Map

| File / System | Purpose | Read | Write | Runtime-Critical |
|---|---|---|---|---|
| `inventory.db` | SQLite DB: users, drafts, orders | All auth/draft/order routes | Auth upsert, draft mutations, order submit | **Yes** (currently) |
| `data/*.json` (12 files) | Inventory items per category | `GET /api/inventory/{category}`, startup | `POST /api/admin/rebuild-inventory`, `POST /api/admin/upload-master` | **Yes** |
| `categories.json` | Category icons, colors, labels | Nearly every inventory route | `POST /api/admin/rebuild-inventory`, `POST /api/admin/upload-master` | **Yes** |
| `config/locations.txt` | PIN → location name map | Auth PIN route, admin routes | `POST /api/admin/locations` | **Yes** |
| `config/admin_password.txt` | Admin login credential | `POST /api/admin/login` | `POST /api/admin/password` | **Yes** |
| `config/email_settings.txt` | SMTP host/port/credentials | Order submit, admin routes | `POST /api/admin/email-settings` | **Yes** (if email used) |
| `config/order_recipients.txt` | Email recipient list | Order submit | `POST /api/admin/recipients` | **Yes** (if email used) |
| `config/category_order.json` | Display order of categories | `GET /api/categories` | `POST /api/admin/category-order` | **Yes** |
| `config/ui_labels.json` | UI label overrides | `GET /api/ui-labels` | `POST /api/admin/ui-labels` | No (defaults work without it) |
| `config/branding.json` | Logo/color branding | `GET /api/branding` | `POST /api/admin/branding` | No (defaults work without it) |
| `item master/Master.xlsx` | Source of truth for all items | `update_inventory_data.py` on startup + upload | `POST /api/admin/upload-master` | Indirectly (feeds `data/*.json`) |
| `item master/*.bak` | Auto-backup of Excel on upload | Never read at runtime | Created on each upload | No |
| `orders/*.xlsx` | Order export artifacts (emailed) | `email_delivery.py` reads bytes for attachment | `POST /api/submit_order` | Required for email; not for record-keeping |
| `logs/order_email_dead_letter.log` | Failed email delivery payloads | Never read at runtime | `email_delivery.py` on SMTP failure | No |
| `location.txt` | Single legacy location label | `GET /api/status` | Never written at runtime | No (superseded by `config/locations.txt`) |
| `port.txt` | Port for local dev | Startup only | Never | No |
| `inventory_data.json` | Legacy item data (25 KB) | Only by legacy scripts (`scripts/create_masters.py`, `scripts/translate.py`) | Never | **No — dead for runtime** |
| `inventory_state.json` | Unknown legacy state (`{}`) | **Nothing at runtime** | **Nothing at runtime** | **No — dead code** |
| `db/` package | ORM models, repositories, session management | All auth + draft + order routes | Same | **Yes** (currently) |
| `alembic/` | Schema migration chain | Dev/deploy tooling only | Dev/deploy tooling only | No (runtime doesn't run migrations) |
| `scripts/backup.sh` | Archives postgres volume + orders dir | At deploy/cron | Writes to `/app/backups/` | No |
| `scripts/restore.sh` | Restores orders from backup | Manually | Writes to `/app/orders/` | No |
| `scripts/bootstrap_dev_db.py` | Seeds dev SQLite DB | Dev only | Dev only | No |
| `scripts/create_masters.py` | Generates XLSX from legacy JSON | One-time migration | One-time migration | **No — legacy utility** |

---

## 2. Database Usage Verdict

### PostgreSQL
**Verdict: UNUSED at runtime. Deployment-only infrastructure.**

The `DATABASE_URL` env var in the running app is `sqlite:///./inventory.db`. The PostgreSQL container is defined in `docker-compose.yml` with a default URL, but the app has been running against SQLite. `psycopg2-binary` is installed but not exercised. The backup worker archives the postgres data volume, which contains nothing meaningful given the current `DATABASE_URL` config.

### SQLite (`inventory.db`)
**Verdict: REQUIRED by the current app, but only for three features:**
1. User identity (JWT → DB upsert on every auth call)
2. Order drafts (per-user, multi-item, multi-draft state)
3. Submitted order records (authoritative order history + delivery tracking)

The `AppSetting` table is **unused** — defined in models and created by migration, but never read or written anywhere in the application.

---

## 3. Rebuild Recommendation — Move to Plain Files

### Features that can move to plain files with no loss

| Feature | Current | File-based replacement |
|---|---|---|
| Category config | `categories.json` (already a file) | Keep as-is |
| Inventory items | `data/*.json` (already files) | Keep as-is |
| Email settings | `config/email_settings.txt` (already a file) | Keep as-is |
| Recipients | `config/order_recipients.txt` (already a file) | Keep as-is |
| Locations | `config/locations.txt` (already a file) | Keep as-is |
| Admin password | `config/admin_password.txt` (already a file) | Keep as-is |
| Branding/labels | `config/branding.json`, `config/ui_labels.json` | Keep as-is |
| Order export | `orders/*.xlsx` (already files) | Keep as-is |

### Features that need a decision before going file-only

| Feature | Current DB behavior | Simplest file replacement | Tradeoff |
|---|---|---|---|
| **Draft state** | Per-user rows in `order_drafts` + `order_draft_items`; supports multiple named drafts per user | Single `drafts/{session_token}.json` per session | Lose per-user identity; drafts become session-scoped, not user-scoped |
| **Order history** | Full relational record: `orders` + `order_items`, with delivery tracking | Append `orders/submitted/{timestamp}_{pin}.json` on submit | Lose queryable history; admin aggregation becomes a directory scan |
| **User identity** | `users` table keyed by JWT `sub`; enables per-user draft isolation and order attribution | Replace with PIN-based session identity (already collected on login) | Lose cross-session draft persistence; drafts live only as long as the session |
| **Order frequency hints** | `OrderRepository.get_item_frequencies()` aggregates past orders to pre-fill quantities | Scan `orders/submitted/*.json` for same PIN's history | Slightly slower on large datasets; trivial for restaurant scale |
| **Delivery status tracking** | `orders.delivery_status`, `delivery_attempts`, `delivered_at` columns | Append a `{order_id}_delivery.json` sidecar file, or fold into the order JSON | Slightly more complex to query, but workable |

---

## 4. Cleanup Plan (If Going File-Only)

### Remove entirely
- `db/` directory (`database.py`, `models.py`, `repositories.py`, `auth.py`, `__init__.py`)
- `alembic/` directory + `alembic.ini`
- `inventory.db` (delete from git too — it should never have been committed)
- `scripts/bootstrap_dev_db.py`
- `scripts/backup.sh` (replace with `cp -r orders/ backups/` if needed)
- `scripts/restore.sh`
- `scripts/create_masters.py` (legacy one-time utility)
- `inventory_data.json` (dead for runtime; only used by legacy scripts being removed)
- `inventory_state.json` (dead code)

### Remove from `requirements.txt`
```
sqlalchemy
alembic
psycopg2-binary
```
Keep: `pandas`, `openpyxl`, `fastapi`, `uvicorn`, `python-jose` (if JWT retained for admin), `python-multipart`

### Remove from `docker-compose.yml`
- `db` service (PostgreSQL container)
- `backup_worker` service
- `postgres_data` named volume
- `DATABASE_URL` env var (no longer needed)

### Remove from `server.py`
- All imports from `db.*`
- `get_optional_authenticated_user`, `get_required_authenticated_user` (replace with PIN session check)
- `InMemoryRateLimiter` per-user rate limiting (or simplify to per-IP)
- All `with get_session(...)` blocks
- References to `settings.database_url`

### Keep
- All flat-file read/write helpers (`load_locations`, `save_email_settings`, etc.)
- `update_inventory_data.py` — this is the Excel-to-JSON pipeline and is actively used
- `services/email_delivery.py` — already file-based (reads XLSX, writes log)
- `services/recipients.py` — already file-based

---

## 5. Risk List

| Risk | Severity | Detail |
|---|---|---|
| **`inventory.db` committed to git** | High | Binary SQLite file in git root. Any DB change creates binary diffs. Could expose user data or order history in git log. Should be added to `.gitignore` and deleted from history. |
| **Draft loss on session change** | Medium | If DB is removed and drafts become session-scoped, users lose drafts when they close the browser or PIN expires. Currently drafts persist across sessions via the `users` table. |
| **Order history loss** | Medium | Admin aggregation (`GET /api/admin/aggregation`) queries `orders` + `order_items` with joins and frequency counts. Moving to file scans requires rebuilding this logic. |
| **Migrations not auto-run** | Medium | No `alembic upgrade head` in Dockerfile CMD. If a new migration is added, the app starts against a stale schema. Currently hidden by the fact that `inventory.db` is committed at head revision. |
| **`AppSetting` table is dead code** | Low | The table is created but unused. No risk to remove it, but any future code that assumed it was available would break. |
| **`InMemoryRateLimiter` is non-durable** | Low | Rate limit state resets on restart. Abuse window reopens after every deploy. Not a DB dependency, but worth noting for rebuild. |
| **Dead-letter log not backed up** | Low | `logs/order_email_dead_letter.log` is in a Docker volume but `scripts/backup.sh` only backs up `orders/` and the postgres data dir. Failed email payloads are silently lost on volume destruction. |
| **`location.txt` vs `config/locations.txt`** | Low | Two different location storage mechanisms exist. `GET /api/status` reads the legacy `location.txt` single-value file. The actual location management uses `config/locations.txt` (multi-location, PIN-based). `location.txt` is a stale artifact. |
| **Test DB files not gitignored** | Low | `test_flow.db` and `test_auth.db` are created in the repo root during test runs. Not in `.gitignore`. Could be accidentally committed. |
| **XLSX write / DB commit ordering** | Low | In `submit_order`, the XLSX file is written between two DB sessions. If the process crashes after the file write but before the second session (delivery status update), the order is in the DB but has no delivery status. This is recoverable but creates a gap. |

---

## 6. Minimum Viable Rebuilt Backend

**Architecture: PIN-scoped sessions + flat files. No database.**

```
config/
  locations.txt          # PIN → location name (existing)
  admin_password.txt     # admin credential (existing)
  email_settings.txt     # SMTP config (existing)
  order_recipients.txt   # email recipients (existing)
  category_order.json    # display order (existing)
  ui_labels.json         # label overrides (existing)
  branding.json          # branding (existing)

data/
  {category}.json        # inventory items (existing, generated from Excel)

item master/
  Master.xlsx            # source of truth for items (existing)

drafts/
  {pin}_{session_id}.json  # one draft file per active session
                           # written on every item update
                           # deleted on order submit

orders/
  submitted/
    {timestamp}_{pin}.json   # full order record on submit (replaces DB)
    {timestamp}_{pin}.xlsx   # email attachment (existing)

logs/
  order_email_dead_letter.log   # existing append-only JSONL
```

**Auth model:** PIN lookup against `config/locations.txt`. Session token = signed JWT or simply `{pin}_{timestamp}` HMAC. No user table.

**Draft model:** Single active draft per PIN+session. Stored as a JSON file. No named multi-draft support (or implement as multiple files with a `{pin}_{draft_name}.json` pattern).

**Order submission:** Write JSON record to `orders/submitted/`, write XLSX to same dir, email XLSX. No DB involved.

**Admin aggregation:** Scan `orders/submitted/*.json` at request time. For restaurant scale (hundreds of orders), a directory scan is trivially fast. Add an in-memory cache with a file-mtime invalidation key if needed.

**Item frequency hints:** Same scan — count item occurrences per PIN across submitted order JSONs.

**What this removes:** SQLAlchemy, Alembic, psycopg2, the entire `db/` package, PostgreSQL container, backup_worker, and 3 migration files.

**What this keeps:** Every existing flat-file helper in `server.py`, `update_inventory_data.py`, `services/email_delivery.py`, `services/recipients.py`, and all `config/` and `data/` files. The rebuild is additive replacement of the DB layer only.
