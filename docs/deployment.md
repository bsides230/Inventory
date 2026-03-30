# Public Deployment Runbook (Phase 3)

## Stack
- `api`: FastAPI app container.
- `proxy`: Caddy reverse proxy with automated HTTPS certificates.
- `backup_worker`: periodic backup job for config, drafts, and log files and generated order files.

## Prerequisites
1. Public DNS record for your domain pointing to the host.
2. Docker Engine + Docker Compose plugin installed.
3. Host ports `80` and `443` open.

## Environment Setup
Create `.env` in repo root:

```env
APP_DOMAIN=orders.example.com
APP_ENV=production
LOG_LEVEL=INFO
APP_VERSION=0.1.0
AUTH_JWT_SECRET=<strong-random-secret>
AUTH_JWT_ALGORITHM=HS256
ORDER_RECIPIENTS_FILE=config/order_recipients.txt
SMTP_HOST=<smtp-host>
SMTP_PORT=587
SMTP_USERNAME=<smtp-user>
SMTP_PASSWORD=<smtp-password>
SMTP_USE_TLS=true
SMTP_SENDER_EMAIL=inventory@example.com
EMAIL_RETRY_ATTEMPTS=3
EMAIL_RETRY_DELAY_SECONDS=1
EMAIL_DEAD_LETTER_LOG=logs/order_email_dead_letter.log
CORS_ALLOWED_ORIGINS=https://orders.example.com
MAX_REQUEST_BODY_BYTES=1048576
RATE_LIMIT_MAX_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
BACKUP_RETENTION_DAYS=14
BACKUP_INTERVAL_SECONDS=3600
```

## Deploy
1. Build and start:
   - `docker compose up -d --build`
3. Verify services:
   - `docker compose ps`
   - `curl -fsS https://$APP_DOMAIN/health/live`
   - `curl -fsS https://$APP_DOMAIN/health/ready`

## Backup Strategy
- The `backup_worker` service runs `scripts/backup.sh` every hour (configurable).
- Backups are written under `/app/backups/<timestamp>/` inside `backups_data` volume.
- Contents:
  - `orders.tar.gz`
- Retention: directories older than `BACKUP_RETENTION_DAYS` are removed.

## Restore Drill
1. Stop API and DB containers:
   - `docker compose stop api ipc_worker backup_worker`
2. Restore order artifacts from backup:
   - `docker compose run --rm -e BACKUP_DIR=/app/backups backup_worker ./scripts/restore.sh <timestamp>`
4. Restart services:
   - `docker compose start proxy api ipc_worker backup_worker`
5. Validate with live/ready endpoints and a test order submission.

## Abuse Protection
- CORS is allow-list based via `CORS_ALLOWED_ORIGINS`.
- Request body size guard rejects payloads above `MAX_REQUEST_BODY_BYTES` with `413`.
- In-memory IP rate limiter rejects excessive requests with `429`.

## Operational Notes
- Persisted volumes: `postgres_data`, `orders_data`, `logs_data`, `backups_data`, `caddy_data`.
- No Tailscale dependency is required for normal client access.
