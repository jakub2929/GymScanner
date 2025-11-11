# Gym Turnstile QR System

A production-ready system that allows gym members to enter through a turnstile using a QR code generated after a valid payment.

## ⚠️ Důležité: Požadavek HTTPS

**Tento systém VYŽADUJE HTTPS pro správné fungování.** Aplikace běží na portu 443 s SSL certifikáty. Bez HTTPS nebudou některé funkce (např. přístup ke kameře pro skenování QR kódů) fungovat správně.

- Aplikace běží na portu **443** (HTTPS)
- SSL certifikáty musí být umístěny v adresáři `ssl/`
- Pro vývoj lze použít self-signed certifikáty (viz sekce níže)
- V produkci použijte certifikáty od důvěryhodné CA (Let's Encrypt, atd.)

## Features

- **Payment Processing**: Mock payment API (easily switchable to real payment providers)
- **QR Code Generation**: Unique QR codes valid for 24 hours or until first use (one-time use)
- **Turnstile Verification**: `/verify` endpoint for physical scanners
- **Audit Logging**: Complete logging of all access attempts
- **Dockerized**: Easy deployment on VPS or Coolify

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite (default, switchable to Postgres)
- **ORM**: SQLAlchemy
- **QR Code**: python-qrcode
- **Frontend**: Simple HTML/CSS/JS
- **Containerization**: Docker + Docker Compose

## Quick Start

### 1. Generování SSL Certifikátů (Nutné)

Nejprve je nutné vygenerovat SSL certifikáty. Pro vývoj můžete použít self-signed certifikáty:

```bash
# Vytvořte adresář pro SSL certifikáty (pokud neexistuje)
mkdir -p ssl

# Spusťte skript pro generování self-signed certifikátů
bash generate_cert.sh

# Nebo vygenerujte ručně (upravte IP adresu podle vašeho prostředí):
openssl req -x509 -newkey rsa:4096 -nodes \
    -out ssl/cert.pem \
    -keyout ssl/key.pem \
    -days 365 \
    -subj "/C=CZ/ST=State/L=City/O=GymTurniket/CN=localhost" \
    -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"
```

**Poznámka:** Pro produkci použijte certifikáty od důvěryhodné CA (např. Let's Encrypt).

### 2. Spuštění aplikace

#### Using Docker Compose (Doporučeno)

```bash
# Zastavit běžící kontejnery (pokud existují)
docker-compose down

# Sestavit a spustit aplikaci
docker-compose build
docker-compose up -d

# Zobrazit logy
docker-compose logs -f

# Zastavit aplikaci
docker-compose down
```

Aplikace bude dostupná na `https://localhost:443`

**Poznámka:** Prohlížeč může zobrazit varování o self-signed certifikátu. V produkci použijte certifikáty od důvěryhodné CA.

#### Manual Setup (Vývoj)

```bash
# Instalace závislostí
pip install -r requirements.txt

# Spuštění aplikace s SSL
uvicorn app.main:app --reload --host 0.0.0.0 --port 443 \
    --ssl-keyfile ssl/key.pem --ssl-certfile ssl/cert.pem
```

## API Endpoints

### 1. Create Payment

Create a mock payment (in production, integrate with Stripe/PayPal/etc.)

```bash
curl -k -X POST "https://localhost:443/api/create_payment" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "John Doe",
    "amount": 25.00
  }'
```

**Poznámka:** Parametr `-k` v curl ignoruje chyby s self-signed certifikáty. V produkci s platným certifikátem tento parametr není nutný.

**Response:**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "user_id": 1,
  "amount": 25.0
}
```

### 2. Generate QR Code

Generate a QR code token for gym access (requires valid completed payment)

```bash
curl -k -X POST "https://localhost:443/api/generate_qr" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Response:**
```json
{
  "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "qr_code_url": "data:image/png;base64,iVBORw0KGgoAAAANS...",
  "expires_at": "2024-01-02T12:00:00"
}
```

### 3. Verify Token (Turnstile Scanner)

Verify a QR code token for turnstile access

```bash
curl -k -X POST "https://localhost:443/api/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

**Success Response:**
```json
{
  "status": "allow",
  "reason": "Access granted"
}
```

**Failure Response:**
```json
{
  "status": "deny",
  "reason": "Token not found"
}
```

Possible deny reasons:
- `"Token not found"`
- `"Token expired"`
- `"Token already used"`
- `"Payment not valid"`

### 4. Get Payment Status

```bash
curl -k "https://localhost:443/api/payment/550e8400-e29b-41d4-a716-446655440000"
```

### 5. Get Access Logs (Admin/Debugging)

```bash
curl -k "https://localhost:443/api/access_logs?limit=100"
```

### 6. Health Check

```bash
curl -k "https://localhost:443/health"
```

## Frontend

Webové rozhraní je dostupné na `https://localhost:443` a umožňuje uživatelům:
1. Zadání platebních údajů
2. Zpracování mock platby
3. Generování a zobrazení QR kódu

### Admin Dashboard

- Admin dashboard dostupný na `https://localhost:443/admin`
- Umožňuje zobrazit všechny vydané tokeny (jméno, email, platnost, počet skenů)
- Podporuje deaktivaci/aktivaci tokenu jedním klikem
- Součástí je náhled QR kódu a filtrování podle stavu

### Scanner Page

- Stránka pro skenování QR kódů dostupná na `https://localhost:443/scanner`
- Používá kameru pro skenování QR kódů
- **Vyžaduje HTTPS** pro přístup ke kameře (bezpečnostní požadavek prohlížeče)

## Database Schema

### Users
- `id`: Primary key
- `email`: Unique email address
- `name`: User's full name
- `created_at`: Timestamp

### Payments
- `id`: Primary key
- `user_id`: Foreign key to users
- `amount`: Payment amount
- `status`: Payment status (pending, completed, failed)
- `payment_id`: Unique payment identifier (UUID)
- `created_at`: Timestamp
- `completed_at`: Completion timestamp

### Access Tokens
- `id`: Primary key
- `token`: Unique token string (UUID)
- `user_id`: Foreign key to users
- `payment_id`: Foreign key to payments
- `is_used`: Boolean flag (one-time use)
- `expires_at`: Expiration timestamp (24 hours from creation)
- `created_at`: Creation timestamp
- `used_at`: Usage timestamp

### Access Logs
- `id`: Primary key
- `token_id`: Foreign key to access_tokens (nullable)
- `token_string`: Token string (for audit even if token deleted)
- `status`: "allow" or "deny"
- `reason`: Reason for allow/deny
- `ip_address`: Client IP address
- `user_agent`: Client user agent
- `created_at`: Timestamp

## Token Security

- Tokens are **one-time use** - once verified, they cannot be reused
- Tokens expire after **24 hours** from generation
- Tokens are linked to completed payments
- All access attempts are logged for audit purposes

## Using Postgres Instead of SQLite

1. Uncomment the Postgres service in `docker-compose.yml`
2. Update the `DATABASE_URL` environment variable
3. Rebuild and restart:

```bash
docker-compose down
docker-compose up -d --build
```

## Production Deployment

### ⚠️ Důležité: HTTPS je povinné

**Aplikace VYŽADUJE HTTPS pro produkční nasazení.** Bez HTTPS nebudou fungovat kritické funkce:
- Přístup ke kameře pro skenování QR kódů (bezpečnostní požadavek prohlížeče)
- Některé API funkce mohou být omezeny

### SSL Certifikáty pro produkci

Pro produkci použijte certifikáty od důvěryhodné CA:

1. **Let's Encrypt (doporučeno):**
   ```bash
   # Instalace certbot
   sudo apt-get update
   sudo apt-get install certbot
   
   # Získání certifikátu
   sudo certbot certonly --standalone -d yourdomain.com
   
   # Zkopírujte certifikáty do adresáře ssl/
   sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
   sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
   sudo chown $USER:$USER ssl/*.pem
   ```

2. **Automatické obnovení certifikátů:**
   Nastavte cron job pro automatické obnovení certifikátů Let's Encrypt (platné 90 dní).

### Environment Variables

- `DATABASE_URL`: Database connection string (default: SQLite)

### Security Considerations

1. **HTTPS**: **POVINNÉ** - aplikace nefunguje správně bez HTTPS
2. **SSL Certifikáty**: Použijte certifikáty od důvěryhodné CA (Let's Encrypt, atd.)
3. **CORS**: Update CORS settings in `app/main.py` to restrict origins
4. **Rate Limiting**: Consider adding rate limiting to prevent abuse
5. **Authentication**: Add authentication for admin endpoints
6. **Payment Integration**: Replace mock payment with real payment provider (Stripe, PayPal, etc.)

### Coolify Deployment

1. Connect your repository to Coolify
2. Set build command: `docker build -t gym-turnstile .`
3. Set start command: `docker-compose up -d`
4. Configure environment variables
5. **Nastavte SSL certifikáty** - použijte Let's Encrypt přímo v Coolify nebo nahrajte vlastní certifikáty
6. Ujistěte se, že aplikace běží na portu 443 s HTTPS
7. Deploy!

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Vygenerujte SSL certifikáty (viz Quick Start)
bash generate_cert.sh

# Run with auto-reload and SSL
uvicorn app.main:app --reload --host 0.0.0.0 --port 443 \
    --ssl-keyfile ssl/key.pem --ssl-certfile ssl/cert.pem

# Run tests (if you add them)
pytest
```

**Poznámka:** I pro vývoj je HTTPS nutné kvůli přístupu ke kameře pro skenování QR kódů.

## Troubleshooting

### Problémy s HTTPS

#### 1. Aplikace se nespustí - chyba s SSL certifikáty
**Problém:** `FileNotFoundError` nebo podobná chyba při startu aplikace.

**Řešení:**
- Zkontrolujte, že adresář `ssl/` existuje a obsahuje soubory `cert.pem` a `key.pem`
- Vygenerujte certifikáty pomocí `bash generate_cert.sh`
- Ověřte oprávnění k souborům: `chmod 600 ssl/*.pem`

#### 2. Prohlížeč zobrazuje varování o nebezpečném spojení
**Problém:** Prohlížeč varuje před self-signed certifikátem.

**Řešení:**
- Pro vývoj je to normální - klikněte na "Pokračovat" nebo "Advanced" → "Proceed to localhost"
- Pro produkci použijte certifikáty od důvěryhodné CA (Let's Encrypt)

#### 3. Kamera nefunguje na stránce scanner
**Problém:** Prohlížeč neposkytuje přístup ke kameře.

**Řešení:**
- **Ujistěte se, že používáte HTTPS** - kamera funguje pouze přes HTTPS
- Zkontrolujte oprávnění prohlížeče pro přístup ke kameře
- Zkuste použít jiný prohlížeč (Chrome, Firefox, Safari)

#### 4. Port 443 je již používán
**Problém:** `Address already in use` při startu aplikace.

**Řešení:**
```bash
# Zjistěte, který proces používá port 443
sudo lsof -i :443

# Nebo použijte netstat
sudo netstat -tulpn | grep :443

# Zastavte proces nebo změňte port v docker-compose.yml a Dockerfile
```

#### 5. Docker container se nespustí kvůli SSL
**Problém:** Container se nespustí nebo okamžitě spadne.

**Řešení:**
- Ověřte, že volume `./ssl:/app/ssl` je správně namountován v `docker-compose.yml`
- Zkontrolujte logy: `docker-compose logs web`
- Ujistěte se, že certifikáty existují před spuštěním: `ls -la ssl/`

### Další problémy

#### Databáze se nevytváří
- Zkontrolujte, že adresář `data/` existuje a má správná oprávnění
- Ověřte, že volume `./data:/app/data` je správně namountován

#### API endpointy nefungují
- Ověřte, že používáte `https://` místo `http://`
- Zkontrolujte, že port je 443, ne 8000
- Pro self-signed certifikáty použijte `curl -k` nebo přidejte certifikát do důvěryhodných

## License

MIT

