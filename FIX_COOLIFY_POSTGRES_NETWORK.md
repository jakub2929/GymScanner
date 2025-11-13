# Oprava: PostgreSQL Connection v Coolify - Network Issue

## Problém:

Coolify automaticky generuje `DATABASE_URL` s internal hostname, který se nedá přeložit:
```
postgres://postgres:password@kgo0ksc40s8k84wg4kwk0cso:5432/postgres
```

Chyba:
```
could not translate host name "kgo0ksc40s8k84wg4kwk0cso" to address: Temporary failure in name resolution
```

## Příčina:

Aplikace a PostgreSQL databáze **nejsou ve stejné síti** v Coolify. Internal hostname funguje jen v rámci Coolify sítě.

## Řešení:

### Možnost 1: Připoj PostgreSQL k aplikaci jako Resource (doporučeno)

1. V Coolify → tvoje aplikace → **Resources** nebo **Services**
2. Klikni **"Add Resource"** nebo **"Link Resource"**
3. Vyber svou **PostgreSQL databázi**
4. Coolify automaticky:
   - Připojí databázi k aplikaci
   - Vytvoří environment variables s správným connection stringem
   - Nastaví síť, aby aplikace mohla komunikovat s databází

### Možnost 2: Zkontroluj, že jsou ve stejné síti

1. V Coolify → PostgreSQL databáze → **Networking** nebo **Settings**
2. Zkontroluj **Network** nebo **Service Name**
3. V aplikaci → **Environment Variables**
4. Zkontroluj, že `DATABASE_URL` používá správný service name nebo internal hostname

**Service name** by měl být něco jako:
- `postgres` (pokud je to default service name)
- `postgres-db` (pokud jsi to pojmenoval)
- `kgo0ksc40s8k84wg4kwk0cso` (internal hostname - měl by fungovat, pokud jsou ve stejné síti)

### Možnost 3: Použij SQLite (dočasné řešení)

Pokud nemůžeš opravit PostgreSQL síť:

1. V Coolify → Environment Variables
2. **Přepiš** `DATABASE_URL` (i když je automaticky generovaný):
   ```bash
   DATABASE_URL=sqlite:///./data/gym_turnstile.db
   ```
3. Přidej Volume:
   - Path: `/app/data`
   - Mount: `gymturnstile-data`
4. Redeploy

**POZNÁMKA:** Coolify může automaticky přepisovat `DATABASE_URL` při redeploy. Pokud se to stane, použij Možnost 1 nebo 2.

### Možnost 4: Zkontroluj PostgreSQL status

1. V Coolify → PostgreSQL databáze → **Status**
2. Mělo by být **Running** (zelené)
3. Pokud ne, restartuj databázi

## Ověření:

Po opravě zkontroluj logy:
```
Database connection successful
Database tables created successfully
```

## Proč to nefunguje:

- **Internal hostname** (`kgo0ksc40s8k84wg4kwk0cso`) funguje jen v rámci Coolify Docker sítě
- Pokud aplikace a PostgreSQL nejsou ve stejné síti, hostname se nedá přeložit
- Coolify automaticky vytvoří síť, když přidáš PostgreSQL jako Resource k aplikaci

## Nejlepší řešení:

**Přidej PostgreSQL jako Resource k aplikaci** - Coolify to automaticky vyřeší!

