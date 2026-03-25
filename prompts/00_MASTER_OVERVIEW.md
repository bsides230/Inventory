# Master Overview Prompt — Ordering Platform Migration

## What the app is
You are working on a **mobile-first ordering platform** where authenticated users build draft orders, review them, and submit them for fulfillment. This is **not** an inventory-taking tool. The user journey is: sign in → create/update draft order → review → submit → delivery/confirmation.

## Why this migration is needed
The current implementation has single-session behavior (shared draft state) and file-local persistence patterns that break under concurrent public use. The migration is required to:
- support multiple users ordering at the same time without cross-user data collisions;
- enforce auth and role boundaries for write/admin actions;
- provide reliable server-side order delivery (email + retries + artifacts);
- operate safely on public HTTPS infrastructure with observability, backups, and operational controls;
- preserve/install PWA behavior on iPhone and Android.

## Overall phase order (execute in sequence)
1. `01_PHASE_0_STABILIZE_AND_PREPARE.md`
2. `02_PHASE_1_MULTI_USER_DATA_MODEL.md`
3. `03_PHASE_2_EMAIL_DELIVERY_AND_TEXT_CONFIG.md`
4. `04_PHASE_3_PUBLIC_DEPLOYMENT.md`
5. `05_PHASE_4_PWA_HARDENING.md`
6. `06_PHASE_5_ADMIN_PANEL_AND_MASTER_LIST_MANAGEMENT.md`
7. `07_PHASE_6_SECURITY_COMPLIANCE_OPERATIONS.md`

Optional sub-prompts (use when Phase 1 scope is too large for one execution pass):
- `02A_PHASE_1_SCHEMA_AND_MODELS.md`
- `02B_PHASE_1_AUTH_AND_WRITE_PROTECTION.md`
- `02C_PHASE_1_DRAFT_ORDER_FLOW.md`

## How to use these prompt files
- Execute one prompt file at a time.
- Treat each file as self-contained task instructions.
- Complete all required deliverables and tests before moving to the next dependent prompt.
- If a phase is blocked, document blocker(s) and leave the system in a passing, stable state.
- Do not silently expand scope; defer out-of-scope work to the next phase prompt.

## Critical product framing
- Keep the product framed as an **ordering workflow platform**.
- Core entities should be users, draft orders, submitted orders, order items, delivery settings, and admin-managed catalog inputs.
- Avoid language, APIs, or behavior that re-centers the product around “inventory counting” or shared inventory mutation.

## Major constraints and non-goals
- Do not redesign the product into a native mobile app.
- Do not replace FastAPI/static-web architecture unless explicitly required for phased deliverables.
- Do not require Tailscale for public access goals.
- Do not couple immediate recipient management to admin UI before the text-config phase ships.
- Do not collapse all phases into one giant change set.
- Prioritize reliability, concurrency safety, and clear migration sequencing over feature sprawl.

## Global definition of success
- Concurrent users can create and submit orders without affecting each other.
- Authenticated writes and role-bound admin capabilities are enforced.
- Submission and email delivery are auditable and retryable.
- System is publicly deployable via HTTPS and operationally maintainable.
- PWA install/use experience remains functional on Android and iPhone.
