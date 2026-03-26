# Phase 1C — Draft and Submit Transaction Flow

## Objective
Finalize per-user draft-order workflow and atomic submission behavior.

## System Context
This sub-phase assumes schema and auth protections are already in place.

## In-Scope Work
- Replace legacy shared draft mutation and retrieval with per-user DB-backed flow.
- Implement atomic submit transaction with snapshot creation in `orders`/`order_items`.
- Clear only the current user draft after successful submit.
- Keep local artifact behavior compatible with next phase email integration.

## Out-of-Scope / Non-Goals
- Full email delivery/retry logic (Phase 2).
- Public deployment and infra hardening.

## Required Code Changes
- Service-layer transaction orchestration for submit.
- Endpoint contract updates for draft get/update/submit.
- Deprecate/remove shared-state paths.

## Required Tests
- Multi-user submit isolation tests.
- Transaction rollback tests on validation/persistence failure.
- End-to-end API test for draft-to-submit lifecycle.

## Deliverables
- Fully migrated draft and submit flow.

## Definition of Done
- No cross-user contamination.
- Submit is atomic and traceable.

## Notes for the Coding Agent
- Keep migration diff focused on ordering flow correctness.
