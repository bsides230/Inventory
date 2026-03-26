# Final Test, Verification, and Audit Pass

## Objective
Perform a strict end-to-end verification pass that validates completion and quality of all remaining-work prompts, then produce a final readiness report.

## Why this prompt exists now
Remaining implementation work is small but high impact. A dedicated, explicit final audit pass is required to prevent tracker drift, hidden regressions, and false completion signals.

## System context
By this phase, stabilization and security/operations hardening prompts should be complete. This prompt does not add net-new features; it validates reality against prompts, code, tests, docs, and deployment artifacts.

## In-scope work
- Verify every active remaining-work prompt has corresponding implementation and evidence.
- Cross-check codebase state against:
  - `prompts/EXECUTION_STATUS.md`
  - `build_notes.md`
  - prompt deliverables and definitions of done.
- Re-run test suites and required checks from repository root.
- Inspect and validate docs/deployment/auth/email/migrations/readiness/security-related updates for consistency.
- Identify remaining gaps, regressions, risky partial implementations, or tracker mismatches.
- Produce final report at `docs/final_verification_report.md`.

## Out-of-scope / non-goals
- New feature development except minimal corrective fixes necessary to resolve verification-discovered regressions.
- Silent deferral of unresolved issues.

## Required code changes
- Only verification-related updates are expected:
  - report generation,
  - tracker/build-notes reconciliation,
  - minimal correction patches if required by failing verification gates.

## Required tests
- Run full project test command(s) expected for CI/review from repository root.
- Re-run focused tests covering stabilization and security hardening changes.
- Run any lint/static/type/migration checks required by current repo standards.
- Document pass/fail status and root cause for any failures.

## Deliverables
- `docs/final_verification_report.md` containing:
  - verification scope,
  - commands executed,
  - results,
  - evidence of prompt-by-prompt completion,
  - open issues/risk acceptance decisions,
  - release-readiness conclusion.
- Updated `prompts/EXECUTION_STATUS.md` and `build_notes.md` reflecting final audited state.

## Definition of done
- Final report exists and is evidence-based.
- Prompt completion claims match verifiable code/tests/docs.
- Any unresolved issues are explicitly documented with severity and next actions.
- Go/no-go readiness recommendation is clearly stated.

## Notes for the coding agent
- Be stricter than normal implementation prompts; this is an audit gate.
- Do not mark complete on partial evidence.
- If a prompt deliverable is missing, record it as a gap and fail readiness accordingly.
