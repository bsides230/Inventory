# brands Pizza Inventory

A Progressive Web Application (PWA) for managing inventory and submitting orders at brands Pizza restaurant locations.

## Architecture

- **Backend**: FastAPI (Python) served via Uvicorn (dev) / Gunicorn (production)
- **Frontend**: Vanilla JS SPA served as static files by FastAPI from the `web/` directory
- **Database**: PostgreSQL (provided by Replit runtime via `DATABASE_URL`)
- **Migrations**: Alembic (runs automatically or manually with `alembic upgrade head`)

## Project Structure

- `server.py` — Main FastAPI app entry point, API endpoints, middleware
- `web/` — Frontend static files (HTML, CSS, JS, PWA manifest, service worker)
- `db/` — SQLAlchemy models, repositories, auth (JWT)
- `alembic/` — Database migration scripts
- `services/` — Business logic (email delivery, recipient management)
- `data/` — Inventory category JSON files
- `config/` — Configuration files (order recipients list)
- `scripts/` — Utility scripts for backup, restore, bootstrapping
- `tests/` — pytest test suite

## Configuration

Environment variables are set via Replit Secrets. Key settings:

- `DATABASE_URL` — PostgreSQL connection string (provided by Replit)
- `AUTH_JWT_SECRET` — JWT signing secret
- `CORS_ALLOWED_ORIGINS` — Allowed CORS origins (set to `*` for dev)
- `SMTP_*` — Email delivery configuration
- `ORDER_RECIPIENTS_FILE` — Path to recipient list file

## Running Locally

The app reads its port from `port.txt` (currently set to 5000).

```bash
python server.py
```

## Deployment

Configured for **autoscale** deployment using Gunicorn:

```
gunicorn --bind=0.0.0.0:5000 --reuse-port --workers=2 server:app
```

## Key Features

- Browse inventory by category (bakery, meats, produce, etc.)
- Maintain draft orders per user (persisted in database)
- Submit orders as Excel exports emailed to configured recipients
- PWA with offline support via service worker
- JWT-based authentication
- Multi-language support (English/Spanish)
