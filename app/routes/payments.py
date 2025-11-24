from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, root_validator
from app.database import get_db
from app.models import User, Payment
from app.auth import get_current_user
from app.services.payment_service import create_order, mark_order_failed, mark_order_paid, prepare_comgate_data
from app.services.membership import MembershipService
import uuid
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

SUCCESS_STATUSES = {"PAID", "OK", "SUCCESS", "AUTHORIZED", "CAPTURED", "COMPLETED"}
FAILED_STATUSES = {"CANCELLED", "REJECTED", "FAILED", "ERROR", "DENIED", "TIMEOUT", "DECLINED"}


def _apply_status_from_gateway(db: Session, payment_id: str, status: str | None):
    """Normalize Comgate status responses and update payment accordingly."""
    normalized = (status or "").upper()
    if not normalized:
        return None
    if normalized in SUCCESS_STATUSES:
        try:
            mark_order_paid(db, payment_id)
            return "paid"
        except ValueError as exc:
            logger.info("mark_order_paid skipped for %s: %s", payment_id, exc)
            return None
    if normalized in FAILED_STATUSES:
        try:
            mark_order_failed(db, payment_id, normalized.lower())
            return normalized.lower()
        except ValueError as exc:
            logger.info("mark_order_failed skipped for %s: %s", payment_id, exc)
            return None
    return normalized.lower()


def _success_message(payment: Payment) -> str:
    if payment.payment_type == "membership":
        package_name = None
        if payment.package:
            package_name = payment.package.name
        elif payment.package_snapshot:
            package_name = payment.package_snapshot.get("name") or payment.package_snapshot.get("package_name")
        return f"Platba byla úspěšně dokončena! Aktivována permanentka {package_name or ''}".strip()
    tokens = payment.token_amount or 0
    return f"Platba byla úspěšně dokončena! Přidáno {tokens} vstupů."

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
        "payment_type": payment.payment_type,
        "package_id": payment.package_id,
        "package_name": (payment.package.name if payment.package else None),
        "membership_id": payment.membership_id,
        "user_id": payment.user_id,
        "created_at": payment.created_at,
        "completed_at": payment.completed_at,
        "paid_at": payment.paid_at
    }

# New endpoints for token purchase

class CreatePaymentRequest(BaseModel):
    token_amount: int | None = Field(default=None, description="Number of token entries to purchase (1, 5, or 10)")
    package_id: int | None = Field(default=None, description="ID balíčku/permanentky k zakoupení")

    @root_validator(skip_on_failure=True)
    def validate_payload(cls, values):
        token_amount = values.get("token_amount")
        package_id = values.get("package_id")
        if not token_amount and not package_id:
            raise ValueError("token_amount nebo package_id je povinné")
        if token_amount and package_id:
            raise ValueError("Tokeny ani balíček nelze objednat zároveň")
        return values

class CreatePaymentResponse(BaseModel):
    payment_id: str
    token_amount: int | None = None
    package_id: int | None = None
    package_name: str | None = None
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
    Create a payment order for purchasing credits or membership packages.
    """
    membership_service = MembershipService(db)
    package = None
    package_snapshot = None
    token_amount = None
    price_czk = 0
    payment_type = "credits"

    if request.package_id:
        package = membership_service.get_package(request.package_id)
        if not package or not package.is_active:
            raise HTTPException(status_code=404, detail="Balíček nebyl nalezen nebo je neaktivní")
        payment_type = "membership"
        price_czk = package.price_czk
        token_amount = None
        package_snapshot = {
            "id": package.id,
            "name": package.name,
            "slug": package.slug,
            "package_name": package.name,
            "package_type": package.package_type,
            "duration_days": package.duration_days,
            "daily_entry_limit": package.daily_entry_limit,
            "session_limit": package.session_limit,
            "metadata": package.metadata_json,
        }
    else:
        if request.token_amount not in [1, 5, 10]:
            raise HTTPException(status_code=400, detail="token_amount must be 1, 5, or 10")
        token_amount = request.token_amount
        price_czk = token_amount * 100

    payment = create_order(
        db=db,
        user_id=current_user.id,
        price_czk=price_czk,
        provider="comgate",
        payment_type=payment_type,
        token_amount=token_amount,
        package_id=package.id if package else None,
        package_snapshot=package_snapshot,
    )

    comgate_data = prepare_comgate_data(payment, current_user)

    return CreatePaymentResponse(
        payment_id=payment.payment_id,
        token_amount=payment.token_amount,
        package_id=payment.package_id,
        package_name=package.name if package else None,
        price_czk=payment.price_czk,
        provider=payment.provider,
        redirect_url=comgate_data["redirect_url"],
        status=payment.status,
    )

@router.post("/payments/comgate/notify")
async def comgate_notify(request: Request, db: Session = Depends(get_db)):
    """Callback endpoint for Comgate payment notifications (NOTIFY URL)."""
    form_data = await request.form()
    payload = {k: v for (k, v) in form_data.multi_items()}
    logger.info("Comgate notify received: %s", payload)

    payment_id = payload.get("refId") or payload.get("refid") or payload.get("payment_id")
    if not payment_id:
        raise HTTPException(status_code=400, detail="Missing refId in Comgate notification")

    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    status = payload.get("status") or payload.get("result")
    applied = _apply_status_from_gateway(db, payment_id, status)

    return {
        "status": applied or payment.status,
        "payment_id": payment_id,
    }

@router.get("/payments/comgate/return")
async def comgate_return(
    payment_id: str | None = None,
    status: str | None = None,
    refId: str | None = None,
    code: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Return URL endpoint for Comgate payment redirect.
    User is redirected here after completing payment on Comgate.
    
    TODO: Implement full Comgate return handling
    """
    if not payment_id:
        payment_id = refId
    if not payment_id:
        # Redirect to dashboard with error
        return RedirectResponse(url="/dashboard?payment_error=missing_payment_id")
    
    # Get payment
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    
    if not payment:
        return RedirectResponse(url="/dashboard?payment_error=payment_not_found")
    # Apply status info from query parameters if provided (notify may arrive later)
    status_param = status or code
    applied_status = _apply_status_from_gateway(db, payment.payment_id, status_param)
    if applied_status:
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first() or payment
    
    if payment.status == "paid":
        message = _success_message(payment)
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Platba úspěšná</title>
            <meta http-equiv="refresh" content="3;url=/dashboard">
        </head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>Platba úspěšná</h1>
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
            <h1>Platba zpracovávána</h1>
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
            <h1>Platba selhala</h1>
            <p>{message}</p>
            <p>Přesměrování na dashboard za 5 sekund...</p>
            <a href="/dashboard">Klikněte zde, pokud se nepřesměrujete automaticky</a>
        </body>
        </html>
        """)
