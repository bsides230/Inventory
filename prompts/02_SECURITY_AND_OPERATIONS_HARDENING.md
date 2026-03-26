# Security and Operations Hardening

## Objective
Implement the remaining high-value security and operational hardening tasks that are still pending after stabilization.

## Why this prompt exists now
The audit identified unresolved Phase 6-class hardening gaps (especially JWT claim policy and deeper ops readiness/validation). These must be closed before declaring the platform ready for broader rollout.

## System context
Core ordering functionality is implemented and stabilized by Prompt 01. This prompt tightens authentication guarantees, readiness/operational safeguards, and deployment-risk controls without reworking completed business flows.

## In-scope work
- Enforce JWT expiration (`exp`) validation.
- Add optional issuer (`iss`) and audience (`aud`) enforcement via settings-driven configuration.
- Strengthen readiness/ops validation beyond basic file checks (building on Prompt 01 readiness improvements).
- Implement additional security/ops hardening items still truly pending and compatible with current architecture.
- Update deployment/security documentation and tracker/build notes for all hardening changes.

## Out-of-scope / non-goals
- Re-implementing already completed and validated security controls.
- Introducing unrelated product features.
- Large-scale architecture replacement (e.g., complete async job system) unless explicitly required to close a hardening finding.

## Required code changes
- Auth layer changes for stricter JWT claim checks with clear config defaults.
- Tests and settings/docs updates for claim validation behavior and failure modes.
- Operational/readiness hardening changes (application and/or deployment artifact layer) tied to open audit items.
- Documentation updates (`docs/deployment.md`, `docs/api-contract.md`, or other impacted docs).

## Required tests
- Positive/negative auth tests for `exp`, and optional `aud`/`iss` when configured.
- Readiness/ops tests proving expected behavior under degraded dependencies.
- Regression tests for write-protected endpoints and submit flow under new auth policy.

## Deliverables
- Hardened auth and ops behavior with evidence-backed tests.
- Updated operational/security docs and execution tracking artifacts.
- Explicit deferred-risk list for any hardening items intentionally postponed.

## Definition of done
- JWT claim policy is enforced as specified and covered by tests.
- Readiness/ops checks provide materially better deployment signal quality.
- No regression in core ordering/auth behavior.
- Tracker/build notes/docs are aligned with implemented hardening state.

## Notes for the coding agent
- Keep hardening configurable and environment-safe.
- Preserve backward compatibility where possible, but prioritize secure defaults.
- Record exact config requirements and migration notes for operators.
