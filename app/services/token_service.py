import secrets
import string
from sqlalchemy.orm import Session
from app.models import AccessToken

TOKEN_ALPHABET = string.ascii_uppercase + string.digits


def generate_unique_token(db: Session, length: int = 6, max_attempts: int = 30) -> str:
    """Generate a unique short token consisting of letters and digits."""
    for _ in range(max_attempts):
        candidate = "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(length))
        exists = db.query(AccessToken.id).filter(AccessToken.token == candidate).first()
        if not exists:
            return candidate
    raise RuntimeError("Unable to generate unique access token")
