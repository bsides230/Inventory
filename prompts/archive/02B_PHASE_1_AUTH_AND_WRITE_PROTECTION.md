# Phase 1B — Auth and Write Protection

## Objective
Implement authentication identity propagation and enforce write protection on draft/order APIs.

## System Context
This sub-phase builds on schema/models and establishes safe per-user writes before submit transaction overhaul.

## In-Scope Work
- Implement/complete auth mechanism (session or JWT).
- Add user identity context to request handling.
- Protect write endpoints so only authenticated users can mutate draft/order state.
- Add role-aware scaffolding if needed for future admin boundaries.

## Out-of-Scope / Non-Goals
- No final submit transaction rewrite yet.
- No admin panel UI.
- No deployment hardening.

## Required Code Changes
- Auth middleware/dependencies.
- Endpoint guards and authorization checks.
- Auth-related settings and docs updates.

## Required Tests
- Auth success/failure API tests.
- Unauthorized write attempts return expected error codes.
- User isolation tests on draft update routes.

## Deliverables
- Protected write surface for ordering APIs.

## Definition of Done
- Anonymous users cannot mutate ordering data.
- Authenticated users can only mutate their own draft context.

## Notes for the Coding Agent
- Keep auth implementation pragmatic and compatible with Phase 3 deployment.
