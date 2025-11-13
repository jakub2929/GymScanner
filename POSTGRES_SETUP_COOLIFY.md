# Nastavení PostgreSQL v Coolify

## Problém: Coolify hází na GitHub App

Pokud Coolify při vytváření PostgreSQL databáze hází na GitHub App a nevidíš svoji databázi, zkus:

### Možnost 1: Vytvoř PostgreSQL jako samostatný Resource

1. V Coolify dashboard → **"Resources"** nebo **"Databases"**
2. Klikni **"New Resource"** → **"Database"** → **"PostgreSQL"**
3. Pokud to stále hází na GitHub App:
   - Zkus použít jiný způsob vytvoření
   - Nebo použij externí PostgreSQL (např. Supabase, Railway, Render)

### Možnost 2: Použij externí PostgreSQL (doporučeno)

Pokud nemůžeš vytvořit PostgreSQL v Coolify, použij externí službu:

#### Supabase (zdarma, doporučeno)
1. Jdi na https://supabase.com
2. Vytvoř účet a projekt
3. V Project Settings → Database → Connection String
4. Zkopíruj connection string (formát: `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`)

#### Railway (zdarma tier)
1. Jdi na https://railway.app
2. Vytvoř nový projekt → Add PostgreSQL
3. Získej connection string z Railway dashboard

#### Render (zdarma tier)
1. Jdi na https://render.com
2. New → PostgreSQL
3. Získej connection string

## Krok 1: Získej PostgreSQL Connection String

Connection string by měl vypadat takto:
```
postgresql://username:password@host:5432/database_name
```

Příklad:
```
postgresql://gymuser:gympass123@db.xxx.supabase.co:5432/postgres
```

## Krok 2: Nastav DATABASE_URL v Coolify

1. V Coolify → tvoje aplikace → **Environment Variables**
2. Přidej nebo uprav `DATABASE_URL`:
   ```bash
   DATABASE_URL=postgresql://username:password@host:5432/database_name
   ```
3. Ulož a redeploy aplikaci

## Krok 3: Ověření

1. Po redeploy zkontroluj logy aplikace
2. Mělo by se zobrazit: `Using database: postgresql://...`
3. Zkus se zaregistrovat - účet by se měl uložit do PostgreSQL

## Aplikace automaticky vytvoří tabulky

Aplikace automaticky vytvoří všechny potřebné tabulky při prvním spuštění:
- `users`
- `payments`
- `access_tokens`
- `access_logs`

**Nepotřebuješ** ručně vytvářet tabulky!

## Troubleshooting

### "Connection refused"
- Zkontroluj, že PostgreSQL databáze běží
- Zkontroluj, že host a port jsou správné
- Zkontroluj firewall (externí PostgreSQL musí být veřejně dostupná)

### "Authentication failed"
- Zkontroluj username a password v connection stringu
- Ujisti se, že heslo neobsahuje speciální znaky, které potřebují URL encoding

### "Database does not exist"
- Vytvoř databázi v PostgreSQL (nebo použij default `postgres`)
- Aplikace automaticky vytvoří tabulky, ale databáze musí existovat

### "SSL connection required"
Některé externí PostgreSQL služby vyžadují SSL. Přidej do connection stringu:
```
postgresql://user:pass@host:5432/db?sslmode=require
```

## Výhody PostgreSQL vs SQLite

✅ **Automaticky persistentní** - data se neztratí při redeploy  
✅ **Lepší výkon** - pro více uživatelů  
✅ **Lepší škálovatelnost** - podpora pro více serverů  
✅ **Bez volume** - nepotřebuješ nastavovat volume v Coolify

## Migrace z SQLite na PostgreSQL

Pokud už máš data v SQLite a chceš je přenést:

1. Exportuj data ze SQLite (SQL dump)
2. Importuj do PostgreSQL
3. Změň `DATABASE_URL` na PostgreSQL connection string
4. Redeploy aplikaci

**POZNÁMKA:** Aplikace automaticky vytvoří tabulky v PostgreSQL, ale data musíš přenést ručně.

