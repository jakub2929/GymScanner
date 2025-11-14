# Deployment na Coolify

## Přehled

Tato aplikace je připravena pro deployment na Coolify. Coolify je self-hosted platforma pro deployment aplikací, která automaticky řeší SSL certifikáty, reverse proxy a další infrastrukturu.

## Požadavky

- Coolify instance (self-hosted nebo cloud)
- PostgreSQL databáze (povinné pro produkci i lokální běh)
- Veřejná doména pro aplikaci (kvůli HTTPS a Comgate callbackům)

## Krok 1: Příprava databáze

V Coolify vytvoř PostgreSQL databázi:
- Database name: `gymturnstile`
- User: `gymuser`
- Password: `gympass` (nebo silnější heslo)

Získej connection string:
```
postgresql://gymuser:gympass@postgres-host:5432/gymturnstile
```

Pokud potřebuješ offline/debug režim se SQLite, podívej se na `SQLITE_SETUP.md`. Produkční nasazení vyžaduje PostgreSQL.

## Krok 2: Vytvoření aplikace v Coolify

1. V Coolify dashboard klikni na "New Resource" → "Application"
2. Vyber "GitHub" nebo "Dockerfile"
3. Pokud GitHub:
   - Připoj svůj GitHub repository
   - Branch: `main` (nebo jiný)
   - **Build Pack: `Dockerfile`** – **NEPOUŽÍVEJ Docker Compose!**
   - Dockerfile path: `Dockerfile.production`
4. Pokud Dockerfile:
   - Upload nebo zadej Dockerfile.production obsah

**DŮLEŽITÉ:** 
- **NEPOUŽÍVEJ** `docker-compose.yml` v Coolify (Coolify spravuje porty sám)
- Použij **pouze** `Dockerfile.production` přímo
- Coolify automaticky řeší networking, reverse proxy a porty (používá EXPOSE z Dockerfile)
- `docker-compose.yml` už nemá `ports` sekci - Coolify to řeší sám

## Krok 3: Nastavení environment proměnných

V Coolify dashboard → Environment Variables nastav:

### Povinné proměnné:

```bash
# Database
DATABASE_URL=postgresql://gymuser:gympass@postgres-host:5432/gymturnstile

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
```

### Volitelné proměnné:

```bash
PYTHONUNBUFFERED=1  # Pro lepší logování
```

## Krok 4: Nastavení portů

Coolify automaticky detekuje port z Dockerfile (8000). Pokud ne, nastav:
- **Port:** 8000
- **Protocol:** HTTP

Coolify automaticky přidá HTTPS přes reverse proxy.

## Krok 5: Nastavení domény

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

## Krok 6: Volumes

PostgreSQL data spravuj přímo ve službě Coolify (sekce Databases) – Coolify vytvoří persistentní storage automaticky. Volume pro aplikaci nejsou potřeba. Pokud někdy použiješ SQLite fallback, přidej volume dle `SQLITE_SETUP.md`.

## Krok 7: Health Check

Coolify automaticky použije health check endpoint:
- **URL:** `/health`
- **Interval:** 30s

## Krok 8: Deploy

1. Klikni na "Deploy" v Coolify
2. Coolify:
   - Buildne Docker image
   - Spustí kontejner
   - Nastaví reverse proxy
   - Aktivuje SSL certifikát

## Po deploy

### Ověření

1. Otevři `https://tvoje-domena.cz/health` → mělo by vrátit `{"status": "healthy"}`
2. Otevři `https://tvoje-domena.cz/` → měla by se zobrazit login stránka

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
