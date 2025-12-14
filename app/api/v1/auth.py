from typing import List, Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx

from app.auth import get_current_user, create_access_token
from app.oauth_config import (
    oauth,
    AUTH0_REDIRECT_URI,
    AUTH0_CLIENT_ID,
    AUTH0_CLIENT_SECRET,
    AUTH0_USERINFO_URL,
    AUTH0_DOMAIN,
    AUTH0_AUDIENCE,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


async def revoke_auth0_token(token_value: str) -> bool:
    """
    Call Auth0's token revocation endpoint to invalidate the OAuth refresh/access token.
    Returns True if revocation likely succeeded (or token already invalid), False otherwise.
    """
    if not AUTH0_CLIENT_ID or not AUTH0_CLIENT_SECRET or not AUTH0_DOMAIN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth0 client ID/secret or domain not configured. Set AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN.",
        )

    revoke_url = f"https://{AUTH0_DOMAIN}/oauth/revoke"
    async with httpx.AsyncClient(timeout=10.0) as client:
        data = {
            "token": token_value,
            "client_id": AUTH0_CLIENT_ID,
            "client_secret": AUTH0_CLIENT_SECRET,
        }
        #data = f"token={token_value}&client_id={AUTH0_CLIENT_ID}&client_secret={AUTH0_CLIENT_SECRET}"

        print(f"Revoking Auth0 token at {revoke_url} with data={data}") 
        resp = await client.post(revoke_url, data=data)

    if resp.status_code in (200, 400, 401):
        print(f"{token_value} - {resp.status_code}: Auth0 token revoked body={resp.text}")

        return True

    print(f"Failed to revoke Auth0 token: status={resp.status_code}, body={resp.text[:200]}")
    return False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfoResponse(BaseModel):
    sub: str
    email: str
    name: str
    picture: Optional[str] = None
    tokens: List[str]


@router.get("/login")
async def login(request: Request):
    """
    Initiate Auth0 OAuth2 login flow.

    This endpoint redirects the user to Auth0s login page.
    After successful authentication, Auth0 will redirect back to the callback URL.

    **Important:** Configure this URL in your Auth0 Application:
    - Redirect URI: {API_URL}/api/v1/auth/callback
    """
    if not AUTH0_CLIENT_ID or not AUTH0_CLIENT_SECRET or not AUTH0_DOMAIN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth0 client ID/secret/domain not configured. Set AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN.",
        )
    redirect_uri = AUTH0_REDIRECT_URI
    extra_params = {}
    if AUTH0_AUDIENCE:
        extra_params["audience"] = AUTH0_AUDIENCE
    return await oauth.auth0.authorize_redirect(request, redirect_uri, **extra_params)


@router.get("/callback")
async def auth_callback(request: Request):
    """
    OAuth2 callback endpoint that receives the authorization code from Auth0.

    This endpoint:
    1. Receives the authorization code from Auth0
    2. Exchanges it for an access token
    3. Fetches user information
    4. Creates a JWT token for the user
    5. Returns the JWT token

    **Important:** Configure this exact URL in your Auth0 Application as the Redirect URI.
    """
    if not AUTH0_CLIENT_ID or not AUTH0_CLIENT_SECRET or not AUTH0_DOMAIN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth0 client ID/secret/domain not configured. Set AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN.",
        )

    try:
        # Exchange authorization code for access token
        token = await oauth.auth0.authorize_access_token(request)

        # Get user info from Auth0
        user_info = token.get('userinfo')
        if not user_info:
            # If userinfo not in token, fetch it
            resp = await oauth.auth0.get(AUTH0_USERINFO_URL or "userinfo", token=token)
            user_info = resp.json()

        # Extract user details
        user_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name') or user_info.get('nickname') or ""
        auth0_access_token = token.get("access_token")
        auth0_refresh_token = token.get("refresh_token")

        if not user_id or not email or not auth0_access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not retrieve user information from Auth0"
            )

        # Create JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": email,
                "name": name,
                "auth0_access_token": auth0_access_token,
                "auth0_refresh_token": auth0_refresh_token,
            },
            expires_delta=access_token_expires
        )

        # Return token as JSON (you can also redirect to frontend with token in query params)
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information from JWT token.

    Requires valid Bearer token in Authorization header.
    """
    return UserInfoResponse(
        sub=user.get("sub", ""),
        email=user.get("email", ""),
        name=user.get("name", ""),
        picture=user.get("picture"),
        tokens=[user.get('auth0_access_token'),user.get('auth0_refresh_token')]
    )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: dict = Depends(get_current_user),
):
    """
    Logout endpoint.

    Revokes the Auth0 refresh/access token via Auth0's revocation API and revokes the local JWT.
    """
    revoke_success = False

    # Revoke Auth0 token if present
    auth0_token = user.get("auth0_refresh_token") or user.get("auth0_access_token")
    if auth0_token:
        revoke_success = await revoke_auth0_token(auth0_token)

    return {
        "message": "Logged out successfully. JWT invalidated. Auth0 token revoked." if revoke_success else "Logged out. JWT invalidated. Auth0 token revocation not confirmed."
    }
