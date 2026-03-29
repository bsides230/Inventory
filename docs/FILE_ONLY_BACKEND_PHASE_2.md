# File-Only Backend Rebuild — Phase 2

## Goal
Replace DB draft/session behavior with session-scoped file drafts and explicit state flags.

## Inputs from Audits
- `docs/PERSISTENCE_AUDIT.md`
- `docs/implementation_audit_report.md`

## Scope
1. Session identity via PIN-based auth.
2. Draft persistence per session file.
3. State-flag lifecycle and optimistic concurrency.
4. Lock-based writes to avoid collisions.

## Implementation Tasks
1. **Session identity**
   - Keep PIN-based auth from `config/locations.txt`.
   - Issue signed `session_id` (PIN + timestamp + nonce).
2. **Draft persistence**
   - `drafts/<session_id>.json` for single active draft.
   - Optional named drafts: `drafts/<session_id>__<draft_name>.json`.
3. **Draft state flags**
   - `state: active | submitting | submitted | abandoned`.
   - `version` monotonic integer for optimistic concurrency.
4. **Concurrency control**
   - Lock file `drafts/<session_id>.lock` before every write.
   - Reject stale updates when `version` mismatches.
5. **Compatibility guard**
   - Keep API response shape compatible where possible.

## Exit Criteria
- Concurrent users can edit drafts without cross-contamination.
- Restart preserves in-progress draft files.
- Submitting one session leaves other session drafts untouched.

## Milestone Check
**Milestone B:** Concurrent draft isolation is verified in tests.
