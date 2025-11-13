# Jak propojit PostgreSQL s aplikací v Coolify

## Problém:

Aplikace a PostgreSQL jsou ve stejném prostředí, ale nejsou propojené, takže aplikace nemůže komunikovat s databází.

## Řešení - Propojení v Coolify:

### Krok 1: Otevři aplikaci

1. V Coolify → **GymScanner > production > Resources**
2. Klikni na aplikaci: `jakub2929/-gym-scanner:main-...`

### Krok 2: Přidej PostgreSQL jako Resource

1. V aplikaci najdi sekci **"Resources"** nebo **"Services"** nebo **"Linked Resources"**
2. Klikni **"+ Add Resource"** nebo **"Link Resource"**
3. Vyber: `postgresql-database-kgo0ksc40s8k84wg4kwk0cso`
4. Ulož

### Alternativní způsob:

1. V aplikaci → **Configuration** → **Environment Variables**
2. Coolify by měl automaticky přidat proměnné pro propojené resources
3. Nebo přidej ručně:
   - Najdi správný connection string z PostgreSQL konfigurace
   - Použij internal URL: `postgres://postgresql:xU1iNzI1bDgSAkkIExHXzUisr88Xr5M9blbLjeKFBrUaoizYrRxgbUO0POm1sAmz@kgo0ksc40s8k84wg4kwk0cso:5432/postgres`

### Krok 3: Zkontroluj Network

1. V aplikaci → **Configuration** → **Network**
2. Zkontroluj, že aplikace a PostgreSQL jsou ve stejné síti
3. Pokud ne, Coolify by měl automaticky vytvořit síť při propojení

### Krok 4: Restart aplikace

Po propojení:
1. Restart aplikaci
2. Zkontroluj logy - mělo by se zobrazit: `Database connection successful`

## Co se stane po propojení:

- Coolify automaticky vytvoří síť mezi aplikací a databází
- Internal hostname `kgo0ksc40s8k84wg4kwk0cso` bude fungovat
- Aplikace se bude moci připojit k PostgreSQL

## Pokud to stále nefunguje:

1. Zkontroluj, že PostgreSQL běží (status: Running)
2. Zkontroluj logy aplikace - měly by ukázat, jestli se připojila
3. Zkontroluj, že `DATABASE_URL` je správně nastavený

## Poznámka:

Kód automaticky opraví `postgres://` na `postgresql://`, takže to není problém. Hlavní problém je síťové propojení mezi aplikací a databází.

