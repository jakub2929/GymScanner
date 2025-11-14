# Coolify Quick Start Guide

## Rychlý návod pro deployment na Coolify

### 1. Vytvoření aplikace v Coolify

1. Otevři Coolify dashboard
2. Klikni na **"New Resource"** → **"Application"**
3. Vyber **"Git repository"** (nebo GitHub)
4. Zdroj: toto repo, **Branch:** `main`
5. Build pack: **Docker Compose**
6. **Compose file path:** `docker-compose.yml`
7. Coolify vytvoří dvě služby:
   - `web` (FastAPI) → používá `Dockerfile.production`
   - `db` (PostgreSQL 15-alpine with persistent volume `gym-db-data`)

### 2. Nastavení Environment Proměnných

V Coolify → **Environment Variables** přidej:

```bash
# Database (vnitřní Postgres z docker-compose)
DATABASE_URL=postgresql+psycopg2://gymuser:superheslo@db:5432/gymdb

# JWT (ZMIŇ NA SILNÉ HESLO!)
JWT_SECRET_KEY=tvoje_super_tajne_heslo_min_32_znaku_produkce
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Comgate
COMGATE_MERCHANT_ID=tvuj_merchant_id
COMGATE_SECRET=tvuj_secret
COMGATE_TEST_MODE=false
COMGATE_RETURN_URL=https://tvoje-domena.cz/api/payments/comgate/return
COMGATE_NOTIFY_URL=https://tvoje-domena.cz/api/payments/comgate/notify

# App
ENVIRONMENT=production
LOG_LEVEL=info
PYTHONUNBUFFERED=1
```

### 3. Přidání Domény

1. V Coolify → **Domains** přidej svou doménu
2. Coolify automaticky:
   - Nastaví SSL (Let's Encrypt)
   - Nakonfiguruje reverse proxy
3. Aktualizuj `COMGATE_RETURN_URL` a `COMGATE_NOTIFY_URL` na novou doménu

### 4. Deploy

Klikni na **"Deploy"** a počkej na dokončení.

### 5. Ověření

- Otevři `https://tvoje-domena.cz/health` → `{"status": "healthy"}`
- Otevři `https://tvoje-domena.cz/` → Login stránka

## Troubleshooting

**Aplikace se nespustí?**
- Zkontroluj logy v Coolify
- Ověř všechny environment proměnné
- Zkontroluj, že databáze běží

**Database error?**
- Ověř `DATABASE_URL` formát
- Zkontroluj network connectivity

**Comgate notifikace?**
- Ověř, že `COMGATE_NOTIFY_URL` je veřejně dostupná
- Zkontroluj logy pro POST requesty

## Více informací

Detailní návod: [DEPLOY.md](./DEPLOY.md)
