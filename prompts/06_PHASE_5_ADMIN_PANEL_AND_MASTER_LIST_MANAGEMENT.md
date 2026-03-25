# Phase 5 — Admin Panel and Master List Management

## Objective
Replace manual operational edits with admin-managed UI flows for recipient configuration and master list lifecycle management.

## System Context
Earlier phases prioritize ordering correctness and public operation. This phase improves non-technical maintainability and controlled catalog updates.

## In-Scope Work
- Admin UI to manage recipient email list.
- Admin UI to upload/replace English and Spanish master files.
- Diff preview before publish (added/removed/renamed items).
- Category label/icon/color editing controls.
- Safe re-index/rebuild trigger for catalog.
- Versioning/rollback support for master list changes.
- Validation of uploaded sheet structure before acceptance.

## Out-of-Scope / Non-Goals
- Re-architecting end-user ordering UX.
- Eliminating text-config fallback before admin flow is proven stable.

## Required Code Changes
- Admin-only API endpoints and permission checks.
- Admin frontend views/forms for recipients and master list workflows.
- Backend validation, versioning, publish, and rollback logic.
- Audit logging for admin changes.

## Required Tests
- RBAC tests for admin-only routes.
- File validation tests (happy and failure paths).
- Diff generation and rollback tests.
- End-to-end tests for publish workflow.

## Deliverables
- Functional admin panel workflows for recipients and master-list management.
- Safe publish + rollback path with validation and auditability.

## Definition of Done
- Non-technical admin can update recipients and master lists without file-system access.
- Bad uploads are blocked with actionable feedback.
- Rollback can restore a known-good version.

## Notes for the Coding Agent
- Keep changes auditable and reversible.
