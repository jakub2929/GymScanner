from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
import os

# Database URL - defaults to SQLite, can be overridden with POSTGRES_URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./gym_turnstile.db"
)

# For SQLite, we need check_same_thread=False
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # For Postgres and other databases
    engine = create_engine(DATABASE_URL)

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

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

