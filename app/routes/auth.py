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
    is_admin: bool = False
    is_owner: bool = False
    role: str = "user"

@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Registration attempt for email: {request.email}")
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            logger.warning(f"Registration failed: email already exists - {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user with hashed password
        password_hash = get_password_hash(request.password)
        first_name, last_name = _split_full_name(request.name)
        user = User(
            email=request.email,
            name=request.name.strip(),
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"User registered successfully: {user.email} (ID: {user.id})")
        
        return RegisterResponse(
            message="User registered successfully",
            user_id=user.id
        )
    except HTTPException:
        raise
    except Exception as e:
        # Database connection error or other error
        logger.error(f"Registration error for {request.email}: {e}", exc_info=True)
        db.rollback()  # Rollback on error
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
        role = "owner" if bool(user.is_owner) else ("admin" if bool(user.is_admin) else "user")
        access_token = create_access_token({"sub": str(user.id), "role": role})
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            is_admin=bool(user.is_admin),
            is_owner=bool(user.is_owner),
            role=role,
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
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    created_at: str
    qr_count: int
    email_verified: bool = False  # Email verification not implemented yet
    is_admin: bool = False

class UpdateProfileRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=60)
    last_name: str = Field(..., min_length=1, max_length=80)
    email: EmailStr
    phone_number: str | None = Field(default=None, min_length=5, max_length=40)

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Pole nesmí být prázdné")
        return cleaned

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if cleaned and not any(char.isdigit() for char in cleaned):
            raise ValueError("Telefon musí obsahovat číslice")
        return cleaned or None

def _split_full_name(full_name: str | None) -> tuple[str | None, str | None]:
    if not full_name:
        return None, None
    name = full_name.strip()
    if not name:
        return None, None
    parts = name.split(" ", 1)
    first = parts[0].strip() if parts else None
    last = parts[1].strip() if len(parts) > 1 else None
    return first or None, last or None

def _serialize_user_info(user: User, qr_count: int) -> UserInfoResponse:
    first_name = user.first_name
    last_name = user.last_name
    if not first_name:
        split_first, split_last = _split_full_name(user.name)
        first_name = split_first
        last_name = last_name or split_last
    if not last_name:
        _, split_last = _split_full_name(user.name)
        last_name = last_name or split_last
    created_at_str = user.created_at.isoformat() if user.created_at else ""
    return UserInfoResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        first_name=first_name,
        last_name=last_name,
        phone_number=user.phone_number,
        created_at=created_at_str,
        qr_count=qr_count,
        email_verified=False,
        is_admin=bool(user.is_admin),
    )

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
    
    return _serialize_user_info(current_user, qr_count)

@router.put("/user/profile", response_model=UserInfoResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile information (name/email/phone)."""
    new_email = request.email.lower().strip()
    if new_email != current_user.email:
        duplicate = db.query(User).filter(User.email == new_email).first()
        if duplicate and duplicate.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email je již registrovaný",
            )
        current_user.email = new_email

    current_user.first_name = request.first_name
    current_user.last_name = request.last_name
    # Display name = combination (fallback to first only)
    current_user.name = f"{request.first_name} {request.last_name}".strip()
    current_user.phone_number = request.phone_number

    db.commit()
    db.refresh(current_user)
    qr_count = db.query(AccessToken).filter(AccessToken.user_id == current_user.id).count()
    return _serialize_user_info(current_user, qr_count)

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
