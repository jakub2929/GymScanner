# Oprava: Účty se mažou po redeploy

## Problém

Pokud používáš **SQLite** bez volume, databáze se ukládá do kontejneru. Při redeploy se vytvoří nový kontejner a databáze se ztratí.

## Řešení: Nastavit Volume v Coolify

### Krok 1: Přidej Volume v Coolify

1. V Coolify → tvoje aplikace → **Volumes** (nebo **Storage**)
2. Klikni na **"Add Volume"** nebo **"Add Storage"**
3. Nastav:
   - **Path**: `/app/data`
   - **Mount**: `gymturnstile-data` (nebo jakýkoliv název)
4. Ulož

### Krok 2: Ověř, že DATABASE_URL je správně nastaven

V Environment Variables zkontroluj:
```bash
DATABASE_URL=sqlite:///./data/gym_turnstile.db
```

**DŮLEŽITÉ:** Cesta musí být `/app/data/gym_turnstile.db` (relativní k `/app`), protože volume mountuje `/app/data`.

### Krok 3: Redeploy aplikace

Po přidání volume:
1. Restartuj nebo redeploy aplikaci
2. Databáze se nyní ukládá do volume, který přežije redeploy

## Alternativní řešení: PostgreSQL

Pokud můžeš vytvořit PostgreSQL databázi v Coolify, je to lepší řešení:

1. Vytvoř PostgreSQL databázi v Coolify
2. Získej connection string
3. Změň `DATABASE_URL` na PostgreSQL connection string
4. PostgreSQL databáze je automaticky persistentní

## Ověření

Po nastavení volume:

1. Vytvoř nový účet
2. Udělej redeploy
3. Účet by měl zůstat (databáze je v volume)

## Troubleshooting

### "Volume se nepřipojuje"
- Zkontroluj, že path je `/app/data` (ne `/data`)
- Zkontroluj, že aplikace má oprávnění k zápisu do volume

### "Databáze se stále maže"
- Zkontroluj logy aplikace - měla by se vytvářet v `/app/data/`
- Zkontroluj, že volume je skutečně připojený (v Coolify → Volumes)

### "Permission denied"
- Zkontroluj oprávnění volume v Coolify
- Možná potřebuješ nastavit správná oprávnění v Dockerfile

## Pro produkci: Použij PostgreSQL

SQLite s volume funguje, ale pro produkci je lepší PostgreSQL:
- ✅ Automaticky persistentní
- ✅ Lepší pro více uživatelů
- ✅ Lepší výkon
- ✅ Podpora pro více serverů

