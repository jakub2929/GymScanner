from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import User, Payment
from app.auth import get_current_user
import uuid
from datetime import datetime, timezone

router = APIRouter()

class BuyCreditsRequest(BaseModel):
    amount: float  # Payment amount
    credits: int  # Number of credits to buy

class BuyCreditsResponse(BaseModel):
    message: str
    credits_purchased: int
    total_credits: int
    payment_id: str

@router.post("/buy_credits", response_model=BuyCreditsResponse)
async def buy_credits(
    request: BuyCreditsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Buy credits for the authenticated user.
    Mock payment - in production, integrate with real payment gateway.
    """
    if request.credits <= 0:
        raise HTTPException(status_code=400, detail="Credits must be greater than 0")
    
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    # Create mock payment
    payment_id = str(uuid.uuid4())
    payment = Payment(
        user_id=current_user.id,
        amount=request.amount,
        status="completed",
        payment_id=payment_id,
        completed_at=datetime.now(timezone.utc)
    )
    db.add(payment)
    
    # Add credits to user
    current_user.credits = (current_user.credits or 0) + request.credits
    db.commit()
    db.refresh(current_user)
    
    return BuyCreditsResponse(
        message="Credits purchased successfully",
        credits_purchased=request.credits,
        total_credits=current_user.credits,
        payment_id=payment_id
    )

@router.get("/my_credits")
async def get_my_credits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's credit balance"""
    return {
        "credits": current_user.credits or 0,
        "user_name": current_user.name,
        "user_email": current_user.email
    }

