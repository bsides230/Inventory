# Stabilization and Audit Fixes

## Objective
Resolve the highest-priority stabilization and governance gaps identified by the implementation audit before further expansion.

## Why this prompt exists now
Audit results show core migration work is mostly complete, but known defects and process drift remain. This prompt fixes correctness and control-plane issues that block confident continuation.

## System context
Current architecture is DB-backed for draft/order flows with authenticated writes, email delivery attempts, and deployment/PWA assets in place. Remaining blockers are targeted defects and reliability gaps rather than missing foundational architecture.

## In-scope work
- Fix recipient reload fragility/bug so recipient updates are reliably detected.
- Make pytest discovery deterministic from repository root.
- Reconcile prompt execution tracking with implementation evidence.
- Refresh stale architecture documentation to match current DB-backed behavior.
- Add real DB connectivity validation to readiness checks.
- Address any small, high-value stabilization tasks explicitly called out in the audit that fit this scope.

## Out-of-scope / non-goals
- Broad security hardening beyond stabilization essentials (handled in Prompt 02).
- Net-new feature work unrelated to audit stabilization findings.
- Large refactors not needed to close audited defects.

## Required code changes
- Recipient reload logic in relevant service/module(s), with deterministic behavior under rapid/same-size file edits.
- Test discovery configuration (`pytest.ini` or equivalent) so root `pytest` run collects intended test set.
- `/health/ready` (or equivalent readiness path) enhancement to include DB readiness checks.
- `docs/architecture.md` updates reflecting current real system behavior.
- `prompts/EXECUTION_STATUS.md` and `build_notes.md` updates aligned to evidence.

## Required tests
- Add/adjust unit tests validating recipient reload behavior and regression coverage.
- Validate deterministic root-level pytest collection behavior.
- Add/adjust readiness tests to cover DB availability scenarios (success + failure path expectations).
- Run full scoped test suite required by project conventions.

## Deliverables
- Code changes closing each stabilization finding.
- Updated docs and tracking artifacts.
- Clear list of resolved items and any explicitly deferred items with rationale.

## Definition of done
- Recipient reload bug no longer reproducible under test.
- Root `pytest` collection is deterministic and green (or documented if external limitation).
- Readiness endpoint includes real DB check with tests.
- Architecture and tracker/build notes reflect implemented reality.

## Notes for the coding agent
- Prefer minimal, robust fixes over broad redesign.
- Keep each fix traceable to an audit finding.
- If an item cannot be fully closed, document exact residual risk and follow-up prompt need.
