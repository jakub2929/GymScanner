# Jak nastavit admina

## Metoda 1: Python skript (doporučeno)

### Lokálně (pokud máš přístup k serveru):

1. Připoj se k serveru nebo otevři terminál v lokálním prostředí
2. Nastav `DATABASE_URL`:
   ```bash
   export DATABASE_URL="sqlite:///./data/gym_turnstile.db"
   # nebo pro PostgreSQL:
   export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
   ```
3. Spusť skript:
   ```bash
   python set_admin.py <tvuj-email>
   ```
   
   Příklad:
   ```bash
   python set_admin.py admin@example.com
   ```

4. Pro zobrazení všech uživatelů:
   ```bash
   python set_admin.py --list
   ```

### V Coolify (přes Docker exec):

1. V Coolify → tvoje aplikace → **Terminal** nebo **Exec**
2. Spusť:
   ```bash
   python set_admin.py <tvuj-email>
   ```

## Metoda 2: Přímý SQL dotaz

### Pro SQLite:

```sql
UPDATE users SET is_admin = 1 WHERE email = 'tvuj-email@example.com';
```

### Pro PostgreSQL:

```sql
UPDATE users SET is_admin = TRUE WHERE email = 'tvuj-email@example.com';
```

**Jak spustit SQL:**
- **SQLite**: `sqlite3 data/gym_turnstile.db` → pak SQL příkaz
- **PostgreSQL**: Připoj se k databázi přes psql nebo Coolify → PostgreSQL → Terminal

## Metoda 3: Přes API (pokud už máš admina)

Pokud už máš jednoho admina, můžeš vytvořit dalšího přes admin API endpoint (pokud existuje).

## Ověření

1. Přihlas se do aplikace s emailem, který jsi nastavil jako admin
2. Otevři `/admin` stránku
3. Měl bys mít přístup k admin dashboardu

## Troubleshooting

### "Uživatel nebyl nalezen"
- Zkontroluj, že se uživatel zaregistroval (má účet v databázi)
- Použij `python set_admin.py --list` pro zobrazení všech uživatelů

### "Permission denied" v Coolify
- Zkus použít SQL metodu místo Python skriptu
- Nebo zkontroluj, že máš přístup k databázi

### "DATABASE_URL není nastaven"
- Nastav environment variable `DATABASE_URL` před spuštěním skriptu
- Nebo použij SQL metodu

