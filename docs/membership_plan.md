# Membership / Permanentka Migration Plan

Goal: replace the legacy credit-based access model with package-based memberships (permanentky + osobní tréninky) while keeping the platform functional during the transition.

## Strategy Overview

- **Variant A (discarded):** migrate everything in one sweep (credits → memberships). Risky because credits would break mid-migration.
- **Variant B (chosen):** run memberships in parallel, keep credits temporarily for backward compatibility, and gradually move every feature.

## Phases

### Phase 1 – Data & Services (in progress)
- [x] Extend database schema (`membership_packages`, richer `memberships`, AccessLog metadata fix).
- [x] Create backend service helpers for packages, assignments, daily limits, and seeding default packages.
- [ ] Add tests for membership service utilities.

### Phase 2 – Backend & Admin API
- [ ] Admin endpoints for CRUD on membership packages.
- [ ] Admin tooling to assign permanentky / personal trainings to users, pause/cancel memberships, and inspect usage.
- [ ] Update `/verify` / scan processing to evaluate memberships first, credits second (legacy fallback).
- [ ] Extend payments API to create membership purchases (`package_id`).

### Phase 3 – Frontend Integration
- [ ] Admin console “Balíčky” section + user detail panel for permanentky and osobní tréninky.
- [ ] User dashboard: list active memberships, show CTA when no membership is active, new “buy permanentka” flow (Comgate).
- [ ] New scanner UI screens (`/scanner`, `/scanner-in`, `/scanner-out`) to reflect membership reasons (daily limit, expired, etc.).

### Phase 4 – Cleanup & Migration
- [ ] Document migration path (how to convert existing credits to memberships).
- [ ] Hide / remove credits UI once membership management is verified.
- [ ] Update README + deployment docs, seed scripts, and automated tests.

## Notes
- Default packages seeded automatically:
  - `monthly_standard`: 30denní permanentka (1500 Kč, 1 vstup/den).
  - `personal_training_single`: jednorázový osobní trénink (limit 1 vstup).
- Credits remain untouched for now; scanner logic still subtracts credits until Phase 2 hooks in the new service.
