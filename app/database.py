from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
import os
import logging

logger = logging.getLogger(__name__)

# Database URL - must be set in environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the environment.")

# Normalize postgres:// URLs for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

if not DATABASE_URL.startswith(("postgresql://", "postgresql+")):
    raise RuntimeError(
        f"Unsupported DATABASE_URL '{DATABASE_URL}'. "
        "Only PostgreSQL connections are allowed."
    )

engine = create_engine(DATABASE_URL)

logger.info(f"Using database: {DATABASE_URL}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def ensure_access_token_columns():
    inspector = inspect(engine)
    if 'access_tokens' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('access_tokens')]
    alters = []
    if 'is_active' not in columns:
        alters.append("ALTER TABLE access_tokens ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
    if 'scan_count' not in columns:
        alters.append("ALTER TABLE access_tokens ADD COLUMN scan_count INTEGER DEFAULT 0")
    if not alters:
        with engine.begin() as conn:
            conn.execute(text("UPDATE access_tokens SET is_active = TRUE WHERE is_active IS NULL"))
            conn.execute(text("UPDATE access_tokens SET scan_count = 0 WHERE scan_count IS NULL"))
        return
    with engine.begin() as conn:
        for statement in alters:
            conn.execute(text(statement))
        inspector_after = inspect(engine)
        columns_after = [col['name'] for col in inspector_after.get_columns('access_tokens')]
        if 'is_active' in columns_after:
            conn.execute(text("UPDATE access_tokens SET is_active = TRUE WHERE is_active IS NULL"))
        if 'scan_count' in columns_after:
            conn.execute(text("UPDATE access_tokens SET scan_count = 0 WHERE scan_count IS NULL"))

def ensure_user_password_column():
    """Ensure users table has password_hash column"""
    inspector = inspect(engine)
    if 'users' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'password_hash' not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR"))

def ensure_user_credits_column():
    """Ensure users table has credits column"""
    inspector = inspect(engine)
    if 'users' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'credits' not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 0"))
            # Set default credits for existing users
            conn.execute(text("UPDATE users SET credits = 0 WHERE credits IS NULL"))

def ensure_user_admin_column():
    """Ensure users table has is_admin column"""
    inspector = inspect(engine)
    if 'users' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'is_admin' not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
            # Set default is_admin for existing users
            conn.execute(text("UPDATE users SET is_admin = FALSE WHERE is_admin IS NULL"))

def ensure_user_owner_column():
    """Ensure users table has is_owner column"""
    inspector = inspect(engine)
    if 'users' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'is_owner' not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_owner BOOLEAN DEFAULT FALSE"))
            conn.execute(text("UPDATE users SET is_owner = FALSE WHERE is_owner IS NULL"))

def ensure_access_token_nullable_columns():
    """Ensure access_tokens table has nullable payment_id and expires_at"""
    print("[MIGRATION] ensure_access_token_nullable_columns called")
    inspector = inspect(engine)
    if 'access_tokens' not in inspector.get_table_names():
        print("[MIGRATION] access_tokens table does not exist, will be created with nullable columns")
        logger.info("access_tokens table does not exist, will be created with nullable columns")
        return
    
    dialect = engine.dialect.name
    print(f"[MIGRATION] Checking access_tokens table for nullable columns (dialect: {dialect})")
    logger.info("Ensuring access_tokens payment_id and expires_at columns are nullable (PostgreSQL)")
    
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE access_tokens ALTER COLUMN payment_id DROP NOT NULL"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE access_tokens ALTER COLUMN expires_at DROP NOT NULL"))
        except Exception:
            pass

def ensure_last_scan_at_column():
    """Ensure access_tokens table has last_scan_at column for cooldown tracking"""
    inspector = inspect(engine)
    if 'access_tokens' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('access_tokens')]
    if 'last_scan_at' not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE access_tokens ADD COLUMN last_scan_at TIMESTAMP"))

def ensure_payment_comgate_columns():
    """Ensure payments table has columns for Comgate integration"""
    inspector = inspect(engine)
    if 'payments' not in inspector.get_table_names():
        return
    
    columns = [col['name'] for col in inspector.get_columns('payments')]
    alters = []
    
    # Add token_amount column
    if 'token_amount' not in columns:
        alters.append("ALTER TABLE payments ADD COLUMN token_amount INTEGER")
    
    # Add price_czk column
    if 'price_czk' not in columns:
        alters.append("ALTER TABLE payments ADD COLUMN price_czk INTEGER")
    
    # Add provider column
    if 'provider' not in columns:
        alters.append("ALTER TABLE payments ADD COLUMN provider VARCHAR DEFAULT 'comgate'")
    
    # Add paid_at column
    if 'paid_at' not in columns:
        alters.append("ALTER TABLE payments ADD COLUMN paid_at TIMESTAMP")
    
    # Add updated_at column
    if 'updated_at' not in columns:
        alters.append("ALTER TABLE payments ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    # Make amount nullable (for backward compatibility)
    # Note: SQLite doesn't support ALTER COLUMN to change NULL constraint easily
    # We'll leave amount as is for now, but new payments will use price_czk
    
    if alters:
        with engine.begin() as conn:
            for statement in alters:
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    logger.warning(f"Error executing migration statement: {statement}, error: {e}")
                    # Continue with other migrations even if one fails

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
