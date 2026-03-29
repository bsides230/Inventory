# File-Only Backend Rebuild — Phase 4

## Goal
Harden operations, complete migration cutover, and remove obsolete DB-era artifacts.

## Inputs from Audits
- `docs/PERSISTENCE_AUDIT.md`
- `docs/implementation_audit_report.md`

## Scope
1. Cutover tooling and data integrity checks.
2. Backup/restore for file-only runtime state.
3. Health visibility for queue + writable paths.
4. Final cleanup and docs alignment.

## Implementation Tasks
1. **Cutover tooling**
   - Add one-time export from legacy DB (if still needed).
   - Add integrity checker for order/draft/state consistency.
2. **Backup/restore**
   - Archive `config/`, `data/`, `drafts/`, `orders/`, `ipc/`, `logs/`.
   - Add restore drill with checksum validation.
3. **Monitoring/health**
   - `/health/ready` verifies required dirs/files and write access.
   - `/health/queue` reports inbox/processing/failed counts.
4. **Security and validation**
   - Validate payloads against schemas.
   - Enforce max payload size and safe filename rules.
5. **Final cleanup**
   - Remove dead files (`inventory_state.json` if superseded).
   - Remove DB-first docs that no longer match reality.
   - Update architecture/deployment/runbooks to file-only model.

## Exit Criteria
- Production stack has no DB service/container.
- Backup/restore drill passes using file-only data.
- Docs/tests/operations reflect file + IPC + state-flag architecture.

## Milestone Check
**Milestone D:** Backup/restore and queue/health checks validated in CI or drill.

## Cross-Phase Guardrails (applies to all phases)
- Use atomic temp-file + rename for all writes.
- Never mutate state files without lock + version checks.
- Keep event logs append-only.
- Keep state transitions explicit and machine-parseable.
- Add crash/power-loss boundary tests for critical flows.
