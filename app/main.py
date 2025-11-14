from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import modules first (these should not fail)
from app.database import engine, Base, ensure_access_token_columns, ensure_user_password_column
from app.routes import payments, qr, verify, admin, auth, user_qr, credits

logger.info("Starting application initialization...")

app = FastAPI(
    title="Gym Turnstile QR System",
    description="QR code access system for gym turnstiles",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware to debug requests
@app.middleware("http")
async def log_requests(request, call_next):
    # Log request details - using print to ensure it shows up
    auth_header = request.headers.get("Authorization", "None")
    print(f"[MIDDLEWARE] Request: {request.method} {request.url.path}")
    print(f"[MIDDLEWARE] Authorization header: {auth_header[:80] if auth_header != 'None' else 'None'}")
    print(f"[MIDDLEWARE] All headers: {dict(request.headers)}")
    
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
        ensure_last_scan_at_column()
        ensure_payment_comgate_columns()
        logger.info("Database migrations completed")
        
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

@app.get("/")
async def read_root():
    """Return API status and point to the new Next.js frontend."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return {
        "message": "Gym Turnstile API running",
        "frontend": frontend_url,
        "docs": "/docs",
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
