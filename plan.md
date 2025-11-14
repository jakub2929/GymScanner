# Deployment & API Routing Fix Plan – Status: 🟩 100% complete

**Goal:** Zprovoznit API doménu `ko0k4okk0k8wc444os8880gw.93.91.159.48.sslip.io`, aby nevracela 404, frontend volal správné API URL, CORS/ComGate URL reflektovaly skutečné domény a oba kontejnery fungovaly v Coolify bez reverzního proxy „/api“ hacků.

## Tasks
1. 🟩 Audit Compose services (`web`, `frontend`, `db`) a potvrď porty + veřejné domény, aby bylo jasné, že API běží samostatně.
2. 🟩 Upravit FastAPI root (`/`) tak, aby vracel JSON místo slepého redirectu na frontend (ať přístup na API doménu funguje pro lidské i automatické kontroly).
3. 🟩 Sladit veřejné URL proměnné:
   - `NEXT_PUBLIC_API_URL` = plná API doména
   - `FRONTEND_URL` / `WEB_ORIGIN` / `NEXT_PUBLIC_WEB_ORIGIN` / `SERVICE_URL_*` = jejich příslušné domény (HTTP zatím)
4. 🟩 Aktualizovat backend CORS tak, aby četl whitelist z env (`CORS_ORIGINS`) a omezil se na frontend doménu, ne `*`.
5. 🟩 Potvrdit/aktualizovat ComGate `COMGATE_NOTIFY_URL` / `COMGATE_RETURN_URL`, aby dál mířily na API doménu s `/api/payments/comgate/*`.
6. 🟩 Zrevidovat dokumentaci (`COOLIFY_ENV_VARS*.md`, `DEPLOY.md`, `COOLIFY_QUICKSTART.md`) pro nové nastavení URL a CORS.
7. 🟩 Otestovat lokální buildy (`docker compose build`, `pnpm build`) a popsat jak na Coolify ověřit `/health`, `/api/docs`, frontend → API request i ComGate callback.

## Implementation Notes
- **Files to touch:** `app/main.py` (root response + CORS config), pravděpodobně config/helper modul pro CORS whitelist, `docker-compose.yml` (default envs), `COOLIFY_ENV_VARS.md` + `COOLIFY_ENV_VARS_ACTUAL.txt` + `COOLIFY_QUICKSTART.md` + `DEPLOY.md` (nové instrukce), případně `frontend/Dockerfile` nebo `.env` příklady.
- **Env management:** Coolify bude mít plné URL (HTTP prozatím) v `NEXT_PUBLIC_API_URL`, `FRONTEND_URL`, `WEB_ORIGIN`, `CORS_ORIGINS`, `COMGATE_*`. Zmínit, že po zapnutí TLS se přepnou na HTTPS.
- **Redeploy:** Po úpravách je potřeba v Coolify znovu spustit Compose deploy, aby web + frontend buildy získaly nové env proměnné. Frontend musí být rebuiltnut kvůli `NEXT_PUBLIC_API_URL`.

## Verification
- `docker compose build` – proběhlo lokálně (hlídá Python image + nové env defaults).
- `pnpm build` uvnitř `frontend/` – zajišťuje, že Next.js má validní `NEXT_PUBLIC_API_URL`.
- Po nasazení v Coolify: otevři `http://<api-domain>/` (JSON), `http://<api-domain>/health`, `http://<api-domain>/api/docs`, ověř že frontend (`http://<frontend-domain>`) volá API doménu a že ComGate callbacky míří na `http://<api-domain>/api/payments/comgate/*`.
