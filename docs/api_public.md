# GymScanner API (Public Overview)

Základní rozhraní pro integraci s GymScanner backendem. Všechny URL jsou relativní k API doméně (např. `https://api.example.com`).

## Autorizace
- **JWT Bearer** (doporučené pro appky a admin UI): `Authorization: Bearer <token>` získaný z `POST /api/login`.
- **API klíč** (server-to-server): `X-API-KEY: <secret>`, spravuje se v admin sekci (`/api/admin/api-keys`). Tajný klíč se zobrazí pouze při vytvoření.
- Všechny požadavky posílejte přes HTTPS.

## Health & meta
- `GET /health` – základní healthcheck (DB + app).
- `GET /api/routes` – seznam registrovaných tras pro debugging.
- `GET /api/public-docs` – tento dokument (Markdown).

## Autentizace
### `POST /api/login`
```
Content-Type: application/x-www-form-urlencoded
username=<email>&password=<heslo>
```
Response: `{ access_token, token_type, user_id, user_name, is_admin, is_owner }`

### `POST /api/register`
```
{
  "email": "user@example.com",
  "name": "Test User",
  "password": "heslo123"
}
```

## Uživatelská data
### `GET /api/user/info` (JWT)
Vrátí info o účtu, počty kreditů, admin flag.

### `GET /api/my_qr` (JWT)
Vrátí osobní QR/PIN token + přehled membershipů/přítomnosti. Obsahuje blok `membership` s důvodem případného zamítnutí.

### `POST /api/regenerate_qr` (JWT)
Vygeneruje nový QR token (deaktivuje staré).

## Vstup / ověření
### `POST /api/verify` (vyžaduje `X-API-KEY`)
```
{
  "token": "<qr_or_pin>"
}
```
Response: `{ allowed, reason, credits_left, cooldown_seconds_left, membership {...} }`

### `POST /api/verify/entry` (vyžaduje `X-API-KEY`)
Ověří token/PIN, při úspěchu zapíše využití vstupu (daily limit / sessions) a označí uživatele jako „v gymu“.
```
{
  "token": "<qr_or_pin>"
}
```
Response: `{ allowed, reason, membership {...}, message }`

### `POST /api/verify/exit` (vyžaduje `X-API-KEY`)
Ověří token/PIN pro odchod a uzavře aktivní presence session (uživatel už není „v gymu“).
```
{
  "token": "<qr_or_pin>"
}
```
Response: `{ allowed, reason, membership {...}, message }`

## Membership & kredity
### `POST /api/buy_credits` (JWT)
Inicializuje nákup kreditů (Comgate).

### `GET /api/my_credits` (JWT)
Stav kreditů.

## Admin / backoffice (JWT nebo API klíč)
Používejte admin JWT, nebo API klíč v hlavičce `X-API-KEY`.

- `GET /api/admin/users` – poslední uživatelé.
- `GET /api/admin/users/search?q=…` – vyhledávání.
- `POST /api/admin/users/{id}/credits` – úprava kreditů.
- `GET /api/admin/users/{id}/memberships` – přehled membershipů uživatele.
- `POST /api/admin/membership-packages` – vytvoření balíčku.
- `GET /api/admin/tokens` + `/api/admin/tokens/{id}/activate|deactivate`.
- **API klíče**:
  - `GET /api/admin/api-keys` – seznam (bez secretů).
  - `POST /api/admin/api-keys` – vytvoření (`name`). Response obsahuje jednorázově `token`.
  - `POST /api/admin/api-keys/{id}/revoke` – deaktivace.
  - `DELETE /api/admin/api-keys/{id}` – trvalé smazání.

## Příklady (curl)
- Health: `curl https://api.example.com/health`
- Login: `curl -X POST https://api.example.com/api/login -d 'username=admin@admin.com&password=Admin123!'`
- Verify token: `curl -X POST https://api.example.com/api/verify -H 'Content-Type: application/json' -d '{"token":"<QR>"}'`
- List users (API key): `curl https://api.example.com/api/admin/users -H 'X-API-KEY: ak_...'`

## Chybové kódy (výběr)
- `401` – chybí/je neplatný JWT nebo API klíč.
- `403` – chybí admin oprávnění.
- `404` – entita nenalezena.
- `422` – nevalidní vstup.
