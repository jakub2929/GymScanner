from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
from datetime import datetime, timedelta, timezone

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    credits = Column(Integer, default=0)  # Number of credits (1 credit = 1 workout)
    is_admin = Column(Boolean, default=False)  # Admin privileges
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    payments = relationship("Payment", back_populates="user")
    access_tokens = relationship("AccessToken", back_populates="user")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=True)  # Legacy field, kept for backward compatibility
    token_amount = Column(Integer, nullable=True)  # Number of tokens in this order
    price_czk = Column(Integer, nullable=True)  # Price in CZK (for precision)
    status = Column(String, default="pending")  # pending, paid, failed, cancelled
    provider = Column(String, default="comgate")  # Payment provider (comgate, etc.)
    payment_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)  # When payment was completed
    completed_at = Column(DateTime(timezone=True), nullable=True)  # Legacy field, kept for backward compatibility
    
    user = relationship("User", back_populates="payments")
    access_tokens = relationship("AccessToken", back_populates="payment")

class AccessToken(Base):
    __tablename__ = "access_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)  # Optional for user-based tokens
    is_used = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    scan_count = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Nullable - no expiration needed for credit system
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    last_scan_at = Column(DateTime(timezone=True), nullable=True)  # Last successful scan time for cooldown (user-level)
    
    user = relationship("User", back_populates="access_tokens")
    payment = relationship("Payment", back_populates="access_tokens")
    access_logs = relationship("AccessLog", back_populates="token")
    
    def is_valid(self, user_credits: int = 0):
        """Check if token is valid (active and user has credits)"""
        if not self.is_active:
            return False
        # Check if user has credits (1 credit = 1 workout)
        if user_credits <= 0:
            return False
        return True

class AccessLog(Base):
    __tablename__ = "access_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("access_tokens.id"), nullable=True)
    token_string = Column(String, nullable=False)  # Store token string even if token is deleted
    status = Column(String, nullable=False)  # allow, deny
    reason = Column(String, nullable=True)  # Reason for allow/deny
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    token = relationship("AccessToken", back_populates="access_logs")

