## Gym Access QR System – plan.md

Progress: 🟩 100%

### Assumptions Made:
- **Token Usage**: One-time use tokens (valid for 24 hours OR until first use, whichever comes first)
- **Payment**: Mock payment API for MVP (easily switchable to real Stripe integration)
- **Token Cleanup**: Automatic invalidation on access check + optional background cleanup
- **Audit Logging**: Full logging of all access attempts (success/failure) in database

---

### Implementation Steps:

🟩 **Setup FastAPI app structure**
   - Create main FastAPI application
   - Setup project structure (app/, models/, routes/, etc.)
   - Configure CORS for frontend access
   - Add basic error handling

🟩 **Implement database models**
   - SQLite database with SQLAlchemy ORM
   - Models: User, Payment, AccessToken, AccessLog
   - Database initialization and migrations
   - Make it switchable to Postgres (via env vars)

🟩 **Implement payment endpoint**
   - `/create_payment` endpoint (mock payment processing)
   - Payment status tracking (pending, completed, failed)
   - Link payments to users

🟩 **Implement QR code generation**
   - `/generate_qr` endpoint (requires valid payment)
   - Generate unique token with 24h expiration
   - Use `python-qrcode` library
   - Return QR code as image or data URL

🟩 **Implement verification endpoint**
   - `/verify` endpoint for turnstile scanner
   - Check token validity (not expired, not used, payment valid)
   - Mark token as used after successful verification
   - Log all access attempts (success/failure)
   - Return `{"status": "allow"}` or `{"status": "deny"}` with reason

🟩 **Add token cleanup mechanism**
   - Automatic cleanup on access check
   - Optional background task for expired token cleanup
   - Database maintenance

🟩 **Create minimal frontend**
   - Simple HTML page to display QR code
   - Payment flow UI (mock)
   - Show payment status and QR code after payment

🟩 **Dockerize the application**
   - Create Dockerfile for FastAPI app
   - Create docker-compose.yml (FastAPI + SQLite/Postgres)
   - Add environment variable configuration
   - Setup volume mounts for database persistence

🟩 **Create documentation**
   - README.md with setup instructions
   - API endpoint documentation with curl examples
   - Expected request/response formats
   - Docker deployment instructions

🟩 **Testing and validation**
   - Test Docker build locally
   - Verify all endpoints work correctly
   - Test token expiration and one-time use
   - Verify access logging

---

### Technology Stack:
- **Backend**: FastAPI (Python)
- **Database**: SQLite (default, switchable to Postgres)
- **ORM**: SQLAlchemy
- **QR Code**: python-qrcode
- **Frontend**: Simple HTML/CSS/JS
- **Containerization**: Docker + Docker Compose

