from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models import User, Payment
import uuid
from datetime import datetime, timezone

router = APIRouter()

class PaymentRequest(BaseModel):
    email: EmailStr
    name: str
    amount: float

class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    user_id: int
    amount: float

@router.post("/create_payment", response_model=PaymentResponse)
async def create_payment(
    payment_request: PaymentRequest,
    db: Session = Depends(get_db)
):
    """
    Create a mock payment. In production, this would integrate with Stripe/PayPal/etc.
    For now, it simulates a successful payment immediately.
    """
    # Find or create user
    user = db.query(User).filter(User.email == payment_request.email).first()
    if not user:
        user = User(
            email=payment_request.email,
            name=payment_request.name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Create payment record
    payment_id = str(uuid.uuid4())
    payment = Payment(
        user_id=user.id,
        amount=payment_request.amount,
        status="completed",  # Mock payment - always succeeds
        payment_id=payment_id,
        completed_at=datetime.now(timezone.utc)
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    return PaymentResponse(
        payment_id=payment.payment_id,
        status=payment.status,
        user_id=user.id,
        amount=payment.amount
    )

@router.get("/payment/{payment_id}")
async def get_payment_status(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """Get payment status by payment_id"""
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "payment_id": payment.payment_id,
        "status": payment.status,
        "amount": payment.amount,
        "user_id": payment.user_id,
        "created_at": payment.created_at,
        "completed_at": payment.completed_at
    }

