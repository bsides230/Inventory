# Phase 3 — Public Deployment (No Tailscale)

## Objective
Deploy the ordering platform securely on public HTTPS infrastructure with persistence, restart reliability, and basic abuse protections.

## System Context
Prior phases delivered core multi-user ordering and email output. This phase makes the system internet-accessible and operationally stable.

## In-Scope Work
- Containerize app components (API + worker + DB + reverse proxy baseline).
- Configure TLS automation via Nginx or Caddy.
- Restrict CORS to production domain(s).
- Add rate limiting and request size guards.
- Add backup strategy for DB and generated order files.
- Document deployment and recovery workflow.

## Out-of-Scope / Non-Goals
- Full enterprise orchestration (Kubernetes, etc.) unless already standard in repo.
- Admin feature expansion beyond deployment requirements.

## Required Code Changes
- Docker/compose and environment configuration.
- Reverse-proxy configuration with HTTPS.
- App-level security middleware/config for CORS/rate limits/body size.
- Backup scripts/docs and restore validation steps.

## Required Tests
- Container startup smoke tests.
- HTTPS/proxy routing verification.
- Backup/restore drill (or scripted validation).
- Basic abuse guard checks (rate limit/request size).

## Deliverables
- Public HTTPS deployable stack.
- Documented operational startup and backup procedures.

## Definition of Done
- Service reachable via public HTTPS URL.
- Data and order artifacts persist across restart.
- No Tailscale dependency remains for core access.

## Notes for the Coding Agent
- Keep deployment artifacts simple and reproducible for MVP operations.
