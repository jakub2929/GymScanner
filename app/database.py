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

# Volitelná normalizace aliasu postgres:// → postgresql:// (default: vypnuto)
# Některé platformy (např. Heroku/Coolify) používají schéma postgres://, které
# SQLAlchemy nemusí podporovat přímo. Pokud chceš automatickou konverzi, nastav
# NORMALIZE_POSTGRES_URL=true v environment proměnných.
normalize_flag = os.getenv("NORMALIZE_POSTGRES_URL", "false").lower() in {"1", "true", "yes"}
if DATABASE_URL.startswith("postgres://") and normalize_flag:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# For SQLite, we need check_same_thread=False
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # For Postgres and other databases
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
    dialect = engine.dialect.name
    default_true = "1" if dialect == "sqlite" else "TRUE"
    if 'is_active' not in columns:
        alters.append(f"ALTER TABLE access_tokens ADD COLUMN is_active BOOLEAN DEFAULT {default_true}")
    if 'scan_count' not in columns:
        alters.append("ALTER TABLE access_tokens ADD COLUMN scan_count INTEGER DEFAULT 0")
    if not alters:
        with engine.begin() as conn:
            conn.execute(text("UPDATE access_tokens SET is_active = 1 WHERE is_active IS NULL"))
            conn.execute(text("UPDATE access_tokens SET scan_count = 0 WHERE scan_count IS NULL"))
        return
    with engine.begin() as conn:
        for statement in alters:
            conn.execute(text(statement))
        inspector_after = inspect(engine)
        columns_after = [col['name'] for col in inspector_after.get_columns('access_tokens')]
        if 'is_active' in columns_after:
            conn.execute(text("UPDATE access_tokens SET is_active = 1 WHERE is_active IS NULL"))
        if 'scan_count' in columns_after:
            conn.execute(text("UPDATE access_tokens SET scan_count = 0 WHERE scan_count IS NULL"))

def ensure_user_password_column():
    """Ensure users table has password_hash column"""
    inspector = inspect(engine)
    if 'users' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'password_hash' not in columns:
        # For SQLite, we can add nullable column, then update existing users
        # For demo purposes, existing users without password will need to re-register
        dialect = engine.dialect.name
        with engine.begin() as conn:
            if dialect == "sqlite":
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR"))
            else:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR"))

