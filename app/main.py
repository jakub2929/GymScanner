from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

from app.database import engine, Base, ensure_access_token_columns
from app.routes import payments, qr, verify, admin

# Create database tables
Base.metadata.create_all(bind=engine)
ensure_access_token_columns()

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

# Include routers
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

@app.get("/admin", response_class=HTMLResponse)
async def read_admin():
    """Serve the admin dashboard"""
    with open("static/admin.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

