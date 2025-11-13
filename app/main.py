from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
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
from app.database import engine, Base, ensure_access_token_columns, ensure_user_password_column
from app.routes import payments, qr, verify, admin, auth, user_qr, credits

logger.info("Starting application initialization...")

# Ensure data directory exists for SQLite
data_dir = Path(__file__).parent.parent / "data"
if not data_dir.exists():
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created data directory: {data_dir}")

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
        logger.error("Application will start, but database operations will fail.")
        logger.error("Please check:")
        logger.error("1. DATABASE_URL is correct")
        logger.error("2. PostgreSQL database is running")
        logger.error("3. Network connectivity between app and database")
        logger.error("4. If using internal hostname, ensure app and DB are in same network")
        # Don't raise - let app start

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

# Include routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(user_qr.router, prefix="/api", tags=["user_qr"])
app.include_router(credits.router, prefix="/api", tags=["credits"])
app.include_router(payments.router, prefix="/api", tags=["payments"])
app.include_router(qr.router, prefix="/api", tags=["qr"])
app.include_router(verify.router, prefix="/api", tags=["verify"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the frontend page"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/scanner", response_class=HTMLResponse)
async def read_scanner():
    """Serve the QR scanner page"""
    with open("static/scanner.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard():
    """Serve the user dashboard with QR code"""
    with open("static/dashboard.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/settings", response_class=HTMLResponse)
async def read_settings():
    """Serve the user settings page"""
    # Get the project root directory (parent of app directory)
    project_root = Path(__file__).parent.parent
    settings_path = project_root / "static" / "settings.html"
    with open(settings_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/admin/login", response_class=HTMLResponse)
async def read_admin_login():
    """Serve the admin login page"""
    with open("static/admin_login.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/admin", response_class=HTMLResponse)
async def read_admin():
    """Serve the admin dashboard"""
    with open("static/admin.html", "r") as f:
        return HTMLResponse(content=f.read())

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

