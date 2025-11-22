# Gym Turnstile QR System
COMGATE_MERCHANT_ID=123456
COMGATE_NOTIFY_URL=http://ko0k4okk0k8wc444os8880gw.93.91.159.48.sslip.io/api/payments/comgate/notify
COMGATE_RETURN_URL=http://ko0k4okk0k8wc444os8880gw.93.91.159.48.sslip.io/api/payments/comgate/return
COMGATE_SECRET=gx4q8OV3TJt6noJnfhjqJKyX3Z6Ych0y
COMGATE_TEST_MODE=true

scanner@scanner.cz scanner pristup
123456789

## Projekt
Systém pro správu vstupu do posilovny pomocí QR kódů. Uživatelé se registrují, přihlásí, získají osobní QR kód a mohou vstoupit do gymu. Systém používá kredity (1 kredit = 1 cvičení) s ochranou proti dvojitému odpíchnutí pomocí cooldown systému.

## Technologie
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (Docker Compose service)
- **Frontend**: Next.js 14 + React 19 + TypeScript, Tailwind CSS 4, TanStack Query, React Hook Form, html5-qrcode (Apple „liquid glass“ design)
- **Containerization**: Docker & Docker Compose
- **Authentication**: JWT tokens
- **Password Hashing**: Argon2
- **Security**: HTTPS s self-signed certifikáty

## Funkce

### Pro uživatele
- Registrace a přihlášení s JWT autentizací
- Osobní QR kód pro vstup do gymu
- Stahování QR kódu jako obrázek (PNG)
- Kreditový systém (1 kredit = 1 cvičení)
- Nastavení účtu (změna hesla, info o účtu)
- Čistý, moderní UI design s Tailwind CSS

### Pro správu gymu
- QR scanner pro turnstile (mobilní zařízení)
- Cooldown ochrana (60 sekund mezi úspěšnými vstupy)
- Admin dashboard pro správu uživatelů a kreditů
- Access log pro audit vstupů

### Owner / Global branding
- Samostatné owner přihlášení `/owner/login` (JWT s claimem `role=owner`, oddělené sezení od user/admin tokenu)
- Chráněná stránka `/owner/branding` s formulářem pro název značky/konzole, tagline, support email, primární barvu, footer text a URL loga + upload (PNG/JPG/SVG, max 1 MB)
- Uploadované logo se ukládá do `static/branding` a je dostupné přes `/static/...`, Compose mapuje složku na hostitele kvůli persistenci
- Backend má nové endpointy `/api/owner/*` (login, me, branding, upload) a veřejné `/api/branding` pro SSR načtení brandingu ve frontendu
- Frontend načítá branding už v root layoutu (Next.js SSR) a promítá hodnoty do loginů, dashboardů, admin UI i patičky přes CSS proměnné (`--brand-primary`)

## Comgate test API

Produkční nákupy tokenů teď používají Comgate platební bránu. Backend volá HTTP POST endpoint `https://payments.comgate.cz/v1.0/create` (přepiš pomocí `COMGATE_API_URL`, pokud Coolify používá jinou testovací URL) a předává `refId` = interní `payment_id`.  
Po úspěšném vytvoření objednávky backend vrací `redirect_url`, na kterou frontend přesměruje uživatele.  
Callbacky:

- `COMGATE_NOTIFY_URL` → POST `/api/payments/comgate/notify` (potvrdí platbu a přičte tokeny)
- `COMGATE_RETURN_URL` → GET `/api/payments/comgate/return` (zobrazení stavu platby)

Nutné proměnné:

```
COMGATE_MERCHANT_ID=...
COMGATE_SECRET=...
COMGATE_TEST_MODE=true
COMGATE_RETURN_URL=http://<api-domain>/api/payments/comgate/return
COMGATE_NOTIFY_URL=http://<api-domain>/api/payments/comgate/notify
COMGATE_API_URL=https://payments.comgate.cz/v1.0/create        # HTTP-POST endpoint (lze přepsat)
COMGATE_DEFAULT_PHONE=+420777111222                    # fallback telefon, pokud uživatel nemá číslo
COMGATE_PREPARE_ONLY=0                                 # 1 = pouze předautorizace, 0 = rovnou platba
COMGATE_DELIVERY=HOME_DELIVERY                         # Comgate delivery param
COMGATE_CATEGORY=PHYSICAL_GOODS_ONLY                   # Comgate category param

# Turniket / scan logika
GYM_TIMEZONE=Europe/Prague                             # Časová zóna pro denní limit
DOOR_OPEN_DURATION_DEFAULT=5                           # Default délka otevření dveří (sekundy) pro allowed scan
```

