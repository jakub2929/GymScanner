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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    payments = relationship("Payment", back_populates="user")
    access_tokens = relationship("AccessToken", back_populates="user")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending, completed, failed
    payment_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="payments")
    access_tokens = relationship("AccessToken", back_populates="payment")

class AccessToken(Base):
    __tablename__ = "access_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    is_used = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    scan_count = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="access_tokens")
    payment = relationship("Payment", back_populates="access_tokens")
    access_logs = relationship("AccessLog", back_populates="token")
    
    def is_valid(self):
        """Check if token is valid (not expired and active)"""
        if not self.is_active:
            return False
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
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

