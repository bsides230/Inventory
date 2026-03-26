# Phase 1A — Schema and Models Foundation

## Objective
Create the foundational relational schema and ORM models for multi-user ordering without yet finalizing endpoint rewrites.

## System Context
This sub-phase exists to reduce drift and isolate data-layer risk before auth and API behavior changes.

## In-Scope Work
- Add DB engine/session wiring.
- Add schema migrations for users/drafts/orders/items/settings.
- Add ORM/domain models and basic repository access patterns.
- Add seed/dev bootstrap flow for local environment.

## Out-of-Scope / Non-Goals
- No complete API route migration yet.
- No auth enforcement rollout yet.
- No email dispatch work.

## Required Code Changes
- Migration files and model definitions for core entities.
- Configuration plumbing for DB URL and migration commands.
- Minimal data-access abstractions needed by upcoming sub-phases.

## Required Tests
- Migration apply/rollback smoke test.
- Model-level CRUD tests for draft/order entities.

## Deliverables
- Working schema + models committed and test-covered.

## Definition of Done
- Fresh setup can migrate DB and persist/retrieve core ordering entities.

## Notes for the Coding Agent
- Keep naming aligned with ordering lifecycle semantics.