Frontend (`/dashboard`) nyní volá `/api/payments/create` a po úspěchu automaticky přesměruje na Comgate. Po návratu/notify získává uživatel nové kredity.

## Struktura projektu
```
GymScanner/
├── app/                     # FastAPI backend + SQLAlchemy modely
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   └── routes/ (auth, user_qr, verify, credits, admin, …)
├── frontend/                # Next.js 14 aplikace (React/TypeScript, Tailwind)
│   ├── package.json
│   └── src/app/
│       ├── (auth)/login + register
│       ├── (app)/(dashboard|scanner|settings)
│       └── admin/(auth|protected) – nové admin UI
├── docs/                    # Migrační plány a design guidelines
│   ├── apple_liquid_design_plan.md
│   └── nextjs_migration_plan.md
├── docker-compose.local.yml # FastAPI + Postgres lokálně
├── Dockerfile
└── README.md
```

## Jak spustit (PostgreSQL + Docker Compose + Next.js dev)

1. **Vytvoř `.env` a certifikáty:**
```bash
cp .env.example .env
# (Volitelné) Pokud chceš lokální HTTPS, spusť generate_cert.sh a uprav docker-compose podle README.
```

2. **Spusť PostgreSQL a FastAPI backend:**
```bash
docker compose -f docker-compose.local.yml up -d
# první start stáhne image postgres:15-alpine a vytvoří volume postgres_data
```

3. **Sleduj logy / ověř běh backendu:**
```bash
docker compose -f docker-compose.local.yml logs -f web
```

4. **Spusť Next.js dev server (nové UI):**
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8181 npm run dev
```
Dev server běží ve výchozím stavu na `http://localhost:3000`. `NEXT_PUBLIC_API_URL` musí směřovat na FastAPI (`http://localhost:8181` v lokálním Dockeru).

5. **Otevři v prohlížeči:** `http://localhost:3000/login`, `/register`, `/dashboard`, `/settings`, `/admin/login`, `/admin`.
   - Scanner (`/scanner`) je stále dostupný pro kiosk/tablet, ale není součástí hlavní navigace.

**Poznámka:** Docker compose vystavuje FastAPI na `http://localhost:8181`. Pokud chceš HTTPS, povol SSL (viz `generate_cert.sh`) a přidej odpovídající port/certifikáty.
Uploads owner loga se ukládají do `./static/branding` (mapováno do kontejneru jako `/app/static`), takže složka musí existovat a mít práva k zápisu.

## Next.js frontend (React/TypeScript)

- Zdrojáky najdeš v `frontend/src/app/` rozdělené do segmentů `(auth)` pro login/registraci, `(app)` pro chráněné uživatelské stránky a `admin/(auth|protected)` pro nové admin rozhraní.
- Globální stav tokenu je v Jotai (`lib/authStore`), data se načítají přes TanStack Query a `apiClient` automaticky doplňuje JWT z `sessionStorage`.
- Vytvoř si `.env.local` (nebo použij proměnnou při `npm run dev`) s `NEXT_PUBLIC_API_URL=http://localhost:8181` / adresou FastAPI.
- Pro produkční deployment je připraven `frontend/Dockerfile` (Next.js standalone build) – viz `DEPLOY.md`.

### Užitečné příkazy v `frontend/`
```bash
npm run dev    # Next.js dev server (Turbopack)
npm run build  # produkční build
npm run start  # spuštění buildu
npm run lint   # ESLint (musí projít před commitem)
```

## API Endpoints

### Autentizace
- `POST /api/register` - Registrace nového uživatele
- `POST /api/login` - Přihlášení (vrací JWT token + `user_name`, `user_email`, `is_admin`)
- `POST /api/logout` - Odhlášení
- `GET /api/user/info` - Informace o aktuálním uživateli (`is_admin`, `qr_count`, datum registrace) – vyžaduje auth
- `POST /api/user/change-password` - Změna hesla (vyžaduje auth)

### QR kódy a vstup
- `GET /api/my_qr` - Získání osobního QR kódu (vyžaduje auth)
- `POST /api/regenerate_qr` - Vygenerování nového QR kódu (vyžaduje auth)
- `POST /api/verify` - Ověření QR kódu (turnstile scanner)
  - Response: `{allowed: bool, reason: str, credits_left: int, cooldown_seconds_left: int | null}`
