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
- [x] Admin endpoints for CRUD on membership packages.
- [x] Admin tooling to assign permanentky / personal trainings to users, pause/cancel memberships, and inspect usage.
- [x] Update `/verify` / scan processing to evaluate memberships first, credits second (legacy fallback).
- [x] Extend payments API to create membership purchases (`package_id`).

### Phase 3 – Frontend Integration
- [x] Admin console “Balíčky” section + user detail panel for permanentky and osobní tréninky.
- [x] User dashboard: list active memberships, show CTA when no membership is active, new “buy permanentka” flow (Comgate).
- [x] New scanner UI screens (`/scanner`, `/scanner-in`, `/scanner-out`) to reflect membership reasons (daily limit, expired, etc.).

### Phase 4 – Cleanup & Migration
- [ ] Document migration path (how to convert existing credits to memberships).
- [ ] Hide / remove credits UI once membership management is verified.
- [ ] Update README + deployment docs, seed scripts, and automated tests.

## Notes
- Default packages seeded automatically:
  - `monthly_standard`: 30denní permanentka (1500 Kč, 1 vstup/den).
  - `personal_training_single`: jednorázový osobní trénink (limit 1 vstup).
- Credits remain untouched for now; scanner logic still subtracts credits until Phase 2 hooks in the new service.

## Personal Training Sessions (Osobní tréninky)

### Options considered
1. **Membership-specific QR codes** – každý balíček by měl vlastní QR/PIN. Nevýhody: složité UX (uživatel musí přepínat kódy), více záznamů v čtečce.
2. **Jeden QR/PIN na uživatele + server-side kontrola** – čtečka najde uživatele podle tokenu a ověří aktivní permanentky/tréninky. Výhody: QR na kartičce/stickeru nikdy není potřeba měnit, PIN lze zadat ručně na čtečce.

**Vybraná varianta:** #2. Token (QR i PIN) je pevně svázán s uživatelem. Při skenu/pinu scanner pošle token, backend dohledá uživatele a následně vyhodnotí permanentky i osobní tréninky. Pokud není aktivní balíček, padá se zpět na starý kreditový systém.

### Workflow, který je nyní implementovaný
- Balíčky mohou mít `session_limit` (např. 5 osobních tréninků). Databáze i `MembershipService` sledují `sessions_used`.
- V admin API vznikl endpoint `POST /api/admin/users/{user_id}/memberships/{membership_id}/sessions/consume`, který odečte 1–10 tréninků, přidá optional poznámku a nastaví stav `completed`, když se limit vyčerpá.
- Admin UI (modál „Permanentky“ na obrazovce Uživatelé) ukazuje u každého membershipu progress bar a tlačítko **Odečíst trénink** – nově je tu i textové pole pro poznámku k zásahu trenéra/admina.
- Scanner (`/verify`) nejdřív posuzuje permanentky/tréninky (včetně denních limitů), až když nic aktivního není, bere kredity. Metadata o membershipu se logují do `AccessLog`.
- Uživatel na dashboardu vidí všechny aktivní balíčky, počet zbývajících tréninků a má CTA pro nákup nové permanentky; PIN je zvýrazněný na pravé straně.

### Manuální editace aktivního předplatného
1. Admin v sekci **Uživatelé → Permanentky** zvolí membership s tréninky a doplní poznámku (např. „Trénink s trenérem Filipem 12/6“).
2. Klikne na **Odečíst trénink** – UI zavolá zmíněný endpoint, backend zvýší `sessions_used`, uloží timestamp i poznámku.
3. Jakmile se `sessions_used == sessions_total`, membership se automaticky přepne do stavu `completed`. Další pokus o odečet vrátí 400.
4. Poznámky se ukládají do `membership.notes`, takže lze zpětně auditovat, kdo kdy odečetl trénink.

Tento flow dává trenérům možnost ručně „odklikat“ absolvované lekce bez potřeby dalšího hardware. Pokud bude potřeba, můžeme později UI rozšířit o historii odečtů nebo propojit s AccessLog.
