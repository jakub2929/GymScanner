# Environment Variables pro Coolify

Zkopíruj a vlož do Coolify dashboard → Environment Variables:

## Povinné proměnné

```bash
# Database (interní PostgreSQL kontejner z docker-compose)
# Výchozí hodnota v compose:
# postgresql+psycopg2://gymuser:superheslo@db:5432/gymdb
# Pokud chceš použít vlastní DB, přepiš proměnnou v Coolify
DATABASE_URL=postgresql+psycopg2://gymuser:superheslo@db:5432/gymdb

# JWT Authentication (vygeneruj silné heslo - min 32 znaků)
JWT_SECRET_KEY=tvoje_super_tajne_heslo_produkce_min_32_znaku_pro_jwt_tokeny

# JWT Algorithm (volitelné, default: HS256)
JWT_ALGORITHM=HS256

# JWT Token Expiration (volitelné, default: 60 minut)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

## Comgate Payment Gateway

```bash
# Comgate Credentials (získej z Comgate účtu)
COMGATE_MERCHANT_ID=tvuj_merchant_id
COMGATE_SECRET=tvuj_comgate_secret

# Comgate Test Mode (true pro testování, false pro produkci)
# Pro testování: COMGATE_TEST_MODE=true
# Pro produkci: COMGATE_TEST_MODE=false
COMGATE_TEST_MODE=true

# Comgate URLs (nahraď tvoje-domena.cz svou skutečnou doménou)
# POZNÁMKA: Nastav až po nasazení a získání domény z Coolify!
COMGATE_RETURN_URL=https://tvoje-domena.cz/api/payments/comgate/return
COMGATE_NOTIFY_URL=https://tvoje-domena.cz/api/payments/comgate/notify
```

## Volitelné proměnné

```bash
# Python (pro lepší logování)
PYTHONUNBUFFERED=1

# Environment (volitelné)
ENVIRONMENT=production
LOG_LEVEL=info
```

---

## Rychlý postup

1. **Nejdřív nastav povinné proměnné** (DATABASE_URL, JWT_SECRET_KEY)
2. **Deploy aplikaci** v Coolify
3. **Získej doménu** z Coolify (např. `gym-scanner.coolify.app`)
4. **Aktualizuj Comgate URLs** s tvou skutečnou doménou:
   ```
   COMGATE_RETURN_URL=https://gym-scanner.coolify.app/api/payments/comgate/return
   COMGATE_NOTIFY_URL=https://gym-scanner.coolify.app/api/payments/comgate/notify
   ```
5. **Restart aplikace** v Coolify

---

## Generování JWT_SECRET_KEY

Pro produkci vygeneruj silné heslo:

```bash
# Linux/Mac
openssl rand -hex 32

# Nebo použij online generátor
# https://randomkeygen.com/
```

Minimálně 32 znaků!
