import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    set_refresh_cookie,
)
from app.schemas.auth import (
    AuthTokensResponse,
    GoogleUrlResponse,
    UserInfo,
)
from app.services.auth import get_or_create_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)
optional_bearer = HTTPBearer(auto_error=False)


@router.get("/google/url", response_model=GoogleUrlResponse)
async def get_google_auth_url(allow_create: bool = False) -> GoogleUrlResponse:
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": f"allow_create:{'true' if allow_create else 'false'}",
    }
    # Assemble query string manually to avoid extra dependencies
    query = urlencode(params)
    return GoogleUrlResponse(auth_url=f"{base_url}?{query}")


@router.get("/google/callback")
async def google_callback(
    code: str,
    response: Response,
    state: str | None = None,
    allow_create: bool = False,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    token_endpoint = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        token_res = await client.post(token_endpoint, data=payload)
    if token_res.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange code with Google",
        )

    token_data = token_res.json()
    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing id_token from Google response",
        )

    # NOTE: For MVP we decode without verifying signature.
    decoded = jwt.decode(id_token, options={"verify_signature": False, "verify_aud": False})
    sub = decoded.get("sub")
    email = decoded.get("email")
    name = decoded.get("name") or email

    if not sub or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google token payload",
        )

    allow_create_flag = allow_create
    if state and state.startswith("allow_create:"):
        allow_create_flag = state.split("allow_create:")[1].lower() == "true"

    try:
        user = await get_or_create_user(
            session=session,
            google_sub=sub,
            email=email,
            display_name=name,
            allow_create=allow_create_flag,
        )
    except ValueError as e:
        # Signup not allowed in this flow
        logger.warning(f"User creation failed: {e}")
        redirect_url = f"{settings.frontend_url}/login?error=signup_not_allowed"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except Exception as e:
        # Database connection error or other unexpected errors
        logger.error(f"Database error during user creation: {e}", exc_info=True)
        redirect_url = f"{settings.frontend_url}/login?error=database_error"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    access_expires = timedelta(minutes=settings.access_token_ttl_min)
    refresh_expires = timedelta(days=settings.refresh_token_ttl_day)

    access_token = create_access_token(
        subject=str(user.id),
        secret=settings.jwt_secret,
        expires_delta=access_expires,
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        secret=settings.jwt_secret,
        expires_delta=refresh_expires,
    )

    set_refresh_cookie(response, refresh_token, settings)
    redirect_url = f"{settings.frontend_url}/dashboard?access_token={access_token}"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.post("/refresh", response_model=AuthTokensResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthTokensResponse:
    # The refresh token is expected in HttpOnly cookie
    refresh_token: Optional[str] = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    try:
        payload = decode_token(refresh_token, settings.jwt_secret)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc) or "Invalid refresh token",
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    try:
        user = await get_or_create_user(
            session=session,
            google_sub=None,
            email=None,
            display_name=None,
            user_id=int(user_id),
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    access_expires = timedelta(minutes=settings.access_token_ttl_min)
    refresh_expires = timedelta(days=settings.refresh_token_ttl_day)

    access_token = create_access_token(
        subject=str(user.id),
        secret=settings.jwt_secret,
        expires_delta=access_expires,
    )
    new_refresh = create_refresh_token(
        subject=str(user.id),
        secret=settings.jwt_secret,
        expires_delta=refresh_expires,
    )
    set_refresh_cookie(response, new_refresh, settings)

    return AuthTokensResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserInfo(id=user.id, email=user.email, display_name=user.display_name),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> UserInfo:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = decode_token(token, settings.jwt_secret)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc) or "Invalid token",
        )
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user = await get_or_create_user(
            session=session,
            google_sub=None,
            email=None,
            display_name=None,
            user_id=int(sub),
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return UserInfo(id=user.id, email=user.email, display_name=user.display_name)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    session: AsyncSession = Depends(get_session),
) -> UserInfo | None:
    if not credentials:
        return None
    token = credentials.credentials
    try:
        payload = decode_token(token, settings.jwt_secret)
    except ValueError:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        user = await get_or_create_user(
            session=session,
            google_sub=None,
            email=None,
            display_name=None,
            user_id=int(sub),
        )
    except ValueError:
        return None
    return UserInfo(id=user.id, email=user.email, display_name=user.display_name)
