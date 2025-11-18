# Logo unification for login + dashboard

Progress: 🟨 70% – Shared logo source implemented, pending tests & verification

## Cíl
Login stránka (a další veřejné auth stránky) musí používat stejné branding logo jako dashboard a ostatní části UI. Logo se má brát z backendového branding API (`logo_url`), s fallbackem na defaultní asset, aby se změny loga projevily všude a přežily redeploy.

## Scope
- Měníme jen frontendové zdroje loga (layouty/komponenty), aby používaly sdílený branding hook/helper.
- Neměníme backend API, databázové schéma ani logiku nahrávání loga (už funguje).
- Nepřidáváme multi-tenant routing; respektujeme stávající globální branding.

## Tasks

- 🟩 [x] Najít a popsat zdroj loga na dashboardu (DB, API, komponenta)
- 🟩 [x] Najít a popsat zdroj loga na login stránce (statický asset / komponenta)
- 🟩 [x] Navrhnout společný interface / hook pro načítání aktivního loga
- 🟩 [x] Upravit login layout, aby používal dynamické logo
- 🟩 [x] Ujistit se, že funguje fallback logo (pokud není vlastní)
- 🟨 [ ] Přidat případně testy (unit/integration) pro logiku brandingu
- 🟨 [ ] Ruční test:  
  - nahrát nové logo,  
  - ověřit změnu na dashboardu i login stránce,  
  - ověřit chování po redeployi

## Implementation Notes
- Branding data se načítají v `frontend/src/app/layout.tsx` → `BrandingProvider`. Nový hook `useBrandingLogo` vrací hotové URL (prefixuje `/static/...` pomocí `NEXT_PUBLIC_API_URL`, jinak nechá lokální asset).
- `defaultBranding.logoUrl` nyní ukazuje na `public/logo-default.svg`, aby byl jasný fallback, když není vlastní logo.
- `AuthCard`, user/admin/owner layouty používají `useBrandingLogo`, takže login, register i chráněné sekce mají stejný zdroj.
- Formulář owner brandingu dál používá `resolveBrandingAssetUrl` pro preview (musí podporovat manuálně psané URL).
- Další krok je přidat testy/fyzické ověření – např. ručně nahrát logo, refresh login/dashboard, otestovat i po redeploy.

Plan ready for implementation.
