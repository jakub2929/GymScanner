# Debug 404 Error v Coolify

## Krok 1: Zkontroluj logy v Coolify

1. V Coolify → tvoje aplikace → **Logs**
2. Hledej chyby při startu aplikace:
   - `Failed to initialize database`
   - `could not connect to server`
   - `ImportError`
   - `SyntaxError`
   - Jiné Python chyby

## Krok 2: Zkontroluj status aplikace

1. V Coolify → tvoje aplikace → **Status**
2. Mělo by být **Running** (zelené)
3. Pokud je **Stopped** nebo **Error**, aplikace se nespustila

## Krok 3: Zkus health check endpoint

Otevři v prohlížeči:
```
https://ko0k4okk0k8wc444os8880gw.93.91.159.48.sslip.io/health
```

**Očekávaná odpověď:**
```json
{
  "status": "healthy",
  "database": "connected",
  "app": "running"
}
```

**Pokud vrátí 404:**
- Aplikace se nespustila
- Zkontroluj logy (Krok 1)

**Pokud vrátí error:**
- Zkontroluj, jaký error (bude v response)
- Možná problém s databází

## Krok 4: Zkontroluj port v Coolify

1. V Coolify → tvoje aplikace → **Configuration**
2. Zkontroluj **Port** - měl by být **8000**
3. Zkontroluj **Protocol** - měl by být **HTTP**

## Krok 5: Zkontroluj DATABASE_URL

V Environment Variables zkontroluj:
```bash
DATABASE_URL=postgresql://postgres:password@host:5432/postgres
```

**DŮLEŽITÉ:**
- Musí začínat `postgresql://` (ne `postgres://`)
- Kód automaticky opraví `postgres://` na `postgresql://`, ale je lepší to mít správně

## Krok 6: Zkontroluj, že aplikace startuje

V logách by mělo být:
```
Starting application initialization...
Creating database tables...
Database tables created successfully
Database migrations completed
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Možné problémy:

### Aplikace se vůbec nespustila
- **Příčina:** Chyba při importu nebo inicializaci
- **Řešení:** Zkontroluj logy, hledej Python chyby

### Aplikace běží, ale 404
- **Příčina:** Špatný port nebo routing
- **Řešení:** Zkontroluj port v Coolify (mělo by být 8000)

### Databáze se nepřipojí
- **Příčina:** Špatný DATABASE_URL nebo databáze neběží
- **Řešení:** Zkontroluj connection string a status PostgreSQL databáze

### Health check funguje, ale hlavní stránka ne
- **Příčina:** Next.js frontend neběží nebo `FRONTEND_URL` míří na špatnou adresu
- **Řešení:** Ověř, že Next.js dev/prod server běží (`npm run dev` nebo frontend Docker image) a proměnná `FRONTEND_URL` ukazuje na správnou doménu (`http://localhost:3000` lokálně)

## Co jsem přidal do kódu:

1. **Lepší error handling** - aplikace zaloguje chyby při startu
2. **Lepší health check** - zobrazí status databáze
3. **Debug logy** - více informací o startu aplikace

Po redeploy zkontroluj logy - měly by ukázat, kde je problém!
