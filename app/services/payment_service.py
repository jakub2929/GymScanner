from sqlalchemy.orm import Session
from app.models import Payment, User
from datetime import datetime, timezone
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

def prepare_comgate_data(payment: Payment) -> dict:
    """
    Prepare data for Comgate API request.
    
    When calling Comgate API 'create', these URLs must be sent as parameters:
    - notifyUrl: Where Comgate will send payment status notifications (POST)
    - returnUrl: Where user will be redirected after payment (GET)
    
    Comgate stores these URLs with the payment and uses them for callbacks.
    
    Args:
        payment: Payment object
    
    Returns:
        Dictionary with Comgate API data including notifyUrl and returnUrl
    """
    # Get Comgate configuration from environment
    merchant_id = os.getenv("COMGATE_MERCHANT_ID", "")
    test_mode = os.getenv("COMGATE_TEST_MODE", "true").lower() == "true"
    
    # Get URLs from environment - these will be sent to Comgate API
    return_url = os.getenv("COMGATE_RETURN_URL", "https://localhost/api/payments/comgate/return")
    notify_url = os.getenv("COMGATE_NOTIFY_URL", "https://localhost/api/payments/comgate/notify")
    
    # TODO: In future, this will make actual Comgate API call
    # The API call will include notifyUrl and returnUrl as parameters
    # Example:
    # r = requests.post('https://payments.comgate.cz/v1.0/create', params={
    #     'merchant': merchant_id,
    #     'test': 1 if test_mode else 0,
    #     'price': payment.price_czk,
    #     'curr': 'CZK',
    #     'refId': payment.payment_id,
    #     'notifyUrl': notify_url,  # ← Comgate will call this for notifications
    #     'returnUrl': return_url,  # ← User will be redirected here after payment
    #     'secret': secret,
    #     # ... další parametry
    # })
    # redirect_url = response.json()['redirectUrl']  # URL na platební stránku Comgate
    
    # For now, return placeholder redirect URL
    # In production, this will be the actual Comgate payment page URL from API response
    if merchant_id:
        # If configured, show that we would redirect to Comgate
        redirect_url = f"https://payments.comgate.cz/v1.0/create?refId={payment.payment_id}&price={payment.price_czk}"
    else:
        # If Comgate is not configured, return placeholder
        redirect_url = f"https://example.com/comgate-placeholder?payment_id={payment.payment_id}&amount={payment.price_czk}"
        logger.warning("COMGATE_MERCHANT_ID not set, using placeholder redirect URL")
    
    return {
        "redirect_url": redirect_url,
        "payment_id": payment.payment_id,
        "amount": payment.price_czk,
        "currency": "CZK",
        "merchant_id": merchant_id if merchant_id else "PLACEHOLDER",
        "test_mode": test_mode,
        "notify_url": notify_url,  # This will be sent to Comgate API as 'notifyUrl' parameter
        "return_url": return_url    # This will be sent to Comgate API as 'returnUrl' parameter
    }

