import logging
import os
import time
from typing import Dict

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AccessToken, AccessLog, User
from app.routes.verify import VerifyResponse, process_verification
from app.services.scan_processing import process_scan

logger = logging.getLogger(__name__)

router = APIRouter()

RATE_LIMIT_SECONDS = 0.05  # 50 ms per scanner
_last_request_per_scanner: Dict[str, float] = {}
_last_422_log_per_scanner: Dict[str, float] = {}


class ScannerBaseRequest(BaseModel):
    token: str = Field(..., min_length=1)
    scanner_id: str = Field(..., min_length=1)
    raw_data: str | None = None


class ScannerOutResponse(BaseModel):
    ok: bool
    reason: str


class ScanRequest(BaseModel):
    token: str = Field(..., min_length=1)
    timestamp: datetime
    device_id: str = Field(..., min_length=1)


class ScanUser(BaseModel):
    name: str | None = None
    email: str | None = None


class ScanResponse(VerifyResponse):
    open_door: bool = False
    door_open_duration: int | None = None
    user: ScanUser | None = None


def _get_api_key():
    key = os.getenv("TURNSTILE_API_KEY")
    if not key:
        logger.error("TURNSTILE_API_KEY is not configured in the environment.")
    return key


def _require_api_key(request: Request):
    expected = _get_api_key()
    provided = request.headers.get("X-TURNSTILE-API-KEY")
    if not expected or provided != expected:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized turnstile request",
        )


def _enforce_rate_limit(scanner_id: str):
    now = time.monotonic()
    last = _last_request_per_scanner.get(scanner_id)
    if last and (now - last) < RATE_LIMIT_SECONDS:
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests for this scanner",
        )
    _last_request_per_scanner[scanner_id] = now


def _log_422_throttled(scanner_id: str, message: str):
    now = time.monotonic()
    last = _last_422_log_per_scanner.get(scanner_id, 0)
    if now - last >= 1:
        logger.warning(message)
        _last_422_log_per_scanner[scanner_id] = now


@router.post("/scanner/in", response_model=VerifyResponse)
async def scanner_in(
    payload: ScannerBaseRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_api_key(request)
    _enforce_rate_limit(payload.scanner_id)
    token = (payload.token or "").strip()
    if not token:
        _log_422_throttled(payload.scanner_id, "Empty token received on /scanner/in")
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="token is required",
        )

    if len(token) < 1:
        _log_422_throttled(payload.scanner_id, "Too short token on /scanner/in")
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="token is required",
        )

    verify_response = await process_verification(
        token,
        request,
        db,
        direction="in",
        scanner_id=payload.scanner_id,
        raw_data=payload.raw_data,
    )

    if verify_response.reason == "token_not_found":
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="token_not_found",
        )

    if verify_response.reason == "user_not_found":
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="user_not_found",
        )

    return verify_response


@router.post("/scanner/out", response_model=ScannerOutResponse)
async def scanner_out(
    payload: ScannerBaseRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_api_key(request)
    _enforce_rate_limit(payload.scanner_id)
    token = (payload.token or "").strip()
    if not token:
        _log_422_throttled(payload.scanner_id, "Empty token received on /scanner/out")
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="token is required",
        )
    if len(token) < 1:
        _log_422_throttled(payload.scanner_id, "Too short token on /scanner/out")
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="token is required",
        )

    token_obj = db.query(AccessToken).filter(AccessToken.token == token).first()
    if not token_obj:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="token_not_found",
        )
    if not token_obj.is_active:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="token_deactivated",
        )

    user = db.query(User).filter(User.id == token_obj.user_id).first() if token_obj else None
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="user_not_found",
        )

    try:
        access_log = AccessLog(
            token_id=token_obj.id,
            token_string=token,
            status="allow",
            reason="Logged exit",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", None),
            direction="out",
            scanner_id=payload.scanner_id,
            raw_data=payload.raw_data,
        )
        db.add(access_log)
        db.commit()
    except Exception as e:
        logger.error(f"Error logging OUT access: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log exit",
        )

    return ScannerOutResponse(ok=True, reason="logged")


@router.post("/scan/in", response_model=ScanResponse)
async def scan_in(
    payload: ScanRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_api_key(request)
    _enforce_rate_limit(payload.device_id)
    token = (payload.token or "").strip()
    if not token:
        _log_422_throttled(payload.device_id, "Empty token received on /scan/in")
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="token is required",
        )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", None)
    response = process_scan(
        db,
        token_str=token,
        scanned_at=payload.timestamp,
        device_id=payload.device_id,
        device_direction="in",
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return response


@router.post("/scan/out", response_model=ScanResponse)
async def scan_out(
    payload: ScanRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_api_key(request)
    _enforce_rate_limit(payload.device_id)
    token = (payload.token or "").strip()
    if not token:
        _log_422_throttled(payload.device_id, "Empty token received on /scan/out")
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="token is required",
        )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", None)
    response = process_scan(
        db,
        token_str=token,
        scanned_at=payload.timestamp,
        device_id=payload.device_id,
        device_direction="out",
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return response
