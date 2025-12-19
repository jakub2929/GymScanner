# Cal.com (self‑hosted) – local notes

## Admin account (local test)
- URL: http://localhost:3200
- Username (path slug): `admin`
- Full name: `admin`
- Email: `admin@example.com`
- Password: `Adminadmin1234!`

These credentials are for local testing only. Change them before exposing the service publicly.

## Services / ports
- Web UI: http://localhost:3200
- Postgres: internal (`calcom-postgres`), password `calcompass`
- Redis: internal (`calcom-redis`)

## Webhook integration with GymScanner backend
- Backend webhook endpoint: `POST /api/integrations/calcom/webhook` (local: `http://localhost:8000/api/integrations/calcom/webhook`).
- Configure in admin UI (our app) under **Admin → Integrace → Cal.com**:
  - Set a strong `Secret` (32+ chars) and zapnout integraci.
  - Copy `Webhook URL` into Cal.com → Settings → Developer → Webhooks.
  - Select event triggers you need (minimálně Booking Created/Rescheduled/Cancelled).
  - Cal.com sends HMAC SHA256 signature; we verify against the stored secret.
- Events are logged to `calcom_webhook_events` (last events visible v admin UI).

## Webhooks (OSS)
Self‑hosted Cal.com supports outgoing webhooks for booking lifecycle events. In Settings → Developer → Webhooks you can register a URL and choose events such as:
- `booking.created`
- `booking.rescheduled`
- `booking.cancelled`
- `booking.requested` / `booking.rejected` (if request/approval flows are enabled)
- `booking.reminder.*` (reminder/workflow triggers)

Payloads include booking metadata (time, attendees, event type), host/user info and the webhook signature header for verification.

## API (OSS)
- **REST**: Admin/API keys (per team) can call endpoints for bookings, availability, event types, teams, users. Typical base URL: `http://localhost:3200/api`. Auth via `Authorization: Bearer <api-key>`.
- **GraphQL**: `/api/graphql` exposes similar resources (event types, bookings, availability).
- **ICS/Cal feeds**: public subscription links per event type.
- **Scheduling links**: `/{username}/{eventSlug}` for booking pages.

Notes:
- UNKEY rate limit and VAPID web‑push keys are optional; missing keys only disable those features.
- Replace dummy secrets in `calcom/.env.calcom` (`NEXTAUTH_SECRET`, `CALENDSO_ENCRYPTION_KEY`, `JWT_SECRET`) before production and configure SMTP/OAuth if needed.
