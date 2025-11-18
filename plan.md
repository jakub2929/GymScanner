# Owner Branding – Logo Upload Fix

Overall status: 🟨 60% – Backend + frontend upload flow hotový, chybí docker/test verifikace.

## 1. Backend – Upload endpoint a uložení souboru
- [x] 🟩 Zkontrolovat a sjednotit FastAPI endpoint pro upload loga (form field `file`, HTTP 401/415/413 odpovědi)
- [x] 🟩 Opravit ukládání: po uploadu hned aktualizovat `BrandingSettings.logo_url`, smazat původní logo a vrátit aktuální BrandingSettings
- [x] 🟩 Přidat validnější chyby (velikost, typ, prázdný soubor) a rollback při selhání

## 2. Backend – Servírování statických souborů
- [x] 🟩 Ověřit, že `app.mount("/static", ...)` používá správný adresář i v Dockeru/Coolify (ponechány relativní cesty)
- [x] 🟩 Rozhodnout, že backend vrací relativní `/static/...` cesty a prefix řeší frontend helper
- [ ] 🟥 Aktualizovat dokumentaci/env vzory pro volume `static/branding`

## 3. Frontend – Formulář a API volání
- [x] 🟩 Prověřit `handleLogoUpload` – FormData posílá pole `file`, bez ručního Content-Type
- [x] 🟩 Po úspěchu automaticky uložit logo (response = BrandingSettings) + toast
- [x] 🟩 Ošetřit reset inputu a validaci chyb

## 4. Frontend – Náhled a použití loga
- [x] 🟩 Konvertovat `logoUrl` na absolutní URL pomocí helperu `resolveBrandingAssetUrl`
- [x] 🟩 Aktualizovat preview/layouty (`AuthCard`, user/admin/owner nav) aby používaly helper a placeholder
- [x] 🟩 Ujistit se, že se změna loga projeví okamžitě v náhledu (aktualizace form value + toast)

## 5. Docker & Deployment
- [ ] 🟥 Potvrdit volume pro `static/branding` v `docker-compose*.yml` i Coolify (perzistence uploadů)
- [ ] 🟥 Ověřit upload v lokálním `docker-compose` (soubor se zapíše a je dostupný na `/static/...`)
- [ ] 🟥 Popsat postup v README/DEPLOY (velikost 1 MB, povolené typy, potřeba restartu?)

## 6. Testy a kontrola
- [ ] 🟥 Přidat Pytest pro upload endpoint (validní PNG, příliš velký soubor, chybný MIME)
- [ ] 🟥 Vyzkoušet UX v prohlížeči (Chrome devtools → Network: request, response, náhled)
- [ ] 🟥 FInální smoke test: změna loga + textů + primární barvy, reload UI, loga se zobrazují na všech stránkách

Plán je hotový, přepni se do Implementation Phase podle tohoto plan.md.
