# SQLite Setup pro Coolify (bez PostgreSQL)

Pokud nemůžeš vytvořit PostgreSQL databázi v Coolify, použij SQLite. Aplikace ho podporuje a funguje bez další konfigurace.

## Environment Variables pro SQLite

V Coolify → Environment Variables nastav:

```bash
# SQLite Database (nejjednodušší řešení)
DATABASE_URL=sqlite:///./data/gym_turnstile.db

# JWT Authentication
JWT_SECRET_KEY=22316a650ece222be8b494406413e5ee93d213455ae2a0f3c2d037139e1922a3
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Comgate Payment Gateway
COMGATE_MERCHANT_ID=123456
COMGATE_SECRET=gx4q8OV3TJt6noJnfhjqJKyX3Z6Ych0y
COMGATE_TEST_MODE=true
COMGATE_RETURN_URL=https://ko0k4okk0k8wc444os8880gw.93.91.159.48.sslip.io/api/payments/comgate/return
COMGATE_NOTIFY_URL=https://ko0k4okk0k8wc444os8880gw.93.91.159.48.sslip.io/api/payments/comgate/notify

# Python
PYTHONUNBUFFERED=1
```

## Volumes v Coolify (volitelné, ale doporučeno)

Pro persistentní data (aby se databáze neztratila při restartu):

1. V Coolify → tvoje aplikace → **Volumes**
2. Přidej volume:
   - **Path**: `/app/data`
   - **Mount**: `gymturnstile-data` (nebo jakýkoliv název)

**POZNÁMKA:** Pokud nepřidáš volume, databáze se vytvoří v kontejneru, ale ztratí se při restartu/redeploy. Pro testování to stačí, pro produkci přidej volume.

## Výhody SQLite

✅ **Jednoduché** - žádná další konfigurace  
✅ **Rychlé** - perfektní pro malé až střední aplikace  
✅ **Bez závislostí** - nepotřebuješ externí databázi  
✅ **Okamžitě funkční** - jen nastav DATABASE_URL a jede to

## Nevýhody SQLite

❌ **Není pro velké aplikace** - limit na velikost databáze  
❌ **Není pro vysoký load** - nepodporuje mnoho současných připojení  
❌ **Není pro produkci s více servery** - SQLite je lokální soubor

## Kdy použít SQLite vs PostgreSQL

### SQLite je vhodné pro:
- ✅ Testování a vývoj
- ✅ Malé aplikace (do ~1000 uživatelů)
- ✅ Aplikace s nízkým loadem
- ✅ Když nemůžeš vytvořit PostgreSQL databázi

### PostgreSQL je vhodné pro:
- ✅ Produkční aplikace
- ✅ Vysoký load (mnoho současných uživatelů)
- ✅ Více serverů (scaling)
- ✅ Velké množství dat

## Migrace z SQLite na PostgreSQL (později)

Když budeš moct vytvořit PostgreSQL databázi:

1. Vytvoř PostgreSQL databázi v Coolify
2. Získej connection string
3. Změň `DATABASE_URL` na PostgreSQL connection string
4. Restartuj aplikaci
5. Aplikace automaticky vytvoří tabulky v PostgreSQL

**POZNÁMKA:** Data ze SQLite se nepřenesou automaticky - budeš muset exportovat/importovat ručně, nebo začít s prázdnou databází.

