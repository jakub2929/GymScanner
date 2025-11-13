# Coolify Quick Start Guide

## Rychlý návod pro deployment na Coolify

### 1. Vytvoření aplikace v Coolify

1. Otevři Coolify dashboard
2. Klikni na **"New Resource"** → **"Application"**
3. Vyber **"GitHub"** (pokud máš repo) nebo **"Dockerfile"**
4. Pokud GitHub:
   - Připoj repository
   - **Branch:** `main`
   - **Build Pack:** `Dockerfile`
   - **Dockerfile Path:** `Dockerfile.production`
5. Pokud Dockerfile:
   - Upload `Dockerfile.production`

### 2. Nastavení Environment Proměnných

V Coolify → **Environment Variables** přidej:

```bash
# Database (PostgreSQL doporučeno)
DATABASE_URL=postgresql://user:password@postgres-host:5432/gymturnstile

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

### 3. Nastavení Portu

- **Port:** `8000`
- **Protocol:** `HTTP`

Coolify automaticky přidá HTTPS.

### 4. Přidání Domény

1. V Coolify → **Domains** přidej svou doménu
2. Coolify automaticky:
   - Nastaví SSL (Let's Encrypt)
   - Nakonfiguruje reverse proxy
3. Aktualizuj `COMGATE_RETURN_URL` a `COMGATE_NOTIFY_URL` na novou doménu

### 5. Deploy

Klikni na **"Deploy"** a počkej na dokončení.

### 6. Ověření

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

