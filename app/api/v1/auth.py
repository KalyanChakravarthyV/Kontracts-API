from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from supertokens_python.recipe.emailpassword.asyncio import sign_up, sign_in
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.session.asyncio import create_new_session
from supertokens_python.types import RecipeUserId

from app.auth import get_current_user
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/auth", tags=["Authentication"])


class SignUpRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")


class SignInRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Password")


class AuthResponse(BaseModel):
    message: str
    user_id: str
    email: str


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: SignUpRequest):
    """
    Register a new user with email and password.

    After successful signup, use the /auth/signin endpoint to obtain session tokens.
    """
    try:
        # Use SuperTokens sign_up function
        result = await sign_up("public", user_data.email, user_data.password)

        if result.status == "OK":
            return AuthResponse(
                message="User created successfully. Please sign in to get access token.",
                user_id=result.user.id,
                email=user_data.email
            )
        elif result.status == "EMAIL_ALREADY_EXISTS_ERROR":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during signup: {str(e)}"
        )


@router.post("/signin", response_model=AuthResponse)
async def signin(credentials: SignInRequest, request: Request, response: Response):
    """
    Sign in with email and password to obtain session tokens.

    Returns session tokens in cookies and response headers.
    SuperTokens automatically sets HTTP-only cookies for session management.

    After signing in:
    - Session cookies are automatically set
    - All subsequent requests will include these cookies
    - Protected endpoints will work automatically
    """
    try:
        # Use SuperTokens sign_in function to validate credentials
        result = await sign_in("public", credentials.email, credentials.password)

        recipe_user = None

        # Check if result has status attribute or is a specific result type
        if hasattr(result, 'status'):
            if result.status == "OK":
                recipe_user = result.user
            elif result.status == "WRONG_CREDENTIALS_ERROR":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to sign in"
                )
        else:
            # Successful sign in returns SignInOkResult directly
            recipe_user = result.user

        # Create a SuperTokens session - this sets the cookies automatically
        # Create RecipeUserId from the string id
        recipe_user_id = RecipeUserId(recipe_user.id)
        await create_new_session(request, "public", recipe_user_id)

        return AuthResponse(
            message="Sign in successful. Session cookies have been set.",
            user_id=recipe_user.id,
            email=credentials.email
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during signin: {str(e)}"
        )


@router.get("/me", response_model=dict)
async def get_current_user_info(session: SessionContainer = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Requires valid session token in Authorization header or cookies.
    """
    user_id = session.get_user_id()
    return {
        "user_id": user_id,
        "session_handle": session.get_handle()
    }


@router.post("/signout")
async def signout(session: SessionContainer = Depends(verify_session())):
    """
    Sign out the current user and revoke session tokens.

    Requires valid session token.
    """
    try:
        await session.revoke_session()
        return {"message": "Signed out successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during signout: {str(e)}"
        )
