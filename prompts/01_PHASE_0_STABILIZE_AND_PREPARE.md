# Phase 0 — Stabilize & Prepare

## Objective
Create a safe baseline for iterative migration by adding architecture docs, typed settings, structured logs, health/version endpoints, and baseline tests **without changing core runtime behavior**.

## System Context
The codebase currently has a working FastAPI + static web foundation, but later phases will introduce DB-backed ordering and auth hardening. This phase must prepare the code so later changes are safer and easier to validate.

## In-Scope Work
- Add/update architecture documentation for current and target ordering flow.
- Add `.env` support and typed settings module (pydantic settings or equivalent).
- Add structured logging with request IDs across API requests.
- Add `/health/live`, `/health/ready`, and a version endpoint.
- Add baseline tests covering existing endpoints and new health/version endpoints.
- Ensure CI-equivalent local checks can run lint + tests.

## Out-of-Scope / Non-Goals
- No database migration or schema introduction yet.
- No auth model redesign yet.
- No behavior changes to order creation/submission flow.
- No deployment topology changes yet.

## Required Code Changes
- Add `docs/architecture.md` and `docs/api-contract.md` reflecting current and target state.
- Introduce settings/config module and `.env.example` documentation.
- Integrate request ID correlation into logs and request lifecycle.
- Implement health/readiness/version endpoints.
- Add/update tests and test fixtures for baseline behavior.

## Required Tests
- Automated tests for health/live/readiness/version endpoints.
- Regression tests for existing public/order endpoints to ensure no behavior regression.
- Static checks/lint configured and passing if already present.

## Deliverables
- New/updated docs for architecture and API contract.
- Working typed settings loading from environment.
- Structured logs including request IDs.
- Operational endpoints for liveness/readiness/version.
- Passing baseline test suite.

## Definition of Done
- All new tests pass.
- Existing endpoint behavior remains functionally unchanged.
- Team can run lint + tests locally in a repeatable way.
- Environment variables are documented and discoverable.

## Notes for the Coding Agent
- Make minimal, low-risk edits.
- Prefer additive changes over refactors in this phase.
- Preserve ordering-platform framing in docs and naming.
