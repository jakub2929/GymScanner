# Oprava 404 Error v Coolify

## Problém 1: DATABASE_URL má špatný formát

Tvůj `DATABASE_URL` má `postgres://` místo `postgresql://`:

**ŠPATNĚ:**
```bash
DATABASE_URL=postgres://postgres:password@host:5432/postgres
```

**SPRÁVNĚ:**
```bash
DATABASE_URL=postgresql://postgres:password@host:5432/postgres
```

### Oprava:

V Coolify → Environment Variables změň:
```bash
DATABASE_URL=postgresql://postgres:xU1iNzI1bDgSAkklExHXzUisr88Xr5M9bIbLjeKFBrUaoizYrRxgbUO0POm1sAmz@kgo0ksc40s8k84wg4kwk0cso:5432/postgres
```

**DŮLEŽITÉ:** Změň `postgres://` na `postgresql://`!

## Problém 2: Aplikace se možná nespustila

404 error může znamenat, že aplikace se nespustila kvůli chybě.

### Zkontroluj logy v Coolify:

1. V Coolify → tvoje aplikace → **Logs**
2. Hledej chyby jako:
   - `RuntimeError: DATABASE_URL is not set`
   - `OperationalError: could not connect to server`
   - `ImportError` nebo jiné Python chyby

### Zkontroluj, že aplikace běží:

1. V Coolify → tvoje aplikace → **Status**
2. Mělo by být **Running** (zelené)
3. Pokud je **Stopped** nebo **Error**, zkontroluj logy

## Problém 3: Health check endpoint

Zkus otevřít:
```
https://ko0k4okk0k8wc444os8880gw.93.91.159.48.sslip.io/health
```

Mělo by vrátit:
```json
{"status": "healthy"}
```

Pokud to nefunguje, aplikace se nespustila.

## Krok za krokem - Oprava:

### 1. Oprav DATABASE_URL

V Coolify → Environment Variables:
```bash
# ZMĚŇ postgres:// na postgresql://
DATABASE_URL=postgresql://postgres:xU1iNzI1bDgSAkklExHXzUisr88Xr5M9bIbLjeKFBrUaoizYrRxgbUO0POm1sAmz@kgo0ksc40s8k84wg4kwk0cso:5432/postgres
```

### 2. Zkontroluj logy

V Coolify → Logs → hledej chyby

### 3. Restart aplikace

Po změně DATABASE_URL:
- Restart nebo Redeploy aplikaci

### 4. Ověř

1. Zkus `/health` endpoint
2. Zkus hlavní stránku `/`
3. Zkontroluj logy, jestli se aplikace připojila k databázi

## Možné další problémy:

### "Connection refused"
- PostgreSQL databáze neběží
- Špatný host nebo port
- Firewall blokuje připojení

### "Authentication failed"
- Špatné heslo v connection stringu
- Uživatel nemá oprávnění

### "Database does not exist"
- Databáze `postgres` neexistuje
- Vytvoř databázi nebo použij jinou

### "SSL connection required"
Některé PostgreSQL služby vyžadují SSL. Přidej:
```
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

## Kompletní správné Environment Variables:

```bash
SERVICE_FQDN_WEB=ko0k4okk0k8wc444os8880gw.93.91.159.48.sslip.io
SERVICE_URL_WEB=http://ko0k4okk0k8wc444os8880gw.93.91.159.48.sslip.io

COMGATE_MERCHANT_ID=123456
COMGATE_NOTIFY_URL=https://ko0k4okk0k8wc444os8880gw.93.91.159.48.sslip.io/api/payments/comgate/notify
COMGATE_RETURN_URL=https://ko0k4okk0k8wc444os8880gw.93.91.159.48.sslip.io/api/payments/comgate/return
COMGATE_SECRET=gx4q8OV3TJt6noJnfhjqJKyX3Z6Ych0y
COMGATE_TEST_MODE=true

# DŮLEŽITÉ: postgresql:// ne postgres://
DATABASE_URL=postgresql://postgres:xU1iNzI1bDgSAkklExHXzUisr88Xr5M9bIbLjeKFBrUaoizYrRxgbUO0POm1sAmz@kgo0ksc40s8k84wg4kwk0cso:5432/postgres

JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_ALGORITHM=HS256
JWT_SECRET_KEY=22316a650ece222be8b494406413e5ee93d213455ae2a0f3c2d037139e1922a3

PYTHONUNBUFFERED=1
```
