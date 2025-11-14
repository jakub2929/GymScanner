# Deployment na Coolify

## Přehled

Tato aplikace je připravena pro deployment na Coolify. Coolify je self-hosted platforma pro deployment aplikací, která automaticky řeší SSL certifikáty, reverse proxy a další infrastrukturu.

## Požadavky

- Coolify instance (self-hosted nebo cloud)
- PostgreSQL databáze (povinné pro produkci i lokální běh)
- Veřejná doména pro aplikaci (kvůli HTTPS a Comgate callbackům)

## Architektura

Repo nyní obsahuje tyto služby:

1. **FastAPI backend** (`services.web` v compose) – poskytuje REST API, generuje QR kódy a komunikuje s PostgreSQL. Build jede přes `Dockerfile.production`.
2. **PostgreSQL databáze** (`services.db` v compose) – `postgres:15-alpine` se persistentním volume `gym-db-data`.
3. **Next.js frontend** (složka `frontend/`) – moderní React/TypeScript UI s Apple “liquid glass” designem. Deployuje se jako samostatná Node.js aplikace (Dockerfile v `frontend/Dockerfile`) a komunikuje s backendem přes `NEXT_PUBLIC_API_URL`.

Na Coolify typicky vytváříme:
- Jednu aplikaci typu **Docker Compose** pro backend + databázi (použije kořenový `docker-compose.yml`).
- Druhou aplikaci pro Next.js frontend.

## Krok 1: Příprava databáze

`docker-compose.yml` nyní obsahuje databázový kontejner `db` (PostgreSQL 15) s persistentním volume. Coolify Compose deployment tak spustí databázi automaticky vedle backendu. Výchozí connection string v compose:

```
postgresql+psycopg2://gymuser:superheslo@db:5432/gymdb
```

Můžeš ho přepsat v Coolify přes Environment → `DATABASE_URL` (např. pokud chceš externí databázi). Pro většinu instalací ale stačí vestavěná služba `db`.

## Krok 2: Backend aplikace v Coolify (Docker Compose)

1. V Coolify klikni na **New Resource → Application**
2. Zdroj: Git repozitář (nebo GitHub) → vyber toto repo
3. Branch: `main` (nebo tvůj production branch)
4. Build pack: **Docker Compose**
5. `Compose file path`: `docker-compose.yml`
6. Coolify automaticky vytvoří dvě služby (web + db) a připojí persistentní volume `gym-db-data`
7. Deploy target: `api.tvoje-domena.cz`

## Krok 3: Frontend (Next.js) aplikace v Coolify

1. Vytvoř druhou aplikaci (New Resource → Application).
2. Branch: `main`.
3. **Build pack:** Dockerfile
4. **Dockerfile path:** `frontend/Dockerfile`
5. V sekci Environment přidej `NEXT_PUBLIC_API_URL=https://api.tvoje-domena.cz` (musí směřovat na veřejnou URL FastAPI backendu – použije se už při build-time).
6. Zvol doménu např. `app.tvoje-domena.cz`.
7. Port z Dockerfile je 3000 → Coolify jej připojí na reverse proxy (HTTPS terminace probíhá v Coolify).

Next.js Docker image používá production build (`npm run build`) a `output: standalone`, takže běží jako Node server uvnitř kontejneru.

## Krok 4: Nastavení environment proměnných

### Backend (FastAPI)

V Coolify dashboard → Environment Variables služby backendu nastav:

```bash
# Database (vestavěný Postgres kontejner)
DATABASE_URL=postgresql+psycopg2://gymuser:superheslo@db:5432/gymdb

# JWT
JWT_SECRET_KEY=tvoje_super_tajne_heslo_produkce_min_32_znaku
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Comgate
COMGATE_MERCHANT_ID=tvuj_merchant_id
COMGATE_SECRET=tvuj_comgate_secret
COMGATE_TEST_MODE=false  # true pro testování, false pro produkci
COMGATE_RETURN_URL=https://tvoje-domena.cz/api/payments/comgate/return
COMGATE_NOTIFY_URL=https://tvoje-domena.cz/api/payments/comgate/notify

# App
ENVIRONMENT=production
LOG_LEVEL=info
FRONTEND_URL=https://app.tvoje-domena.cz
```

### Volitelné proměnné:

```bash
PYTHONUNBUFFERED=1  # Pro lepší logování
```

### Frontend (Next.js)

U frontend aplikace přidej minimálně:

```bash
NEXT_PUBLIC_API_URL=https://api.tvoje-domena.cz  # veřejná URL FastAPI aplikace
NEXT_TELEMETRY_DISABLED=1
```

Pamatuj, že `NEXT_PUBLIC_API_URL` se propisuje během buildu, takže změna cílové API URL vyžaduje nový build/redeploy frontend služby.

## Krok 5: Nastavení portů

Coolify automaticky detekuje port z Dockerfile (8000). Pokud ne, nastav:
- **Port:** 8000
- **Protocol:** HTTP

