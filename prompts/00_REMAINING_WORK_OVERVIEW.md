# Remaining Work Prompt System Overview (Reset Pass)

## Objective
Define the second-pass, remaining-work-only prompt sequence after the implementation audit, and establish this sequence as the active control surface for the repo.

## Why this prompt exists now
The original migration prompt chain delivered most core platform capabilities, but the audit found unresolved stabilization, governance, and security/operations hardening issues. The prior prompt sequence and tracker state drifted from implementation reality (notably around Phase 5 status), so this reset creates an accurate execution path.

## System context
- Core ordering platform phases (stabilization baseline, DB-backed draft/order flow, auth write protection, email delivery, deployment artifacts, and PWA hardening) are substantially implemented.
- Audit findings identified unresolved issues: recipient reload fragility, non-deterministic root pytest collection, stale architecture docs, shallow readiness checks, incomplete JWT claim enforcement, and tracker integrity drift.
- This prompt system intentionally excludes redoing completed migration phases except where revalidation is required in the final verification pass.

## In-scope work
- Execute remaining work in this order:
  1. `01_STABILIZATION_AUDIT_FIXES.md`
  2. `02_SECURITY_AND_OPERATIONS_HARDENING.md`
  3. `99_FINAL_TEST_AND_VERIFICATION.md`
- Keep `prompts/EXECUTION_STATUS.md` synchronized with real implementation state at every step.
- Use final verification as a strict go/no-go audit for next-stage planning.

## Out-of-scope / non-goals
- Re-implementing completed migration phases.
- Introducing unrelated new feature scope.
- Marking tasks complete based on intent without code/test evidence.

## Required code changes
- Prompt/tracker/docs changes needed to reflect the reset sequence.
- No functional implementation work is required by this overview itself.

## Required tests
- None required for this control document alone.
- Subsequent prompts define required tests.

## Deliverables
- A concise, accurate remaining-work sequence.
- Explicit warning that tracker state must match verifiable implementation.
- Final prompt designated as dedicated verification/testing/audit.

## Definition of done
- Remaining-work sequence is clear, ordered, and limited to unresolved audit-backed items.
- Final verification prompt is explicitly last and audit-focused.
- No legacy migration phase list remains as active guidance.

## Notes for the coding agent
- Treat audit findings and current code state as the source of truth.
- Do not mark prompt completion unless corresponding code/tests/docs are updated and verified.
- If new drift is discovered, update tracker and build notes immediately with evidence-backed status.
