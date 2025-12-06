from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from datetime import timedelta

from app.auth import get_current_user, create_access_token
from app.oauth_config import (
    oauth,
    ZOHO_REDIRECT_URI,
    ZOHO_CLIENT_ID,
    ZOHO_CLIENT_SECRET,
    ZOHO_USERINFO_URL,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfoResponse(BaseModel):
    sub: str
    email: str
    name: str
    picture: Optional[str] = None


@router.get("/login")
async def login(request: Request):
    """
    Initiate Zoho OAuth2 login flow.

    This endpoint redirects the user to Zoho's login page.
    After successful authentication, Zoho will redirect back to the callback URL.

    **Important:** Configure this URL in your Zoho Application:
    - Redirect URI: {API_URL}/api/v1/auth/callback
    """
    redirect_uri = ZOHO_REDIRECT_URI
    return await oauth.zoho.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request):
    """
    OAuth2 callback endpoint that receives the authorization code from Zoho.

    This endpoint:
    1. Receives the authorization code from Zoho
    2. Exchanges it for an access token
    3. Fetches user information
    4. Creates a JWT token for the user
    5. Returns the JWT token

    **Important:** Configure this exact URL in your Zoho Application as the Redirect URI.
    """
    if not ZOHO_CLIENT_ID or not ZOHO_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Zoho OAuth client ID/secret not configured. Set ZOHO_CLIENT_ID and ZOHO_CLIENT_SECRET.",
        )

    try:
        # Exchange authorization code for access token
        token = await oauth.zoho.authorize_access_token(request)

        # Get user info from Zoho
        user_info = token.get('userinfo')
        if not user_info:
            # If userinfo not in token, fetch it
            resp = await oauth.zoho.get(ZOHO_USERINFO_URL, token=token)
            user_info = resp.json()

        # Extract user details
        user_id = user_info.get('sub') or user_info.get('ZUID')
        email = user_info.get('email')
        name = user_info.get('name') or user_info.get('Display_Name')

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not retrieve user information from Zoho"
            )

        # Create JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": email,
                "name": name
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
        picture=user.get("picture")
    )


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    Logout endpoint.

    For JWT-based auth, the client should simply delete the token.
    This endpoint validates the token is valid before confirming logout.
    """
    return {
        "message": "Logged out successfully. Please delete your access token on the client side."
    }
