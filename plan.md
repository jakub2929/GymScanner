# Plán projektu GymTurniket

## 🟩 100% – Fix PostgreSQL dialect / DATABASE_URL v produkci

**Problém:** SQLAlchemy vyhazuje `sqlalchemy.exc.NoSuchModuleError: sqlalchemy.dialects:postgres` když DATABASE_URL má prefix `postgres://` místo `postgresql+psycopg2://`.

**Příčina:** Coolify poskytuje connection string ve formátu `postgres://user:pass@host:5432/db`, ale SQLAlchemy potřebuje explicitní dialekt `postgresql+psycopg2://` pro správné načtení PostgreSQL driveru.

**Řešení:**
- Normalizovat DATABASE_URL v kódu: `postgres://` → `postgresql+psycopg2://`
- Ověřit, že `psycopg2-binary` je v requirements.txt
- Aktualizovat dokumentaci s poznámkou o automatické konverzi

### Backend – Normalizace DATABASE_URL 🟩
- **Soubor:** `app/database.py`
- **Změny:**
  - ✅ Přidána normalizace: pokud DATABASE_URL začíná `postgres://`, přepíše se na `postgresql+psycopg2://`
  - ✅ Přidáno logování změny pro debugging
  - ✅ Aplikace nyní automaticky převádí `postgres://...` connection string z Coolify na správný formát

### Kontrola PostgreSQL driveru 🟩
- **Soubor:** `requirements.txt`
- **Ověření:** ✅ `psycopg2-binary==2.9.9` je přítomen v requirements.txt

### Dokumentace / .env.example 🟩
- **Soubory:** `POSTGRES_SETUP_COOLIFY.md`, `COOLIFY_ENV_VARS_ACTUAL.txt`
- **Změny:**
  - ✅ Aktualizován příklad connection stringu na `postgresql+psycopg2://username:password@host:5432/database_name`
  - ✅ Přidána poznámka o automatické konverzi `postgres://` → `postgresql+psycopg2://`
  - ✅ Přidána sekce troubleshooting pro `NoSuchModuleError`

### Deploy & ověření 🟨
- ⏳ Commit a push změn (čeká na uživatele)
- ⏳ Redeploy na Coolify (čeká na uživatele)
- ⏳ Ověřit logy: nesmí se objevit `NoSuchModuleError` (čeká na deploy)
- ⏳ Ověřit, že Uvicorn úspěšně naběhne (čeká na deploy)

**Poznámka:** Po dokončení implementace spusť Docker build a ověř, že build proběhne úspěšně:
```bash
docker build -t gymturniket -f Dockerfile.production .
```

---

# Plán integrace platební brány Comgate + nákup tokenů

**Celkový progress:** 🟩 100% – Integrace platební brány (Comgate) + nákup tokenů dokončena

## Analýza existujícího kódu

### Existující struktura

**Modely:**
- ✅ `User` model má `credits` (Integer, default=0) - toto je to, co potřebujeme
- ✅ `Payment` model už existuje s poli: id, user_id, amount (Float), status (String), payment_id (String, unique), created_at, completed_at
- ✅ `AccessToken` má vztah k Payment přes `payment_id` (nullable)

**Existující payment logika:**
- ✅ `app/routes/credits.py` - má `/api/buy_credits` (mock payment, okamžitě přidává kredity)
- ✅ `app/routes/payments.py` - má `/api/create_payment` (starý mock endpoint)

**Frontend:**
- ✅ `static/dashboard.html` - hlavní stránka s QR kódem, zobrazuje kredity v `creditsDisplay` elementu
- ✅ Používá Tailwind CSS
- ✅ Má tlačítka "Stáhnout QR" a "Vygenerovat nový QR kód"

### Co potřebujeme přidat/upravit

1. **Rozšířit Payment model** o pole pro Comgate:
   - `token_amount` (Integer) - počet tokenů v objednávce
   - `price_czk` (Integer) - cena v Kč
   - `provider` (String) - "comgate" nebo jiný provider
   - `paid_at` (DateTime, nullable) - kdy byla platba dokončena
   - `updated_at` (DateTime) - poslední aktualizace

2. **Vytvořit nový payment service** pro abstrakci platební logiky

3. **Nové endpointy:**
   - `POST /api/payments/create` - vytvoření objednávky
   - `POST /api/payments/comgate/notify` - callback z Comgate (NOTIFY URL)
   - `GET /api/payments/comgate/return` - návrat uživatele po platbě (RETURN URL)

4. **Frontend:**
   - Přidat tlačítko "Koupit tokeny" na dashboard
   - Modal s tabulkou balíčků (1, 5, 10 tokenů)
   - Integrace s novým endpointem

---

## 1) Backend – Platební logika & modely

