from typing import Optional
from fastapi import Depends, HTTPException, status
from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.session import SessionContainer


async def get_current_user(session: SessionContainer = Depends(verify_session())):
    """
    Dependency to get the current authenticated user.
    Requires a valid SuperTokens session.

    Usage:
        @router.get("/protected")
        async def protected_route(session: SessionContainer = Depends(get_current_user)):
            user_id = session.get_user_id()
            return {"user_id": user_id}
    """
    return session


async def get_optional_user(session: Optional[SessionContainer] = Depends(verify_session(session_required=False))):
    """
    Dependency to get the current user if authenticated, otherwise None.
    Does not require authentication but provides user info if available.

    Usage:
        @router.get("/optional-auth")
        async def optional_route(session: Optional[SessionContainer] = Depends(get_optional_user)):
            if session:
                user_id = session.get_user_id()
                return {"user_id": user_id, "authenticated": True}
            return {"authenticated": False}
    """
    return session


def get_user_id(session: SessionContainer) -> str:
    """
    Helper function to extract user_id from session.

    Usage:
        user_id = get_user_id(session)
    """
    return session.get_user_id()
