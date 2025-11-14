# Gym Turnstile QR System

## Projekt
Systém pro správu vstupu do posilovny pomocí QR kódů. Uživatelé se registrují, přihlásí, získají osobní QR kód a mohou vstoupit do gymu. Systém používá kredity (1 kredit = 1 cvičení) s ochranou proti dvojitému odpíchnutí pomocí cooldown systému.

## Technologie
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (Docker Compose service)
- **Frontend**: HTML/JavaScript s Tailwind CSS (čistý, moderní design)
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

## Struktura projektu
```
GymTurniket/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI aplikace
│   ├── database.py          # DB konfigurace a migrace
│   ├── auth.py              # JWT autentizace
│   ├── models.py            # SQLAlchemy modely
│   └── routes/
│       ├── auth.py          # Login/Register endpoints + nastavení
│       ├── user_qr.py       # QR generování pro uživatele
│       ├── verify.py        # Ověření QR kódu (turnstile scanner)
│       ├── credits.py       # Nákup kreditů
│       ├── payments.py      # Mock platby
│       ├── qr.py            # Starý QR endpoint (payment-based)
│       └── admin.py         # Admin dashboard
├── static/
│   ├── index.html           # Login/Register stránka
│   ├── dashboard.html       # User dashboard s QR kódem (Tailwind CSS, download QR)
│   ├── scanner.html         # QR scanner pro turnstile (moderní gym design)
│   ├── settings.html        # Nastavení účtu
│   ├── admin.html           # Admin dashboard
│   └── admin_login.html     # Admin přihlášení
├── ssl/                     # SSL certifikáty pro HTTPS
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Jak spustit (PostgreSQL + Docker Compose)

1. **Vytvoř `.env` a certifikáty:**
```bash
cp .env.example .env
bash generate_cert.sh  # volitelné pro HTTPS v lokálním běhu
```

2. **Spusť PostgreSQL a aplikaci:**
```bash
docker compose -f docker-compose.local.yml up -d
# první start stáhne image postgres:15-alpine a vytvoří volume postgres_data
```

3. **Sleduj logy / ověř běh:**
```bash
docker compose -f docker-compose.local.yml logs -f web
```

4. **Otevři v prohlížeči:**
- Login/Register: `https://localhost:8443`
- Dashboard: `https://localhost:8443/dashboard`
- Settings: `https://localhost:8443/settings`
- Scanner: `https://localhost:8443/scanner`
- Admin Login: `https://localhost:8443/admin/login`
- Admin Dashboard: `https://localhost:8443/admin`

**Poznámka:** Pokud nepotřebuješ HTTPS, API je dostupné i na `http://localhost:8181`. Kvůli self-signed certifikátům pro HTTPS bude prohlížeč zobrazovat varování – klikni na "Pokračovat" / "Advanced".

## API Endpoints

### Autentizace
- `POST /api/register` - Registrace nového uživatele
- `POST /api/login` - Přihlášení (vrací JWT token)
- `POST /api/logout` - Odhlášení
- `GET /api/user/info` - Informace o aktuálním uživateli (vyžaduje auth)
- `POST /api/user/change-password` - Změna hesla (vyžaduje auth)

### QR kódy a vstup
- `GET /api/my_qr` - Získání osobního QR kódu (vyžaduje auth)
- `POST /api/regenerate_qr` - Vygenerování nového QR kódu (vyžaduje auth)
- `POST /api/verify` - Ověření QR kódu (turnstile scanner)
  - Response: `{allowed: bool, reason: str, credits_left: int, cooldown_seconds_left: int | null}`
- **Frontend:** Tlačítko "Stáhnout QR" pro stažení QR kódu jako PNG obrázek

### Kredity
- `POST /api/buy_credits` - Nákup kreditů (vyžaduje auth)
- `GET /api/my_credits` - Zobrazení kreditů (vyžaduje auth)

### Admin
- `GET /api/admin/users/search` - Vyhledávání uživatelů (vyžaduje admin)
- `POST /api/admin/users/{user_id}/credits` - Přidání kreditů uživateli (vyžaduje admin)
- `GET /api/admin/users` - Seznam všech uživatelů (vyžaduje admin)

### Logs
- `GET /api/access_logs` - Access log (pro debugging/admin)

## Databázové modely

### User
- `id`, `email`, `name`, `password_hash`
- `credits` (Integer, default=0) - Počet kreditů
- `is_admin` (Boolean, default=False) - Admin práva
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
- `ip_address` (String, nullable) - IP adresa klienta
- `user_agent` (String, nullable) - User agent
- `created_at` (DateTime) - Čas pokusu o vstup

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
- `web` (FastAPI aplikace, porty mapované na `8181 -> 8000` a `8443 -> 443`)

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

**Poznámka:** `docker-compose.yml` je určený pro Coolify (řeší porty/SSL). Lokální HTTPS vyžaduje `docker-compose.local.yml` se self-signed certifikáty a Postgres službou.

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
- `JWT_SECRET_KEY` - Secret key pro JWT tokeny (důležité pro produkci!)
- `JWT_ALGORITHM` - Algorithm pro JWT (default: `HS256`)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Expirace tokenu v minutách (default: `60`)

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