- `POST /api/scanner/in` - Server-to-server verifikace pro turniket (API key v `X-TURNSTILE-API-KEY`, payload: token, scanner_id, raw_data)
- `POST /api/scanner/out` - Logování odchodu (API key v `X-TURNSTILE-API-KEY`, payload: token, scanner_id, raw_data)
- `POST /api/scan/in` - Alias pro IN se strukturovaným payloadem `{token, timestamp, device_id}`
- `POST /api/scan/out` - Alias pro OUT se strukturovaným payloadem `{token, timestamp, device_id}`
- `POST /api/admin/users/{user_id}/rebuild-presence` - Admin akce pro přepočet `is_in_gym` z posledního logu
- Scan response pro turnikety obsahuje navíc: `open_door` (bool), `door_open_duration` (sekundy), `user {name,email}`; pokud `allowed=true` a `open_door=true`, daemon otevře relé na zadanou dobu.
- **Frontend:** Tlačítko "Stáhnout QR" pro stažení QR kódu jako PNG obrázek

### Kredity
- `POST /api/buy_credits` - Nákup kreditů (vyžaduje auth)
- `GET /api/my_credits` - Zobrazení kreditů (vyžaduje auth)

### Admin
- `GET /api/admin/users` - Posledních 100 uživatelů (vyžaduje admin)
- `GET /api/admin/users/search` - Vyhledávání uživatelů dle jména/e-mailu (vyžaduje admin)
- `POST /api/admin/users/{user_id}/credits` - Přidání/odečtení kreditů (vyžaduje admin)
- `GET /api/admin/tokens` - Přehled tokenů včetně QR preview (vyžaduje admin)
- `POST /api/admin/tokens/{token_id}/activate` - Aktivuj token (vyžaduje admin)
- `POST /api/admin/tokens/{token_id}/deactivate` - Deaktivuj token (vyžaduje admin)

### Logs
- `GET /api/access_logs` - Access log (pro debugging/admin)

## Databázové modely

### User
- `id`, `email`, `name`, `password_hash`
- `credits` (Integer, default=0) - Počet kreditů
- `is_admin` (Boolean, default=False) - Admin práva
- `is_owner` (Boolean)
- `is_trainer` (Boolean) - Trenér (bypass membership/daily limit)
- `is_in_gym` (Boolean) - Stav přítomnosti
- `last_entry_at`, `last_exit_at`
- `created_at` (DateTime) - Datum vytvoření účtu

### AccessToken
- `token` (String, unique) - UUID token pro QR kód
- `user_id` (Foreign Key) - Vlastník tokenu
- `is_active` (Boolean, default=True) - Aktivní token
- `scan_count` (Integer, default=0) - Počet skenů
- `last_scan_at` (DateTime, nullable) - Poslední úspěšný scan (pro cooldown)
- `used_at` (DateTime, nullable) - Kdy byl token naposledy použit
- `expires_at` (DateTime, nullable) - Expirace (null = žádná expirace)
- `created_at` (DateTime) - Datum vytvoření tokenu

### AccessLog
- `token_id` (Foreign Key, nullable) - ID tokenu
- `token_string` (String) - Token string (i když token je smazaný)
- `status` (String) - "allow" nebo "deny"
- `reason` (String) - Důvod povolení/zamítnutí
- `direction` (Enum: in/out) - Směr průchodu z device
- `scanner_id` (String, nullable) - ID čtečky (např. in-1/out-1 / device_id)
- `raw_data` (Text, nullable) - Původní string ze čtečky
- `ip_address` (String, nullable) - IP adresa klienta
- `user_agent` (String, nullable) - User agent
- `scanned_at` (DateTime) - Čas scanu na zařízení
- `processed_at` (DateTime) - Čas zpracování na serveru
- `entry`/`exit` (Boolean) - Doménová interpretace
- `allowed` (Boolean) - true/false
- `direction_from_device`, `direction_from_state`, `direction_mismatch` (Bool)
- `raw_token_masked` (String)
- `metadata` (JSON, nullable)
- `created_at` (DateTime) - Čas zápisu záznamu

### Membership
- `id`, `user_id`
- `valid_from`, `valid_to` (30denní platnost)
- `daily_limit_enabled` (Boolean) - aktivuje pravidlo 1 vstup denně

