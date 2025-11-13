from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from app.database import get_db
from app.models import User, Payment
from app.auth import get_current_user
from app.services.payment_service import create_order, mark_order_paid, prepare_comgate_data
import uuid
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

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
        "token_amount": payment.token_amount,
        "price_czk": payment.price_czk,
        "user_id": payment.user_id,
        "created_at": payment.created_at,
        "completed_at": payment.completed_at,
        "paid_at": payment.paid_at
    }

# New endpoints for token purchase

class CreatePaymentRequest(BaseModel):
    token_amount: int = Field(..., description="Number of tokens to purchase (1, 5, or 10)")

class CreatePaymentResponse(BaseModel):
    payment_id: str
    token_amount: int
    price_czk: int
    provider: str
    redirect_url: str
    status: str

@router.post("/payments/create", response_model=CreatePaymentResponse)
async def create_payment_order(
    request: CreatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a payment order for purchasing tokens.
    Validates token_amount (must be 1, 5, or 10) and creates a pending payment.
    """
    # Validate token_amount
    if request.token_amount not in [1, 5, 10]:
        raise HTTPException(
            status_code=400,
            detail="token_amount must be 1, 5, or 10"
        )
    
    # Calculate price (100 CZK per token)
    price_czk = request.token_amount * 100
    
    # Create payment order
    payment = create_order(
        db=db,
        user_id=current_user.id,
        token_amount=request.token_amount,
        price_czk=price_czk,
        provider="comgate"
    )
    
    # Prepare Comgate redirect data
    comgate_data = prepare_comgate_data(payment)
    
    return CreatePaymentResponse(
        payment_id=payment.payment_id,
        token_amount=payment.token_amount,
        price_czk=payment.price_czk,
        provider=payment.provider,
        redirect_url=comgate_data["redirect_url"],
        status=payment.status
    )

@router.post("/payments/comgate/notify")
async def comgate_notify(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Callback endpoint for Comgate payment notifications (NOTIFY URL).
    This endpoint is called by Comgate when payment status changes.
    
    TODO: Implement Comgate signature validation
    TODO: Parse Comgate notification data
    TODO: Mark payment as paid and add tokens to user
    """
    # Get raw body for signature validation
    body = await request.body()
    form_data = await request.form()
    
    logger.info(f"Comgate notify received: {dict(form_data)}")
    
    # TODO: Validate Comgate signature
    # signature = form_data.get("signature")
    # expected_signature = calculate_comgate_signature(form_data)
    # if signature != expected_signature:
    #     logger.error("Invalid Comgate signature")
    #     raise HTTPException(status_code=400, detail="Invalid signature")
    
    # TODO: Parse payment_id from Comgate notification
    # payment_id = form_data.get("refId")  # or whatever Comgate sends
    # status = form_data.get("status")  # "PAID", "CANCELLED", etc.
    
    # For now, return placeholder response
    return {
        "status": "ok",
        "message": "Comgate notify endpoint - TODO: implement full integration"
    }

@router.get("/payments/comgate/return")
async def comgate_return(
    payment_id: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    Return URL endpoint for Comgate payment redirect.
    User is redirected here after completing payment on Comgate.
    
    TODO: Implement full Comgate return handling
    """
    if not payment_id:
        # Redirect to dashboard with error
        return RedirectResponse(url="/dashboard?payment_error=missing_payment_id")
    
    # Get payment
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    
    if not payment:
        return RedirectResponse(url="/dashboard?payment_error=payment_not_found")
    
    # TODO: Verify payment status with Comgate API
    # For now, just show status page
    
    if payment.status == "paid":
        message = f"Platba byla úspěšně dokončena! Přidáno {payment.token_amount} tokenů."
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Platba úspěšná</title>
            <meta http-equiv="refresh" content="3;url=/dashboard">
        </head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>✅ Platba úspěšná</h1>
            <p>{message}</p>
            <p>Přesměrování na dashboard za 3 sekundy...</p>
            <a href="/dashboard">Klikněte zde, pokud se nepřesměrujete automaticky</a>
        </body>
        </html>
        """)
    elif payment.status == "pending":
        message = "Platba je stále zpracovávána. Prosím počkejte."
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Platba zpracovávána</title>
            <meta http-equiv="refresh" content="5;url=/dashboard">
        </head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>⏳ Platba zpracovávána</h1>
            <p>{message}</p>
            <p>Přesměrování na dashboard za 5 sekund...</p>
            <a href="/dashboard">Klikněte zde, pokud se nepřesměrujete automaticky</a>
        </body>
        </html>
        """)
    else:
        message = "Platba selhala nebo byla zrušena."
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Platba selhala</title>
            <meta http-equiv="refresh" content="5;url=/dashboard">
        </head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>❌ Platba selhala</h1>
            <p>{message}</p>
            <p>Přesměrování na dashboard za 5 sekund...</p>
            <a href="/dashboard">Klikněte zde, pokud se nepřesměrujete automaticky</a>
        </body>
        </html>
        """)

