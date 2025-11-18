# Owner Branding & Login – Implementation Plan

Overall status: 🟨 75% – Backend + frontend hotovo, zbývá docker test a finální verifikace.

## 1. Backend – Owner Auth & Models
- [x] 🟩 Přidat model/roli pro ownera (rozšířit `User` o `is_owner`, helper funkce, seeding podle ENV)
- [x] 🟩 Přidat JWT claim/roli pro ownera (volitelně OWNER_ACCESS_TOKEN_EXPIRE_MINUTES, new deps `get_current_owner`)
- [x] 🟩 Přidat endpointy pro owner login/logout (`/api/owner/login`, `/api/owner/me` guard) napojené na FastAPI auth flow
- [x] 🟩 Přidat endpointy pro CRUD nad branding settings (`GET/PUT /api/owner/branding` s validací)
- [x] 🟩 Přidat endpoint pro upload loga (POST `/api/owner/logo-upload`, 1 MB limit, PNG/JPG/SVG, ukládání do static/branding + cleanup)

## 2. Database & Migration
- [x] 🟩 Migrace DB (sloupec `is_owner` u users, tabulka `branding_settings`, timestamps, indexes)
- [x] 🟩 Seed / inicializace výchozího owner účtu a brandingu (OWNER_EMAIL/PASSWORD, default branding fallback)
- [ ] 🟥 Otestovat migraci v Docker Compose lokálně (app start + helper skripty)

## 3. Frontend – Owner Login & Routing
- [x] 🟩 Vytvořit segment `/owner/login` (form, validace, nová navigace)
- [x] 🟩 Napojit na backend owner login endpoint (samostatný `ownerApiClient`, storage klíč)
- [x] 🟩 Uložit owner JWT do storage a přidat ho do `apiClient` (owner guard hook + token hydrator)
- [x] 🟩 Implementovat logout ownera (`useOwnerLogout`, čištění owner session dat)

## 4. Frontend – Branding UI & Preview
- [x] 🟩 Vytvořit stránku `/owner/branding` podle screenshotu (dvousloupcový layout, Tailwind glass styl)
- [x] 🟩 Formulář pro brand name, console name, tagline, support email, primary color, footer text, logo URL + upload/reset
- [x] 🟩 Náhledový panel s logem, textem a barvami (živá ukázka + fallbacky)
- [x] 🟩 Validace vstupů a error/success stavy (react-hook-form + zod, toast notifikace, loading states)

## 5. Global Theming Integration
- [x] 🟩 Načíst branding data do root layoutu (SSR fetch `/api/branding`, fallback defaults, cache strategy)
- [x] 🟩 Propagovat logo a texty do headeru/loginu/footeru (user + admin + auth layouty)
- [x] 🟩 Nastavit primary color přes CSS variables / Tailwind (globals.css var(--brand-primary), gradient update)
- [ ] 🟥 Otestovat na desktopu i mobilu (vizuální smoke test + reload scenarios)

## 6. Tests, Docker & Deployment
- [x] 🟩 Přidat základní unit/integration testy (backend owner guard, branding API; frontend component tests pokud možné)
- [ ] 🟥 Ověřit lokálně v `docker-compose.local.yml` (upload path volume, static serving)
- [x] 🟩 Aktualizovat `README.md` / `DEPLOY.md` s novými env a cestami (OWNER_EMAIL, upload info, SSR fetch)
- [ ] 🟥 Ověřit build a běh v produkčním Docker image (Coolify poznámky, static exposure)
