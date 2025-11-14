from sqlalchemy.orm import Session
from app.models import Payment, User
from datetime import datetime, timezone
from urllib.parse import parse_qsl
import httpx
import uuid
import os
import logging

logger = logging.getLogger(__name__)

def create_order(db: Session, user_id: int, token_amount: int, price_czk: int, provider: str = "comgate") -> Payment:
    """
    Create a new payment order with status 'pending'.
    
    Args:
        db: Database session
        user_id: ID of the user making the order
        token_amount: Number of tokens to purchase (1, 5, or 10)
        price_czk: Price in CZK
        provider: Payment provider (default: "comgate")
    
    Returns:
        Payment object with status 'pending'
    """
    payment_id = str(uuid.uuid4())
    
    payment = Payment(
        user_id=user_id,
        token_amount=token_amount,
        price_czk=price_czk,
        provider=provider,
        status="pending",
        payment_id=payment_id
    )
    
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    logger.info(f"Created payment order {payment_id} for user {user_id}: {token_amount} tokens for {price_czk} CZK")
    
    return payment

def mark_order_paid(db: Session, payment_id: str) -> Payment:
    """
    Mark a payment order as paid and add tokens to user's account.
    This function is idempotent - calling it multiple times won't add tokens twice.
    
    Args:
        db: Database session
        payment_id: Payment ID to mark as paid
    
    Returns:
        Updated Payment object
    
    Raises:
        ValueError: If payment not found or already paid
    """
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    
    if not payment:
        raise ValueError(f"Payment {payment_id} not found")
    
    # Idempotent check: if already paid, just return the payment
    if payment.status == "paid":
        logger.info(f"Payment {payment_id} already marked as paid, skipping")
        return payment
    
    # Only process if status is 'pending'
    if payment.status != "pending":
        raise ValueError(f"Payment {payment_id} has status '{payment.status}', cannot mark as paid")
    
    # Get user
    user = db.query(User).filter(User.id == payment.user_id).first()
    if not user:
        raise ValueError(f"User {payment.user_id} not found for payment {payment_id}")
    
    # Update payment and add tokens in a transaction
    now = datetime.now(timezone.utc)
    payment.status = "paid"
    payment.paid_at = now
    payment.updated_at = now
    
    # Add tokens to user
    user.credits = (user.credits or 0) + payment.token_amount
    
    db.commit()
    db.refresh(payment)
    db.refresh(user)
    
    logger.info(f"Payment {payment_id} marked as paid. Added {payment.token_amount} tokens to user {user.id}. New balance: {user.credits}")
    
    return payment

def mark_order_failed(db: Session, payment_id: str, status: str = "failed") -> Payment:
    """
    Update payment status to failed/cancelled without crediting tokens.
    """
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    
    if not payment:
        raise ValueError(f"Payment {payment_id} not found")
    
    if payment.status == "paid":
        logger.info("Payment %s already paid, ignoring failure update (%s)", payment_id, status)
        return payment
    
    normalized_status = status or "failed"
    now = datetime.now(timezone.utc)
    payment.status = normalized_status
    payment.updated_at = now
    db.commit()
    db.refresh(payment)
    logger.info("Payment %s updated to status %s", payment_id, normalized_status)
    return payment

def prepare_comgate_data(payment: Payment, user: User) -> dict:
    """
    Call Comgate test/production API and return redirect payload.
    Falls back to placeholder redirect if configuration/API call fails.
    """
    merchant_id = os.getenv("COMGATE_MERCHANT_ID")
    secret = os.getenv("COMGATE_SECRET")
    test_mode = os.getenv("COMGATE_TEST_MODE", "true").lower() == "true"
    api_url = os.getenv("COMGATE_API_URL", "https://payments.comgate.cz/v1.0/create")
    return_url = os.getenv("COMGATE_RETURN_URL", "https://localhost/api/payments/comgate/return")
    notify_url = os.getenv("COMGATE_NOTIFY_URL", "https://localhost/api/payments/comgate/notify")
    default_phone = os.getenv("COMGATE_DEFAULT_PHONE", "")
    prepare_only = os.getenv("COMGATE_PREPARE_ONLY", "0")

    if not merchant_id or not secret:
        logger.warning("Comgate credentials missing, falling back to placeholder redirect URL")
        return {
            "redirect_url": f"https://example.com/comgate-placeholder?payment_id={payment.payment_id}&amount={payment.price_czk}",
            "payment_id": payment.payment_id,
            "amount": payment.price_czk,
            "currency": "CZK",
            "merchant_id": merchant_id or "PLACEHOLDER",
            "test_mode": test_mode,
            "notify_url": notify_url,
            "return_url": return_url,
            "provider_status": "missing_credentials",
        }

    payload = {
        "merchant": merchant_id,
        "test": 1 if test_mode else 0,
        # HTTP POST expects price in haléřích (cents)
        "price": (payment.price_czk or 0) * 100,
        "curr": "CZK",
        "label": f"GymScanner - {payment.token_amount} tokens",
        "refId": payment.payment_id,
        "method": "ALL",
        "email": user.email,
        "phone": default_phone or "",
        "notifyUrl": notify_url,
        "returnUrl": return_url,
        "secret": secret,
        "prepareOnly": 1 if str(prepare_only).lower() in {"1", "true"} else 0,
    }

    try:
        logger.info("Calling Comgate HTTP POST API for payment %s", payment.payment_id)
        with httpx.Client(timeout=15.0) as client:
            response = client.post(api_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        response.raise_for_status()
        parsed = dict(parse_qsl(response.text, keep_blank_values=True))
        redirect_url = parsed.get("redirect") or parsed.get("redirectUrl")
        result = parsed.get("code") or parsed.get("result") or "0"

        if not redirect_url or result not in {"0", "OK"}:
            logger.error("Comgate HTTP POST create failed (code=%s, body=%s)", result, response.text)
            raise RuntimeError(f"Comgate HTTP POST create failed (code={result})")

        return {
            "redirect_url": redirect_url,
            "payment_id": payment.payment_id,
            "amount": payment.price_czk,
            "currency": "CZK",
            "merchant_id": merchant_id,
            "test_mode": test_mode,
            "notify_url": notify_url,
            "return_url": return_url,
            "provider_status": result,
            "comgate_response": parsed,
        }
    except Exception as exc:
        logger.exception("Comgate API call failed for payment %s: %s", payment.payment_id, exc)
        return {
            "redirect_url": f"https://payments.comgate.cz/v1.0/create?refId={payment.payment_id}&price={payment.price_czk}",
            "payment_id": payment.payment_id,
            "amount": payment.price_czk,
            "currency": "CZK",
            "merchant_id": merchant_id,
            "test_mode": test_mode,
            "notify_url": notify_url,
            "return_url": return_url,
            "provider_status": "error",
        }
