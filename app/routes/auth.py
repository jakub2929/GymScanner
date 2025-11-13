from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Annotated
from app.database import get_db
from app.models import User
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from app.models import AccessToken
import os
from datetime import timedelta

router = APIRouter()

class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        # Simple email validation
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        return v.lower().strip()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        # Minimum length check
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class RegisterResponse(BaseModel):
    message: str
    user_id: int

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    user_name: str
    user_email: str

@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user with hashed password
        password_hash = get_password_hash(request.password)
        user = User(
            email=request.email,
            name=request.name,
            password_hash=password_hash
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return RegisterResponse(
            message="User registered successfully",
            user_id=user.id
        )
    except HTTPException:
        raise
    except Exception as e:
        # Database connection error or other error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not verify_password(form_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token (sub must be a string for JWT standard)
        access_token = create_access_token({"sub": str(user.id)})
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            user_name=user.name,
            user_email=user.email
        )
    except HTTPException:
        raise
    except Exception as e:
        # Database connection error or other error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/logout")
async def logout():
    """
    Logout endpoint - clears server-side session if needed.
    Client should clear localStorage on frontend.
    """
    return {"message": "Logged out successfully"}

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class ChangePasswordResponse(BaseModel):
    message: str

class UserInfoResponse(BaseModel):
    user_id: int
    email: str
    name: str
    created_at: str
    qr_count: int
    email_verified: bool = False  # Email verification not implemented yet

@router.get("/user/info", response_model=UserInfoResponse)
async def get_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user account information including created date and QR code count.
    Optional endpoint for settings page.
    """
    # Count user's access tokens (QR codes generated)
    qr_count = db.query(AccessToken).filter(
        AccessToken.user_id == current_user.id
    ).count()
    
    # Format created_at date
    created_at_str = current_user.created_at.isoformat() if current_user.created_at else ""
    
    return UserInfoResponse(
        user_id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        created_at=created_at_str,
        qr_count=qr_count,
        email_verified=False  # Email verification not implemented yet
    )

@router.post("/user/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password.
    Requires current password verification.
    Optional endpoint for settings page.
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Check if new password is different from current
    if verify_password(request.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Hash new password
    new_password_hash = get_password_hash(request.new_password)
    
    # Update user password
    current_user.password_hash = new_password_hash
    db.commit()
    db.refresh(current_user)
    
    return ChangePasswordResponse(
        message="Password changed successfully"
    )

