#!/usr/bin/env python3
"""
Skript pro nastavení admina v databázi.
Použití: python set_admin.py <email>
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import User

# Získej DATABASE_URL z environment nebo použij default
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ Chyba: DATABASE_URL není nastaven v environment variables!")
    print("Nastav PostgreSQL connection string, např.:")
    print("  export DATABASE_URL='postgresql+psycopg2://gymuser:gympass@localhost:5432/gym_turnstile'")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

if not DATABASE_URL.startswith(("postgresql://", "postgresql+")):
    print("❌ Tato aplikace nyní podporuje pouze PostgreSQL. Zadaný DATABASE_URL je neplatný.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def set_admin(email: str):
    """Nastav uživatele jako admina"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ Uživatel s emailem '{email}' nebyl nalezen!")
            print("\nDostupní uživatelé:")
            users = db.query(User).all()
            if users:
                for u in users:
                    print(f"  - {u.email} (ID: {u.id}, Admin: {u.is_admin})")
            else:
                print("  (žádní uživatelé v databázi)")
            return False
        
        if user.is_admin:
            print(f"✅ Uživatel '{email}' už je admin!")
            return True
        
        user.is_admin = True
        db.commit()
        print(f"✅ Uživatel '{email}' byl nastaven jako admin!")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Chyba při nastavování admina: {e}")
        return False
    finally:
        db.close()

def list_users():
    """Vypiš všechny uživatele"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("📭 V databázi nejsou žádní uživatelé.")
            return
        
        print("\n📋 Seznam uživatelů:")
        print("-" * 60)
        for user in users:
            admin_status = "✅ Admin" if user.is_admin else "❌ User"
            print(f"  {user.email:30} | {admin_status} | Credits: {user.credits}")
        print("-" * 60)
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("📝 Použití: python set_admin.py <email>")
        print("   nebo:   python set_admin.py --list")
        print("\nPříklad:")
        print("  python set_admin.py admin@example.com")
        sys.exit(1)
    
    if sys.argv[1] == "--list" or sys.argv[1] == "-l":
        list_users()
    else:
        email = sys.argv[1]
        set_admin(email)
