# Phase 1 — Multi-User Data Model (Core Fix)

## Objective
Eliminate shared global state and implement a multi-user, authenticated draft-order workflow backed by a transactional database model.

## System Context
Current draft state is shared and unsafe for concurrent users. This phase is the core migration from single-session behavior to per-user order lifecycle behavior.

## In-Scope Work
- Introduce DB-backed models for users, drafts, orders, items, and settings.
- Implement auth/session/JWT integration sufficient to identify the current user for write operations.
- Replace shared draft storage with per-user draft retrieval and mutation.
- Convert submit flow into an atomic transaction:
  1) validate draft;
  2) persist order + order item snapshots;
  3) clear only submitting user draft.
- Update API contracts and tests accordingly.

## Out-of-Scope / Non-Goals
- Full production email delivery pipeline (Phase 2).
- Public internet deployment hardening (Phase 3).
- Admin panel UI for managing catalog/recipients (Phase 5).

## Required Code Changes
- Add schema/migrations for minimum entities:
  - `users`, `draft_orders`, `draft_order_items`, `orders`, `order_items`, `settings`.
- Replace legacy global draft mutation paths with authenticated per-user draft endpoints.
- Add auth guards to order write/submit endpoints.
- Add transaction boundaries and rollback-safe error handling on submit.
- Add migration/seed support needed for local/dev validation.

## Required Tests
- Two-user concurrency tests proving no cross-user draft contamination.
- Submit flow test proving one user submit does not clear another user’s draft.
- Auth tests proving unauthenticated/unauthorized writes are blocked.
- Migration smoke tests (up/down or equivalent validation path).

## Deliverables
- Database-backed draft/order lifecycle.
- Authenticated write path for draft and submit actions.
- Updated API docs/tests for new contract.
- Removal (or deprecation) of shared global draft behavior.

## Definition of Done
- Multiple users can create/update drafts concurrently without collisions.
- Submission is atomic and user-isolated.
- Legacy global-state behavior is no longer active for order writes.
- Test suite includes explicit multi-user and auth coverage.

## Notes for the Coding Agent
- Keep the product language centered on ordering workflow.
- Favor incremental migration adapters only if necessary; remove dead paths when safe.
- If Phase 1 is too large for one pass, execute 02A → 02B → 02C.
