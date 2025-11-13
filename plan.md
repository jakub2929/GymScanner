# Plán úpravy designu QR stránky + tlačítko "Stáhnout QR"

**Celkový progress:** 🟩 100% (3/3 hlavních úkolů dokončeno)

## Celkový popis

Úprava designu dashboard stránky (QR kód + kredity) - odstranění "AI gradient" stylu, zavedení Tailwind CSS, čistá barevná paleta vhodná pro GYM, odstranění emojis, přidání tlačítka pro stažení QR kódu.

**Důležité:** NESAHAT na backend logiku, databázi, business logiku. Pouze frontend design a QR download funkcionalita.

---

## Analýza současného stavu

### Stack:
- **Backend:** FastAPI (Python)
- **Frontend:** Vanilla HTML/CSS/JS (statické soubory)
- **QR stránka:** `static/dashboard.html`
- **QR implementace:** Backend generuje PNG jako base64 data URL, zobrazuje se jako `<img id="qrImage">`
- **Email API:** Neexistuje (jen TODO komentáře v kódu)

### Současný design:
- Animované gradienty (`linear-gradient(135deg, #0a0a0f 0%, #1a0a2e 25%...)`)
- Neon efekty a animace (`@keyframes gradientShift`, `@keyframes float`)
- Emojis v nadpisech (🏋️)
- Inline CSS v `<style>` tagu
- "AI gradient" styl s přehnanými efekty

### Soubory k úpravě:
- `static/dashboard.html` - hlavní QR stránka (design + download tlačítko)

---

## Úkoly

### 1. Tailwind CSS setup 🟩
- **Popis:** Přidat Tailwind CSS do projektu (přes CDN, protože je to vanilla HTML)
- **Soubor:** `static/dashboard.html`
- **Změny:**
  - Přidat Tailwind CDN link do `<head>` sekce
  - Přidat základní theme konfiguraci (volitelně přes CDN config)
  - Vytvořit čistou barevnou paletu vhodnou pro GYM (čitelné, jednoduché barvy)

### 2. Design refactor (Tailwind) 🟩
- **Popis:** Přepsat současný CSS na Tailwind utility classy, odstranit emojis, změnit barvy
- **Soubor:** `static/dashboard.html`
- **Změny:**
  - Odstranit všechny emojis z nadpisů/popisků (🏋️, 🔄, atd.)
  - Přepsat inline CSS na Tailwind utility classy
  - Odstranit animované gradienty a neon efekty
  - Vytvořit čistý, moderní design s:
    - Jednoduchým pozadím (světle šedé nebo bílé)
    - Čitelnou typografií
    - Čistými kartami a tlačítky
    - "Gym vibe" barvami (např. tmavě modrá, šedá, bílá - žádný neon)
  - Zachovat všechny funkce (QR zobrazení, kredity, regenerace QR)

### 3. QR download button 🟩
- **Popis:** Přidat tlačítko "Stáhnout QR" pro stažení QR kódu jako obrázek
- **Soubor:** `static/dashboard.html`
- **Změny:**
  - Přidat tlačítko vedle "Vygenerovat nový QR kód"
  - Implementovat funkci `downloadQR()` která:
    - Získá QR obrázek z `<img id="qrImage">` (data URL)
    - Převede data URL na blob nebo použije přímý download
    - Stáhne jako PNG soubor (např. `my-qr-code.png`)
  - Funkce musí fungovat na mobilu i desktopu
  - **Důležité:** NESAHAT na logiku generování QR (backend zůstává stejný)

### 4. Volitelné: Email QR button 🟥 (zrušeno - není potřeba)
- **Popis:** Přidat UI tlačítko "Poslat QR e-mailem" s TODO komentářem
- **Soubor:** `static/dashboard.html`
- **Změny:**
  - Přidat tlačítko "Poslat QR e-mailem" (volitelné, vedle download tlačítka)
  - Implementovat funkci `sendQRByEmail()` s TODO komentářem
  - Funkce zkontroluje, jestli existuje `/api/send_qr_email` endpoint
  - Pokud neexistuje, zobrazí TODO zprávu nebo připraví strukturu pro budoucí implementaci
  - **Důležité:** Email API endpoint neexistuje, takže jen připravit strukturu

---

## Technické detaily

### QR download implementace:
- QR je zobrazen jako `<img id="qrImage" src="data:image/png;base64,...">`
- Možnosti stažení:
  1. **Přímý download:** Vytvořit `<a>` element s `download` atributem a data URL jako `href`
  2. **Canvas approach:** Vykreslit obrázek na canvas a stáhnout jako blob
- **Doporučení:** Použít přímý download (jednodušší, funguje všude)

### Tailwind CDN:
```html
<script src="https://cdn.tailwindcss.com"></script>
```

### Barevná paleta (Gym vibe):
- **Primární:** Tmavě modrá (`#1e3a8a` / `blue-900`)
- **Sekundární:** Šedá (`#4b5563` / `gray-600`)
- **Pozadí:** Světle šedé/bílé (`#f9fafb` / `gray-50`)
- **Akcent:** Modrá (`#3b82f6` / `blue-500`)
- **Text:** Tmavě šedá (`#1f2937` / `gray-800`)

---

## Pořadí implementace

1. **Tailwind setup** (úkol 1) - přidat CDN, základní konfigurace
2. **Design refactor** (úkol 2) - přepsat CSS na Tailwind, odstranit emojis, změnit barvy
3. **QR download button** (úkol 3) - implementovat stažení QR kódu
4. **Email QR button** (úkol 4) - volitelně přidat UI + TODO komentář

---

## Testování

Po implementaci otestovat:
- ✅ QR kód se stále korektně zobrazuje
- ✅ Kredity se správně zobrazují
- ✅ Tlačítko "Vygenerovat nový QR kód" funguje
- ✅ Tlačítko "Stáhnout QR" stáhne obrázek
- ✅ Design je čistý, bez emojis, bez přehnaných gradientů
- ✅ Stránka je responzivní (mobil + desktop)
- ✅ Login/QR logika není rozbitá

---

**Poznámka:** Backend logika, databáze, business logika zůstávají beze změny. Upravujeme pouze frontend design a přidáváme download funkcionalitu.