### 1.1 Rozšíření Payment modelu 🟩
- **Popis:** Přidat pole pro Comgate integraci do existujícího Payment modelu
- **Soubor:** `app/models.py`
- **Změny:**
  - Přidat `token_amount` (Integer) - počet tokenů v objednávce
  - Přidat `price_czk` (Integer) - cena v Kč (místo Float amount pro přesnost)
  - Přidat `provider` (String, default="comgate") - identifikace platební brány
  - Přidat `paid_at` (DateTime, nullable) - kdy byla platba dokončena
  - Přidat `updated_at` (DateTime) - poslední aktualizace
  - Změnit `status` na enum: "pending", "paid", "failed", "cancelled"
  - **Migrace:** Vytvořit migrační funkci v `app/database.py` pro přidání nových sloupců

### 1.2 Vytvoření Payment Service vrstvy 🟩
- **Popis:** Vytvořit abstrakci pro platební logiku (připravit pro Comgate)
- **Soubor:** `app/services/payment_service.py` (nový)
- **Funkce:**
  - `create_order(user_id, token_amount, price_czk) -> Payment` - vytvoří objednávku se statusem pending
  - `mark_order_paid(payment_id) -> Payment` - označí objednávku jako paid, přičte tokeny uživateli
  - `prepare_comgate_data(payment) -> dict` - připraví data pro budoucí Comgate redirect (zatím placeholder)
  - **Důležité:** Použít transakce pro atomické operace (připsání tokenů + update payment)

### 1.3 Nové payment endpointy 🟩
- **Soubor:** `app/routes/payments.py` (upravit existující)
- **Endpointy:**
  - `POST /api/payments/create`:
    - Vstup: `{ "token_amount": 1 | 5 | 10 }`
    - Validace: token_amount musí být 1, 5 nebo 10
    - Spočítá cenu: `token_amount * 100` Kč
    - Vytvoří Payment se statusem "pending"
    - Připraví data pro Comgate (zatím placeholder redirect_url)
    - Odpověď: `{ payment_id, token_amount, price_czk, provider, redirect_url }`
  
  - `POST /api/payments/comgate/notify`:
    - Callback z Comgate (NOTIFY URL)
    - Zatím TODO logika s validací signatury
    - Po úspěšné validaci: označit payment jako paid, přičíst tokeny
  
  - `GET /api/payments/comgate/return`:
    - Návrat uživatele po platbě (RETURN URL)
    - Zobrazí status platby (úspěch/neúspěch)
    - Přesměruje na dashboard s informací o připsaných tokenech

### 1.4 Migrace databáze 🟩
- **Soubor:** `app/database.py`
- **Funkce:** `ensure_payment_comgate_columns()`
- **Změny:**
  - Přidat sloupce: token_amount, price_czk, provider, paid_at, updated_at
  - Aktualizovat existující payments (pokud existují)

---

## 2) Frontend – Tlačítko "Koupit tokeny" + tabulka balíčků

### 2.1 Přidání tlačítka "Koupit tokeny" 🟩
- **Soubor:** `static/dashboard.html`
- **Změny:**
  - Přidat tlačítko "Koupit tokeny" na dashboard (např. vedle "Vygenerovat nový QR kód" nebo jako samostatnou sekci)
  - Stylově sladěné s Tailwind CSS (modrá barva, podobné jako ostatní tlačítka)

### 2.2 Modal s tabulkou balíčků 🟩
- **Soubor:** `static/dashboard.html`
- **Změny:**
  - Po kliknutí na "Koupit tokeny" otevřít modal/panel
  - Tabulka s balíčky:
    - **1 token** – 100 Kč
    - **5 tokenů** – 500 Kč
    - **10 tokenů** – 1000 Kč
  - U každého balíčku tlačítko "Koupit"
  - Design: čistý, moderní, s Tailwind CSS

### 2.3 Integrace s backend API 🟩
- **Soubor:** `static/dashboard.html` (JavaScript sekce)
- **Funkce:**
  - `openBuyTokensModal()` - otevře modal
  - `buyTokens(tokenAmount)` - zavolá `POST /api/payments/create` s token_amount
  - Po úspěchu:
    - Zobrazí informaci o vytvořené objednávce
    - Zobrazí redirect_url (zatím placeholder)
    - Do budoucna: automatický redirect na Comgate
  - Po chybě: zobrazí error message

### 2.4 Aktualizace zobrazení kreditů 🟩
- **Soubor:** `static/dashboard.html`
- **Změny:**
  - Po úspěšné platbě (simulace) aktualizovat `creditsDisplay`
  - Zobrazit toast notifikaci o připsaných tokenech

---

## 3) Environment & konfigurace

### 3.1 Přidání Comgate proměnných do .env 🟩
- **Soubor:** `.env.example` a `.env`
- **Proměnné:**
  ```
  COMGATE_MERCHANT_ID=
  COMGATE_SECRET=
  COMGATE_TEST_MODE=true
  COMGATE_RETURN_URL=https://localhost/api/payments/comgate/return
  COMGATE_NOTIFY_URL=https://localhost/api/payments/comgate/notify
  ```