### DoorLog
- `device_id`
- `user_id` (nullable)
- `access_log_id` (nullable, pro spojení se scanem)
- `duration` (sekundy)
- `status` ("opened", "hw_error", "timeout", "skipped")
- `initiated_by` ("scan" zatím)
- `started_at`, `ended_at`
- `raw_error` (text, nullable)

### Payment
- `user_id`, `amount`, `status`, `payment_id`
- `created_at`, `completed_at`

## Systém kreditů

- **1 kredit = 1 cvičení**
- Při úspěšném scanování QR kódu se odečte 1 kredit
- QR kód nemá expiraci (pouze kontrola kreditů)
- Kredity se kupují přes `/api/buy_credits` nebo přidávají adminem
- **Ochrana:** Kredity nesmí jít do minusu - pokud je 0 kreditů, vstup je zamítnut

## Cooldown systém

- **Délka:** 60 sekund mezi úspěšnými vstupy
- **Scope:** Na úrovni uživatele (všechny tokeny stejného uživatele sdílejí cooldown)
- **Chování:** Po úspěšném skenu se nastaví `last_scan_at` pro všechny aktivní tokeny uživatele
- **Ochrana:** Zabraňuje dvojitému odpíchnutí - pokud uživatel zkusí naskenovat QR kód dřív než za 60 sekund, vstup je zamítnut s cooldown zprávou

## Response struktura verify endpointu

```json
{
  "allowed": true/false,
  "reason": "ok" | "no_credits" | "cooldown" | "invalid_token" | "token_not_found" | "token_deactivated" | "user_not_found",
  "credits_left": 5,
  "cooldown_seconds_left": null | 45,
  "user_name": "Jan Novák" | null,
  "user_email": "jan@example.com" | null
}
```

### Důvody zamítnutí:
- `no_credits` - Uživatel nemá žádné kredity (0)
- `cooldown` - Příliš rychlé další odpíchnutí (aktivní cooldown)
- `invalid_token` - Token není aktivní nebo je neplatný
- `token_not_found` - Token nebyl nalezen v databázi
- `token_deactivated` - Token byl deaktivován
- `user_not_found` - Uživatel tokenu nebyl nalezen

## Docker (lokální vývoj)

`docker-compose.local.yml` obsahuje dvě služby:
- `postgres` (PostgreSQL 15 + persistentní volume `postgres_data`)
- `web` (FastAPI aplikace, port mapovaný na `8181 -> 8000`)

Užitečné příkazy:

```bash
# Build (přegeneruje image web služby)
docker compose -f docker-compose.local.yml build web

# Start obou služeb v pozadí
docker compose -f docker-compose.local.yml up -d

# Zastavení
docker compose -f docker-compose.local.yml down

# Restart jen backendu
docker compose -f docker-compose.local.yml restart web

# Logy backendu
docker compose -f docker-compose.local.yml logs -f web
```

Pokud potřebuješ rebuild + restart:

```bash
docker compose -f docker-compose.local.yml down
docker compose -f docker-compose.local.yml build web
docker compose -f docker-compose.local.yml up -d
```

**Poznámka:** `docker-compose.yml` je určený pro Coolify. Lokální HTTPS je volitelné – pokud ho potřebuješ, přidej certifikáty (viz `generate_cert.sh`) a uprav docker-compose podle svých potřeb.

## Frontend (Next.js) development

- Zdrojové kódy: `frontend/` (Next.js 14, TypeScript, Tailwind).
- `.env.example` uvnitř obsahuje `NEXT_PUBLIC_API_URL` (default `http://localhost:8181`). Zkopíruj na `.env.local`.
- Instalace závislostí:

```bash
cd frontend
npm install
```

- Spuštění dev serveru (běží na `http://localhost:3000`):

```bash
npm run dev
```

API requests jsou proxy‑ovány na FastAPI (`NEXT_PUBLIC_API_URL`). FastAPI již neslouží žádné HTML stránky, pouze REST API + healthcheck (root endpoint vrací odkaz na frontend).

## Deployment na Coolify

Aplikace je připravena pro deployment na Coolify (self-hosted platforma).

**Pro detailní instrukce viz:** [DEPLOY.md](./DEPLOY.md)

### Rychlý start:

1. Vytvoř aplikaci v Coolify dashboard
2. Použij `Dockerfile.production` pro build
3. Nastav environment proměnné (viz `.env.example`)
4. Přidej doménu (Coolify automaticky nastaví SSL)
5. Deploy!