Coolify automaticky přidá HTTPS přes reverse proxy.

Frontend Dockerfile vystavuje port 3000 – Coolify jej mapuje na HTTPS doménu automaticky.

## Krok 6: Nastavení domény

1. V Coolify → Domains přidej svou doménu
2. Coolify automaticky:
   - Nastaví SSL certifikát (Let's Encrypt)
   - Nakonfiguruje reverse proxy
   - Přesměruje HTTP → HTTPS

3. Aktualizuj environment proměnné:
   ```
   COMGATE_RETURN_URL=https://tvoje-domena.cz/api/payments/comgate/return
   COMGATE_NOTIFY_URL=https://tvoje-domena.cz/api/payments/comgate/notify
   ```

Pro přehledné oddělení doporučujeme:
- `api.tvoje-domena.cz` → FastAPI backend
- `app.tvoje-domena.cz` → Next.js frontend (`NEXT_PUBLIC_API_URL` musí mířit na první doménu)

## Krok 7: Volumes

Docker Compose definuje volume `gym-db-data`, které Coolify vytvoří automaticky při deployi a připojí k `/var/lib/postgresql/data`. Není potřeba zakládat samostatnou DB službu v Coolify. Pokud někdy použiješ SQLite fallback, přidej volume dle `SQLITE_SETUP.md`.

## Krok 8: Health Check

Coolify automaticky použije health check endpoint:
- **URL:** `/health`
- **Interval:** 30s

U frontend služby můžeš volitelně nastavit `/` s očekávaným HTTP 200 (Next.js odpověď).

## Krok 9: Deploy

1. Klikni na "Deploy" v Coolify
2. Coolify:
   - Buildne Docker image
   - Spustí kontejner
   - Nastaví reverse proxy
   - Aktivuje SSL certifikát

## Po deploy

### Ověření

**API**
1. Otevři `https://api.tvoje-domena.cz/health` → mělo by vrátit `{"status": "healthy"}`.
2. Ověř `/admin/login` nebo `/docs` podle potřeby.

**Frontend**
1. Otevři `https://app.tvoje-domena.cz/login` → zobrazí se Apple glass přihlášení.
2. Registruj / přihlaš se, ujisti se že requests míří na `https://api.tvoje-domena.cz`.

### Migrace databáze

Aplikace automaticky vytvoří tabulky při prvním spuštění. Pokud používáš PostgreSQL, tabulky se vytvoří automaticky.

### Testování

1. Zaregistruj nového uživatele
2. Přihlas se
3. Ověř, že QR kód se zobrazuje
4. Otestuj nákup tokenů (v testovacím režimu Comgate)

## Troubleshooting

### Aplikace se nespustí

1. Zkontroluj logy v Coolify: `Logs` tab
2. Ověř, že všechny environment proměnné jsou nastavené
3. Zkontroluj, že databáze je dostupná

### Database connection error

1. Ověř `DATABASE_URL` formát
2. Zkontroluj, že PostgreSQL kontejner běží
3. Ověř network connectivity mezi aplikací a databází

### Comgate notifikace nefungují

1. Ověř, že `COMGATE_NOTIFY_URL` je správně nastavená (veřejná doména)
2. Zkontroluj, že URL je dostupná z internetu
3. Ověř logy v Coolify pro POST requesty na `/api/payments/comgate/notify`

### SSL certifikát

Coolify automaticky řeší SSL přes Let's Encrypt. Pokud máš problémy:
1. Zkontroluj DNS záznamy (A record na IP Coolify serveru)
2. Ověř, že port 80 a 443 jsou otevřené
3. Zkontroluj logy v Coolify

## Backup

### Databáze (PostgreSQL)

```bash
# Export
pg_dump $DATABASE_URL > backup.sql

# Import
psql $DATABASE_URL < backup.sql
```

### Legacy SQLite

Pouze pokud běžíš na dočasném SQLite fallbacku (viz `SQLITE_SETUP.md`):

```bash
cp /app/data/gym_turnstile.db backup.db
```

## Aktualizace aplikace

1. Pushni změny do Git repository
2. V Coolify klikni na "Redeploy"
3. Coolify automaticky:
   - Buildne novou verzi
   - Spustí nový kontejner
   - Přepne provoz na novou verzi

## Monitoring

Coolify poskytuje:
- **Logs:** Real-time logy aplikace
- **Metrics:** CPU, RAM, Network usage
- **Health:** Status aplikace

## Bezpečnost

-  HTTPS automaticky přes Coolify
-  Environment proměnné jsou šifrované
-  JWT secret key v environment proměnných
-  Comgate secret v environment proměnných
- Změň `JWT_SECRET_KEY` na silné heslo pro produkci
- Použij silné heslo pro PostgreSQL

## Podpora

Pro problémy s Coolify: https://coolify.io/docs
Pro problémy s aplikací: zkontroluj logy v Coolify dashboard
