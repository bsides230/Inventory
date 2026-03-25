# Phase 2 — Email Delivery and Text Config

## Objective
Add reliable server-side order email delivery using a text-file recipient configuration, with retries and durable local artifacts.

## System Context
Phase 1 introduced DB-backed orders. This phase adds operational delivery of submitted orders without requiring admin UI yet.

## In-Scope Work
- Add `config/order_recipients.txt` format (one email per line, `#` comments allowed).
- Parse and validate recipients at startup, with refresh/reload mechanism.
- Generate XLSX attachment on submit (CSV optional).
- Send email with order metadata in subject/body (location/date/rush/needed-by/order ID).
- Add retry policy and dead-letter/error logging for failed sends.
- Keep local file export as backup artifact.

## Out-of-Scope / Non-Goals
- Admin UI for recipient management.
- Full-scale distributed queue infra unless required by current architecture.
- Public deployment hardening.

## Required Code Changes
- New config parser/validator and failure handling.
- Email delivery service abstraction and SMTP/provider integration.
- Submit pipeline hook to trigger email and track status/attempts.
- Logging/audit fields for delivery outcomes.

## Required Tests
- Recipient-file parser tests (valid/invalid/comment handling).
- Email send integration/unit tests with provider mocked.
- Retry behavior tests for transient failures.
- Submit flow test ensuring local artifact persists regardless of email outcome path.

## Deliverables
- Working recipient text-config based delivery path.
- Observable retry/failure handling.
- Attachment generation integrated with submit flow.

## Definition of Done
- Editing `order_recipients.txt` changes recipients without redeploy.
- Failed email attempts are visible, diagnosable, and retryable.
- Order artifacts remain available locally as backup.

## Notes for the Coding Agent
- Treat email as an order-delivery mechanism, not optional UX sugar.