**Výhody Coolify:**
- Automatické SSL certifikáty (Let's Encrypt)
- Reverse proxy s HTTPS
- Snadný deployment z Git
- Automatické health checks
- Monitoring a logy

## Environment variables

Vytvoř soubor `.env` na základě `.env.example`:

- `DATABASE_URL` - PostgreSQL connection string (default: `postgresql+psycopg2://gymuser:gympass@localhost:5432/gym_turnstile`)
  - V Docker Compose je tato hodnota přepsaná na `postgresql+psycopg2://gymuser:gympass@postgres:5432/gym_turnstile`
- `FRONTEND_URL` - veřejná URL Next.js aplikace (default `http://localhost:3000`, používá ji FastAPI root endpoint pro odkázání na UI)
  - Pokud ti Next.js dev server běží na jiném portu (např. `http://localhost:3200`), nastav tuto hodnotu, aby root API vracel správný odkaz.
- `JWT_SECRET_KEY` - Secret key pro JWT tokeny (důležité pro produkci!)
- `JWT_ALGORITHM` - Algorithm pro JWT (default: `HS256`)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Expirace tokenu v minutách (default: `60`)
- `OWNER_EMAIL` / `OWNER_PASSWORD` / `OWNER_NAME` - pokud ještě není vytvořen owner účet, při startu se založí podle těchto hodnot (jinak se v logu objeví varování)
- `OWNER_ACCESS_TOKEN_EXPIRE_MINUTES` - volitelné odlišné TTL pro owner JWT (fallback na `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)
- `BRANDING_UPLOAD_DIR`, `BRANDING_LOGO_MAX_BYTES`, `BRANDING_DEFAULT_*` - konfigurace uploadu loga a výchozí white-label hodnoty (viz `.env.example`)
- `STATIC_DIR` - cesta ke statické složce pro loga (default `static`), přimountuj ji ve `docker-compose*.yml`, aby uploady přežily redeploy

## HTTPS konfigurace

Aplikace běží na HTTPS portu 443 s self-signed certifikáty.

- Certifikáty jsou generovány pomocí `generate_cert.sh`
- Uloženy v `ssl/` složce
- Mapovány do Docker kontejneru přes volume
- Pro produkci doporučujeme použít Let's Encrypt nebo jiný důvěryhodný CA

## Debugging

### Docker logy
```bash
docker-compose logs -f web
```

### Network debugging
1. Zkontroluj Network tab v prohlížeči (Authorization header)
2. Zkontroluj localStorage (access_token)
3. Zkontroluj JWT token na jwt.io

### Backend debugging
- Všechny chyby jsou logovány do konzole Docker kontejneru
- Access log je dostupný přes `/api/access_logs` endpoint
- Middleware loguje všechny requesty (viditelné v Docker logách)

## Poznámky

- Systém je připraven k použití
- Mock platby (ne skutečné platební brány)
- PostgreSQL databáze (docker volume `postgres_data`)
- HTTPS s self-signed certifikáty (pro produkci doporučujeme Let's Encrypt)
- Čistý, moderní UI design s Tailwind CSS (bez emojis, bez přehnaných gradientů)
- Cooldown ochrana proti dvojitému odpíchnutí
- Kompletní error handling a transakční bezpečnost

## Design modernization
- Připravujeme Apple-inspirovaný “liquid glass” vzhled všech stránek. Detailní plán kroků (`tooling → auth → dashboard → scanner → admin`) je v `docs/apple_liquid_design_plan.md`.
- Zvažujeme migraci na Next.js + TypeScript front-end. Rozsah a odhad prací je popsán v `docs/nextjs_migration_plan.md`.

## Historie změn

### Verze 1.2.0 (aktuální)
- Refaktor designu dashboard stránky na Tailwind CSS
- Odstranění emojis z UI (čistší, profesionálnější vzhled)
- Přidání tlačítka "Stáhnout QR" pro stažení QR kódu jako PNG
- Nová barevná paleta (čisté barvy, žádné přehnané gradienty)
- Zachování všech funkcí (QR zobrazení, kredity, regenerace)

### Verze 1.1.0
- Oprava HTTP 500 chyby v verify endpointu
- Přidání cooldown ochrany (60s na úrovni uživatele)
- Moderní gym UI design (scanner, dashboard)
- Nastavení účtu (změna hesla, info)
- HTTPS podpora
- Vylepšený error handling
- Ochrana proti záporným kreditům

### Verze 1.0.0
- Základní funkcionalita (registrace, login, QR kódy)
- Kreditový systém
- Admin dashboard