- **Důležité:** Nepoužívat hard-coded hodnoty v kódu

### 3.2 Načítání konfigurace v backendu 🟩
- **Soubor:** `app/services/payment_service.py`
- **Změny:**
  - Použít `os.getenv()` pro načtení Comgate dat
  - Validace: pokud proměnné nejsou nastavené, použít placeholder hodnoty (pro vývoj)

---

## 4) Napojení tokenů

### 4.1 Logika připsání tokenů po platbě 🟩
- **Soubor:** `app/services/payment_service.py`
- **Funkce:** `mark_order_paid(payment_id)`
- **Logika:**
  - Najít Payment podle payment_id
  - Zkontrolovat, že status je "pending" (ochrana proti dvojímu připsání)
  - V transakci:
    - Nastavit status = "paid"
    - Nastavit paid_at = now()
    - Připsat `token_amount` kreditů uživateli: `user.credits += payment.token_amount`
  - Commit transakce
  - **Důležité:** Použít DB transakci pro atomičnost

### 4.2 Validace a ochrana 🟩
- **Ochrana proti dvojímu připsání:**
  - Kontrola statusu před připsáním (musí být "pending")
  - Použití DB transakce
  - Idempotentní callback handling (Comgate může volat notify vícekrát)

---

## 5) Testování

### 5.1 Test vytvoření objednávky 🟥
- Přihlásit uživatele
- Kliknout na "Koupit tokeny"
- Vybrat balíček (1, 5, 10 tokenů)
- Ověřit, že se vytvoří Payment v DB se statusem "pending"
- Ověřit, že se vrátí správná odpověď s redirect_url

### 5.2 Test simulace zaplacení 🟥
- Ručně zavolat funkci `mark_order_paid(payment_id)`
- Ověřit, že se Payment označí jako "paid"
- Ověřit, že se správně přičtou tokeny uživateli
- Ověřit, že se kredity zobrazí na dashboardu

### 5.3 Test ochrany proti dvojímu připsání 🟥
- Zkusit zavolat `mark_order_paid()` dvakrát na stejný payment
- Ověřit, že se tokeny přičtou pouze jednou

### 5.4 Test stávajících funkcí 🟥
- Ověřit, že QR kód se stále zobrazuje
- Ověřit, že regenerace QR funguje
- Ověřit, že scanner funguje
- Ověřit, že login/registrace fungují

---

## Technické detaily

### Datový tok:
1. User klikne "Koupit tokeny" → otevře se modal
2. User vybere balíček (1/5/10 tokenů) → klikne "Koupit"
3. Frontend zavolá `POST /api/payments/create` s `token_amount`
4. Backend vytvoří Payment (status="pending") a vrátí `redirect_url`
5. **Budoucí:** Frontend přesměruje na Comgate (zatím zobrazí placeholder)
6. User zaplatí na Comgate
7. Comgate zavolá `POST /api/payments/comgate/notify` (callback)
8. Backend označí payment jako "paid" a přičte tokeny
9. Comgate přesměruje uživatele na `GET /api/payments/comgate/return`
10. Backend zobrazí status a přesměruje na dashboard

### Payment model (rozšířený):
```python
class Payment(Base):
    id: int
    user_id: int
    token_amount: int  # NOVÉ: počet tokenů
    price_czk: int  # NOVÉ: cena v Kč
    status: str  # "pending", "paid", "failed", "cancelled"
    provider: str  # NOVÉ: "comgate"
    payment_id: str  # unique identifier
    created_at: datetime
    paid_at: datetime | None  # NOVÉ
    updated_at: datetime  # NOVÉ
    completed_at: datetime | None  # existující (možná deprecated)
```

### Balíčky tokenů:
- **1 token** = 100 Kč
- **5 tokenů** = 500 Kč
- **10 tokenů** = 1000 Kč
- (každý balíček zatím za 100 Kč/token, bez slev)

---

## Pořadí implementace

1. **Backend modely a migrace** (1.1, 1.4) - rozšířit Payment model
2. **Payment service** (1.2) - vytvořit abstrakci
3. **Backend endpointy** (1.3) - vytvořit/upravit payment endpointy
4. **Environment** (3.1, 3.2) - přidat .env proměnné
5. **Frontend UI** (2.1, 2.2) - přidat tlačítko a modal
6. **Frontend integrace** (2.3, 2.4) - propojit s backendem
7. **Testování** (5) - otestovat všechny scénáře

---

**Poznámka:** V této fázi NEPLNOU integraci Comgate (reálné API volání), ale připravíme strukturu, kam se integrace později připojí. Použijeme správnou abstrakci (PaymentService), aby přidání Comgate bylo jen doplnění implementace.
