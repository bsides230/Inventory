# Phase 4 — PWA Hardening (iPhone/Android)

## Objective
Harden installable web app behavior and update/offline UX for mobile ordering users.

## System Context
The app already has basic manifest/service-worker support; this phase makes mobile install/use behavior reliable under real-world conditions.

## In-Scope Work
- Finalize web manifest fields and icon coverage.
- Implement clear service-worker strategy:
  - static assets cache-first with versioning;
  - API calls network-first with graceful offline handling.
- Add install guidance UX for Android and iOS add-to-home-screen.
- Add update detection and refresh prompt flow.

## Out-of-Scope / Non-Goals
- Native iOS/Android app development.
- Offline order submission that bypasses server requirements.

## Required Code Changes
- Manifest and icon set updates.
- Service worker caching/version policy refinements.
- Frontend UI components for install/update/offline messaging.

## Required Tests
- PWA installability checks (manifest/service worker validity).
- Offline simulation tests for key screens.
- Update flow test confirming refresh prompt behavior.

## Deliverables
- Stable mobile PWA install and runtime behavior.

## Definition of Done
- Android install prompt flow works.
- iOS users receive clear add-to-home-screen guidance.
- Offline states are understandable; no broken/blank UI for expected paths.

## Notes for the Coding Agent
- Preserve ordering flow clarity even when presenting offline limitations.
