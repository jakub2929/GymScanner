# Local Login Accounts

These preset accounts exist in the local database for quick access during development/testing.  
Passwords are stored hashed in DB; rerun the provisioning script and restart the stack if you change them manually.

## Owner (platform branding)
- URL: `http://localhost:3000/owner/login`
- Email: `owner@admin.com`
- Password: `Owner123!`
- Permissions: Owner + Admin (access to owner branding + admin console)

## Admin
- URL: `http://localhost:3000/login` (same form as users; admin link also redirects here)
- Email: `admin@admin.com`
- Password: `Admin123!`
- Permissions: Admin dashboard

## User
- URL: `http://localhost:3000/login`
- Email: `test@test.com`
- Password: `User123!`
- Credits: 5

### Note
If the accounts disappear (e.g., after recreating the database), run:
```bash
docker compose -f docker-compose.local.yml exec web python scripts/ensure_accounts.py
```
or re-run the snippet in this repo’s history that re-seeds the accounts. Then restart the stack.

## Jak fungují QR / PINy a permanentky

- Každý uživatel má **jeden 6místný kód**, který se zobrazuje na dashboardu. Kód je použitý v QR i jako ručně zadávaný PIN na čtečce.
- Při koupi permanentky se nic na QR/PINu nemění – při skenování (nebo zadání PINu) se nejprve dohledá uživatel a následně se vyhodnotí jeho aktivní permanentky / osobní tréninky.
- Přes sekci „Balíčky“ si uživatel koupí novou permanentku, která se k účtu automaticky připojí a je okamžitě platná ve scanneru.
- PIN/QR lze kdykoliv regenerovat z dashboardu („Vygenerovat nový QR“); tím se deaktivují staré tokeny.
