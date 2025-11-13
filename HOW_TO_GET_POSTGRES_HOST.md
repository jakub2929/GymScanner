# Jak získat PostgreSQL host v Coolify

## Krok 1: Najdi PostgreSQL databázi v Coolify

1. Otevři **Coolify dashboard**
2. V levém menu klikni na **"Resources"** nebo **"Databases"**
3. Najdi svou **PostgreSQL databázi** (pokud ji ještě nemáš, musíš ji vytvořit)

## Krok 2: Získej Connection String

### Možnost A: Z Coolify Dashboard (nejjednodušší)

1. Klikni na svou **PostgreSQL databázi**
2. Najdi sekci **"Connection String"** nebo **"Connection Details"**
3. Zkopíruj celý connection string - měl by vypadat nějak takto:
   ```
   postgresql://gymuser:gympass@postgres-xxx.coolify.internal:5432/gymturnstile
   ```
   nebo
   ```
   postgresql://gymuser:gympass@postgres-xxx:5432/gymturnstile
   ```

### Možnost B: Z Environment Variables PostgreSQL kontejneru

1. Klikni na PostgreSQL databázi
2. Jdi na **"Environment Variables"**
3. Najdi proměnné jako:
   - `POSTGRES_HOST` nebo `POSTGRES_SERVICE_HOST`
   - `POSTGRES_PORT` (obvykle 5432)
   - `POSTGRES_DB` (název databáze)
   - `POSTGRES_USER` (uživatel)
   - `POSTGRES_PASSWORD` (heslo)

4. Sestav connection string:
   ```
   postgresql://POSTGRES_USER:POSTGRES_PASSWORD@POSTGRES_HOST:POSTGRES_PORT/POSTGRES_DB
   ```

### Možnost C: Z Docker Network (pokud jsou oba kontejnery ve stejné síti)

Pokud máš aplikaci a PostgreSQL ve stejné Coolify aplikaci/síti, můžeš použít:
- **Service name** jako host (např. `postgres` nebo `postgres-db`)
- Coolify automaticky vytvoří DNS pro kontejnery ve stejné síti

Příklad:
```
postgresql://gymuser:gympass@postgres:5432/gymturnstile
```

## Krok 3: Vytvoř PostgreSQL databázi (pokud ji ještě nemáš)

1. V Coolify → **"New Resource"** → **"Database"** → **"PostgreSQL"**
2. Nastav:
   - **Name**: `gymturnstile` (nebo jak chceš)
   - **Database**: `gymturnstile`
   - **User**: `gymuser`
   - **Password**: `gympass` (nebo silnější heslo)
3. Deploy databázi
4. Po deploy získej connection string (viz Krok 2)

## Krok 4: Zkopíruj DATABASE_URL do aplikace

1. Jdi do své **aplikace** v Coolify
2. **Environment Variables**
3. Přidej nebo uprav `DATABASE_URL` s connection stringem z PostgreSQL databáze

## Příklady connection stringů

### Coolify internal network (doporučeno):
```
postgresql://gymuser:gympass@postgres-xxx.coolify.internal:5432/gymturnstile
```

### Service name (pokud jsou ve stejné síti):
```
postgresql://gymuser:gympass@postgres:5432/gymturnstile
```

### Externí IP (pokud je PostgreSQL na jiném serveru):
```
postgresql://gymuser:gympass@192.168.1.100:5432/gymturnstile
```

## Troubleshooting

### "Connection refused" nebo "Host not found"
- Zkontroluj, že PostgreSQL databáze běží v Coolify
- Zkontroluj, že používáš správný host (service name nebo internal host)
- Zkontroluj, že port je 5432

### "Authentication failed"
- Zkontroluj username a password
- Zkontroluj, že uživatel má oprávnění k databázi

### "Database does not exist"
- Zkontroluj název databáze v connection stringu
- Vytvoř databázi, pokud neexistuje

