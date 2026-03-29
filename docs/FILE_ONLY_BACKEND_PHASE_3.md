# File-Only Backend Rebuild — Phase 3

## Goal
Implement DB-free order submission using file IPC and state-flag transitions.

## Inputs from Audits
- `docs/PERSISTENCE_AUDIT.md`
- `docs/implementation_audit_report.md`

## Scope
1. Submit flow writes authoritative order files.
2. IPC queue drives email delivery processing.
3. State flags reflect delivery lifecycle.
4. Recovery handles crashes and stranded work.

## Implementation Tasks
1. **Submit path**
   - Validate draft.
   - Write `orders/submitted/<order_id>.json`.
   - Write `orders/submitted/<order_id>.xlsx`.
   - Write `orders/flags/<order_id>.state` as `submitted`.
2. **IPC enqueue**
   - Create `ipc/inbox/<event_id>.json` with `order_id` and `type=email_send`.
3. **Worker processing**
   - Move event from `inbox -> processing`.
   - Send email from existing file config.
   - State transitions:
     - success: `emailed`
     - failure: `email_failed`
   - Move event to `done` or `failed`.
4. **Observability/dead-letter**
   - Append failures to `logs/order_email_dead_letter.log`.
   - Append transitions to `logs/events.jsonl`.
5. **Crash recovery**
   - Requeue stale `processing` events on startup.

## Exit Criteria
- Submit path is fully DB-free and persists JSON + XLSX.
- Email retries and transitions run through IPC queue.
- Worker crash/restart can recover in-flight events safely.

## Milestone Check
**Milestone C:** Submit/email lifecycle is fully file-driven with retries.
