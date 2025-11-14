# Oprava: PostgreSQL Connection Error

## Chyba:
```
could not translate host name "kgo0ksc40s8k84wg4kwk0cso" to address: Temporary failure in name resolution
```

## Problém:

Aplikace se nemůže připojit k PostgreSQL databázi, protože:
1. Hostname je internal Coolify hostname, který funguje jen v rámci Coolify sítě
2. Aplikace a PostgreSQL databáze nejsou ve stejné síti
3. Nebo PostgreSQL databáze neběží

## Řešení:

### Možnost 1: Zkontroluj, že aplikace a PostgreSQL jsou ve stejné síti

1. V Coolify → tvoje aplikace → **Networking** nebo **Settings**
2. Zkontroluj, že aplikace a PostgreSQL databáze jsou ve **stejné síti**
3. Pokud ne, přidej PostgreSQL databázi jako **Resource** do stejné aplikace

### Možnost 2: Použij správný connection string

Pokud máš PostgreSQL jako samostatný resource:

1. V Coolify → PostgreSQL databáze → **Connection String**
2. Zkopíruj connection string
3. V aplikaci → Environment Variables → nastav `DATABASE_URL`

**DŮLEŽITÉ:** Connection string by měl obsahovat:
- Pro internal network: `postgresql://user:pass@postgres-service-name:5432/dbname`
- Nebo: `postgresql://user:pass@postgres-xxx.coolify.internal:5432/dbname`

### Možnost 4: Zkontroluj, že PostgreSQL běží

1. V Coolify → PostgreSQL databáze → **Status**
2. Mělo by být **Running** (zelené)
3. Pokud ne, restartuj databázi

## Co jsem upravil v kódu:

Aplikace nyní:
- ✅ Nezcrashne při chybě připojení k databázi
- ✅ Zaloguje jasnou chybovou zprávu
- ✅ Spustí se i když databáze není dostupná (ale funkce nebudou fungovat)
- ✅ Zobrazí užitečné tipy v logách

## Ověření:

Po opravě zkontroluj logy:
```
Database connection successful
Database tables created successfully
```

Nebo pokud stále nefunguje:
```
Database connection failed: ...
Please check:
1. DATABASE_URL is correct
2. PostgreSQL database is running
3. Network connectivity between app and database
```

## Nejčastější příčiny:

1. **Aplikace a PostgreSQL nejsou ve stejné síti**
   - Řešení: Přidej PostgreSQL jako resource do stejné aplikace

2. **Špatný hostname v DATABASE_URL**
   - Řešení: Použij service name nebo internal hostname z Coolify

3. **PostgreSQL databáze neběží**
   - Řešení: Restartuj databázi v Coolify

4. **Firewall blokuje připojení**
   - Řešení: Zkontroluj firewall nastavení v Coolify
