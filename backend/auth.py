"""
Google OAuth2 + JWT (access + refresh tokens).
Requires: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, JWT_SECRET, FRONTEND_URL.
Optional: ACCESS_TOKEN_EXPIRE_MINUTES (default 30), REFRESH_TOKEN_EXPIRE_DAYS (default 30).
"""
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

_raw_secret = os.getenv("JWT_SECRET")
if not _raw_secret:
    import warnings
    warnings.warn(
        "JWT_SECRET is not set in environment. A temporary secret was generated — "
        "all tokens will be invalidated on restart. Set JWT_SECRET in .env for production.",
        stacklevel=1,
    )
JWT_SECRET: str = _raw_secret or secrets.token_hex(32)

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "medical-ai"

security = HTTPBearer(auto_error=False)


# --- OAuth state CSRF protection ---

def sign_oauth_state(state: str) -> str:
    """Return 'state.HMAC_sig' — binds the state value to our secret to prevent CSRF."""
    sig = hmac.new(JWT_SECRET.encode(), state.encode(), hashlib.sha256).hexdigest()
    return f"{state}.{sig}"


def verify_oauth_state(signed_state: str) -> str:
    """Verify HMAC signature and return the original state. Raises HTTPException on failure."""
    parts = signed_state.rsplit(".", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid OAuth state format")
    state, sig = parts
    expected = hmac.new(JWT_SECRET.encode(), state.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=400, detail="OAuth state verification failed (possible CSRF)")
    return state


# --- Google OAuth helpers ---

def build_google_login_url(redirect_uri: str, state: str) -> str:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_user(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Google token exchange failed")
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token from Google")

        user_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")
        return user_res.json()


# --- Access token ---

def create_access_token(user_id: int, google_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "google_id": google_id,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iss": JWT_ISSUER,
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate an access token.
    Raises HTTPException(401) on expiry, HTTPException(403) on any other failure.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong token type")
    return payload


# --- Refresh token ---

def create_refresh_token(user_id: int) -> tuple[str, str]:
    """Return (jti, encoded_token). Store jti in DB for revocation."""
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iss": JWT_ISSUER,
        "type": "refresh",
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return jti, token


def decode_refresh_token(token: str) -> dict:
    """
    Decode and validate a refresh token.
    Raises HTTPException(401) on expiry, HTTPException(403) on any other failure.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "jti", "type"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong token type")
    return payload


# --- FastAPI dependency ---

async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> int:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_access_token(credentials.credentials)
    if "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token claims")
    return int(payload["sub"])


# --- Legacy alias (remove after full migration) ---

def create_jwt(user_id: int, google_id: str) -> str:
    """Deprecated: use create_access_token instead."""
    return create_access_token(user_id, google_id)
