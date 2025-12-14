from datetime import datetime, timedelta
from typing import Optional, Set, Dict, Any
import uuid
import hashlib
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.oauth_config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    TOKEN_ISSUER,
    TOKEN_AUDIENCE,
    AUTH0_DOMAIN,
    AUTH0_AUDIENCE,
)

# Security scheme for Swagger UI
security = HTTPBearer()
revoked_jtis: Set[str] = set()
revoked_token_digests: Set[str] = set()
_auth0_jwks_cache: Dict[str, Any] = {}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing the claims to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    to_encode.setdefault("jti", uuid.uuid4().hex)
    to_encode.setdefault("iss", TOKEN_ISSUER)
    to_encode.setdefault("aud", TOKEN_AUDIENCE)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.

    Validates Auth0 RS256 tokens (if configured) and falls back to local HS256 tokens.
    Also enforces revocation lists.
    """
    auth0_error: Optional[str] = None

    def _check_revocation(payload: dict):
        token_digest = hashlib.sha256(token.encode()).hexdigest()
        if token_digest in revoked_token_digests:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        jti = payload.get("jti")
        if jti and jti in revoked_jtis:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Attempt Auth0 RS256 validation first (if configured)
    if AUTH0_DOMAIN:
        try:
            unverified_header = jwt.get_unverified_header(token)
            if unverified_header.get("alg") == "RS256":
                jwks = _get_auth0_jwks()
                rsa_key = {}
                for key in jwks.get("keys", []):
                    if key.get("kid") == unverified_header.get("kid"):
                        rsa_key = {
                            "kty": key.get("kty"),
                            "kid": key.get("kid"),
                            "use": key.get("use"),
                            "n": key.get("n"),
                            "e": key.get("e"),
                        }
                        break
                if rsa_key:
                    payload = jwt.decode(
                        token,
                        rsa_key,
                        algorithms=["RS256"],
                        audience=AUTH0_AUDIENCE or None,
                        issuer=f"https://{AUTH0_DOMAIN}/",
                        options={
                            "verify_aud": bool(AUTH0_AUDIENCE),
                            "verify_iss": True,
                        },
                    )
                    _check_revocation(payload)
                    return payload
        except JWTError as e:
            auth0_error = str(e)
        except Exception as e:
            auth0_error = str(e)

    # Fallback to local HS256 token
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=TOKEN_ISSUER,
            audience=TOKEN_AUDIENCE,
            options={"verify_aud": bool(TOKEN_AUDIENCE), "verify_iss": bool(TOKEN_ISSUER)},
        )
        _check_revocation(payload)
        return payload
    except JWTError as e:
        detail = "Could not validate credentials"
        if auth0_error:
            detail = f"Could not validate credentials (Auth0 error: {auth0_error})"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def _get_auth0_jwks() -> Dict[str, Any]:
    """Fetch and cache Auth0 JWKS."""
    if _auth0_jwks_cache:
        return _auth0_jwks_cache
    if not AUTH0_DOMAIN:
        return {}
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    try:
        resp = httpx.get(jwks_url, timeout=5.0)
        resp.raise_for_status()
        _auth0_jwks_cache.update(resp.json())
    except Exception:
        return {}
    return _auth0_jwks_cache


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency to get the current authenticated user from JWT token.
    Requires a valid Bearer token in the Authorization header.

    Usage:
        @router.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            user_id = user.get("sub")
            return {"user_id": user_id}
    """
    token = credentials.credentials
    payload = verify_token(token)

    if payload.get("sub") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """
    Dependency to get the current user if authenticated, otherwise None.
    Does not require authentication but provides user info if available.

    Usage:
        @router.get("/optional-auth")
        async def optional_route(user: Optional[dict] = Depends(get_optional_user)):
            if user:
                user_id = user.get("sub")
                return {"user_id": user_id, "authenticated": True}
            return {"authenticated": False}
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = verify_token(token)
        return payload
    except HTTPException:
        return None


def get_user_id(user: dict) -> str:
    """
    Helper function to extract user_id from decoded token payload.

    Usage:
        user_id = get_user_id(user)
    """
    return user.get("sub", "")