def ensure_user_credits_column():
    """Ensure users table has credits column"""
    inspector = inspect(engine)
    if 'users' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'credits' not in columns:
        dialect = engine.dialect.name
        with engine.begin() as conn:
            if dialect == "sqlite":
                conn.execute(text("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 0"))
            else:
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
        dialect = engine.dialect.name
        default_false = "0" if dialect == "sqlite" else "FALSE"
        with engine.begin() as conn:
            if dialect == "sqlite":
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
            else:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
            # Set default is_admin for existing users
            conn.execute(text(f"UPDATE users SET is_admin = {default_false} WHERE is_admin IS NULL"))

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
    logger.info(f"Checking access_tokens table for nullable columns (dialect: {dialect})")
    
    if dialect == "sqlite":
        # SQLite doesn't support ALTER COLUMN to change NULL constraint
        # We need to recreate the table with nullable columns
        with engine.begin() as conn:
            try:
                # Get column info using PRAGMA
                result = conn.execute(text("PRAGMA table_info(access_tokens)"))
                columns = result.fetchall()
                print(f"[MIGRATION] Found {len(columns)} columns in access_tokens table")
                logger.info(f"Found {len(columns)} columns in access_tokens table")
                
                # Find payment_id column
                # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
                payment_id_info = None
                for col in columns:
                    if col[1] == 'payment_id':
                        payment_id_info = col
                        break
                
                if payment_id_info:
                    notnull = payment_id_info[3]  # 0 = nullable, 1 = NOT NULL
                    print(f"[MIGRATION] payment_id column found: notnull={notnull}")
                    logger.info(f"payment_id column found: notnull={notnull}")
                    
                    if notnull == 1:  # NOT NULL = 1
                        # Column is NOT NULL, need to recreate table
                        print("[MIGRATION] payment_id is NOT NULL, recreating access_tokens table to allow NULL")
                        logger.warning("payment_id is NOT NULL, recreating access_tokens table to allow NULL")
                        
                        # Create new table with nullable columns
                        conn.execute(text("""
                            CREATE TABLE access_tokens_new (
                                id INTEGER PRIMARY KEY,
                                token VARCHAR NOT NULL UNIQUE,
                                user_id INTEGER NOT NULL,
                                payment_id INTEGER,
                                is_used BOOLEAN DEFAULT 0,
                                is_active BOOLEAN DEFAULT 1,
                                scan_count INTEGER DEFAULT 0,
                                expires_at TIMESTAMP,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                used_at TIMESTAMP,
                                FOREIGN KEY(user_id) REFERENCES users(id),
                                FOREIGN KEY(payment_id) REFERENCES payments(id)
                            )
                        """))
                        
                        # Copy data
                        conn.execute(text("""
                            INSERT INTO access_tokens_new 
                            (id, token, user_id, payment_id, is_used, is_active, scan_count, expires_at, created_at, used_at)
                            SELECT id, token, user_id, payment_id, is_used, is_active, scan_count, expires_at, created_at, used_at
                            FROM access_tokens
                        """))
                        
                        # Drop old table and rename new one
                        conn.execute(text("DROP TABLE access_tokens"))
                        conn.execute(text("ALTER TABLE access_tokens_new RENAME TO access_tokens"))
                        
                        # Recreate indexes
                        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_access_tokens_token ON access_tokens(token)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_access_tokens_user_id ON access_tokens(user_id)"))
                        
                        logger.info("Successfully recreated access_tokens table with nullable payment_id")
                    else:
                        logger.info("payment_id is already nullable, no migration needed")
                else:
                    logger.warning("payment_id column not found in access_tokens table")
            except Exception as e:
                logger.error(f"Error ensuring nullable columns: {str(e)}", exc_info=True)
                # If migration fails, continue - might already be correct
    else:
        # For PostgreSQL, we can alter the column
        with engine.begin() as conn:
            try:
                conn.execute(text("ALTER TABLE access_tokens ALTER COLUMN payment_id DROP NOT NULL"))
            except Exception as e:
                # Column might already be nullable
                pass
            try:
                conn.execute(text("ALTER TABLE access_tokens ALTER COLUMN expires_at DROP NOT NULL"))
            except Exception as e:
                # Column might already be nullable
                pass

def ensure_last_scan_at_column():
    """Ensure access_tokens table has last_scan_at column for cooldown tracking"""
    inspector = inspect(engine)
    if 'access_tokens' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('access_tokens')]
    if 'last_scan_at' not in columns:
        dialect = engine.dialect.name
        with engine.begin() as conn:
            if dialect == "sqlite":
                conn.execute(text("ALTER TABLE access_tokens ADD COLUMN last_scan_at TIMESTAMP"))
            else:
                conn.execute(text("ALTER TABLE access_tokens ADD COLUMN last_scan_at TIMESTAMP"))

def ensure_payment_comgate_columns():
    """Ensure payments table has columns for Comgate integration"""
    inspector = inspect(engine)
    if 'payments' not in inspector.get_table_names():
        return
    
    columns = [col['name'] for col in inspector.get_columns('payments')]
    dialect = engine.dialect.name
    alters = []
    
    # Add token_amount column
    if 'token_amount' not in columns:
        if dialect == "sqlite":
            alters.append("ALTER TABLE payments ADD COLUMN token_amount INTEGER")
        else:
            alters.append("ALTER TABLE payments ADD COLUMN token_amount INTEGER")
    
    # Add price_czk column
    if 'price_czk' not in columns:
        if dialect == "sqlite":
            alters.append("ALTER TABLE payments ADD COLUMN price_czk INTEGER")
        else:
            alters.append("ALTER TABLE payments ADD COLUMN price_czk INTEGER")
    
    # Add provider column
    if 'provider' not in columns:
        if dialect == "sqlite":
            alters.append("ALTER TABLE payments ADD COLUMN provider VARCHAR DEFAULT 'comgate'")
        else:
            alters.append("ALTER TABLE payments ADD COLUMN provider VARCHAR DEFAULT 'comgate'")
    
    # Add paid_at column
    if 'paid_at' not in columns:
        if dialect == "sqlite":
            alters.append("ALTER TABLE payments ADD COLUMN paid_at TIMESTAMP")
        else:
            alters.append("ALTER TABLE payments ADD COLUMN paid_at TIMESTAMP")
    
    # Add updated_at column
    if 'updated_at' not in columns:
        if dialect == "sqlite":
            alters.append("ALTER TABLE payments ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        else:
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

