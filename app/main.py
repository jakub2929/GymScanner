from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import modules first (these should not fail)
from app.database import (
    engine,
    Base,
    ensure_access_token_columns,
    ensure_user_password_column,
    ensure_access_log_columns,
    ensure_access_log_extended_columns,
    ensure_access_log_presence_session_column,
    ensure_user_presence_columns,
    ensure_membership_columns,
    ensure_user_profile_columns,
)
from app.routes import payments, qr, verify, admin, auth, user_qr, credits, branding, owner, calcom
from app.database import ensure_user_owner_column, ensure_calcom_columns, ensure_branding_feature_columns
from app.services.owner import ensure_owner_account, ensure_branding_defaults
from app.services.membership import ensure_default_membership_packages

logger.info("Starting application initialization...")

app = FastAPI(
    title="Gym Turnstile QR System",
    description="QR code access system for gym turnstiles",
    version="1.0.0"
)

# Resolve allowed CORS origins from environment (comma/space separated)
def _parse_cors_origins(raw_value: str | None) -> list[str]:
    if not raw_value:
        return ["*"]
    origins = [origin.strip() for origin in raw_value.replace(" ", "").split(",") if origin.strip()]
    return origins or ["*"]

allowed_cors_origins = _parse_cors_origins(os.getenv("CORS_ORIGINS"))
allow_credentials = "*" not in allowed_cors_origins
logger.info(f"Configuring CORS for origins: {allowed_cors_origins}")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware to debug requests
@app.middleware("http")
async def log_requests(request, call_next):
    def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
        redacted = {}
        for key, value in headers.items():
            if key.lower() in {"authorization", "x-api-key"}:
                redacted[key] = "[redacted]"
            else:
                redacted[key] = value
        return redacted

    print(f"[MIDDLEWARE] Request: {request.method} {request.url.path}")
    print(f"[MIDDLEWARE] Headers: {_sanitize_headers(dict(request.headers))}")

    response = await call_next(request)
    print(f"[MIDDLEWARE] Response status: {response.status_code}")
    return response

# Initialize database on startup (not during import)
@app.on_event("startup")
async def initialize_database():
    """Initialize database tables - called on application startup"""
    try:
        # Test database connection first
        logger.info("Testing database connection...")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        
        # Create database tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Run migrations
        ensure_access_token_columns()
        ensure_user_password_column()
        from app.database import ensure_user_credits_column, ensure_access_token_nullable_columns, ensure_user_admin_column, ensure_last_scan_at_column, ensure_payment_comgate_columns
        ensure_user_credits_column()
        ensure_access_token_nullable_columns()
        ensure_user_admin_column()
        ensure_user_owner_column()
        ensure_last_scan_at_column()
        ensure_payment_comgate_columns()
        ensure_access_log_extended_columns()
        ensure_access_log_presence_session_column()
        ensure_user_presence_columns()
        ensure_access_log_columns()
        ensure_membership_columns()
        ensure_user_profile_columns()
        ensure_calcom_columns()
        ensure_branding_feature_columns()
        logger.info("Database migrations completed")
        ensure_owner_account()
        ensure_branding_defaults()
        ensure_default_membership_packages()
        
    except Exception as db_error:
        logger.error(f"Database initialization failed: {db_error}")
        logger.warning("=" * 60)
        logger.warning("DATABASE CONNECTION FAILED - Application will continue")
        logger.warning("=" * 60)
        logger.warning("Possible solutions:")
        logger.warning("1. Zkontroluj PostgreSQL připojení (docker compose logs postgres)")
        logger.warning("2. Ověř, že DATABASE_URL míří na správného hostitele/uživatele/DB")
        logger.warning("3. Ujisti se, že PostgreSQL kontejner běží a je ve stejné síti jako aplikace")
        logger.warning("4. Pro lokální běh použij `docker compose -f docker-compose.local.yml up -d postgres`")
        logger.warning("=" * 60)
        # Don't raise - let app start (but DB operations will fail)

# Include routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(user_qr.router, prefix="/api", tags=["user_qr"])
app.include_router(credits.router, prefix="/api", tags=["credits"])
app.include_router(payments.router, prefix="/api", tags=["payments"])
app.include_router(qr.router, prefix="/api", tags=["qr"])
app.include_router(verify.router, prefix="/api", tags=["verify"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(owner.router, prefix="/api", tags=["owner"])
app.include_router(branding.router, prefix="/api", tags=["branding"])
app.include_router(calcom.router, prefix="/api", tags=["calcom"])

static_dir = Path(os.getenv("STATIC_DIR", "static"))
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "branding").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_root():
    """
    Provide a simple status payload with pointers to docs/health.
    (Avoid redirecting to the frontend domain so API root stays debuggable.)
    """
    frontend_url = os.getenv("FRONTEND_URL")
    return {
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "api_prefix": "/api",
        "frontend": frontend_url or None,
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Try to connect to database
        from app.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "app": "running"
    }

@app.get("/api/routes")
async def list_routes():
    """List all available API routes for debugging"""
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            for method in route.methods:
                if method != "HEAD":  # Skip HEAD method
                    routes.append({
                        "method": method,
                        "path": route.path,
                        "name": getattr(route, "name", "unknown")
                    })
    return {
        "routes": sorted(routes, key=lambda x: (x["path"], x["method"])),
        "api_prefix": "/api",
        "total": len(routes)
    }

@app.get("/api/public-docs")
async def public_docs():
    """Serve public API documentation (Markdown)."""
    docs_path = Path(__file__).resolve().parent.parent / "docs" / "api_public.md"
    if not docs_path.exists():
        return {"detail": "api_public.md not found"}
    content = docs_path.read_text(encoding="utf-8")
    return Response(content=content, media_type="text/markdown")
