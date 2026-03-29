# File-Only Backend Rebuild — Phase 1

## Goal
Remove DB runtime dependencies while preserving current behavior, and stabilize file contracts.

## Inputs from Audits
- `docs/PERSISTENCE_AUDIT.md`
- `docs/implementation_audit_report.md`

## Scope
1. Remove DB integration from request paths.
2. Remove DB infrastructure from runtime/deploy stack.
3. Define file contracts for draft/order/event/state payloads.
4. Add crash-safe file utilities.

## Implementation Tasks
1. **Remove DB code paths**
   - Remove repository/session usage from `server.py`.
   - Remove ORM-backed user/draft/order calls.
2. **Remove DB infrastructure**
   - Remove `db/` runtime usage and Alembic usage.
   - Remove DB service/volume references from deployment config.
   - Remove DB dependencies from Python requirements.
3. **Publish file contracts in docs**
   - `draft.schema.json`
   - `order.schema.json`
   - `ipc_event.schema.json`
   - `state_flag_conventions.md`
4. **Add file safety helpers**
   - `write_json_atomic(path, payload)`
   - `append_jsonl(path, payload)`
   - `with_lock(lock_path)`

## Exit Criteria
- App boots and serves read endpoints without DB settings.
- No runtime imports from `db.*` remain.
- Draft/order/event/state file contracts are documented.

## Milestone Check
**Milestone A:** Runtime has zero DB imports and zero DB containers.
