from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from supertokens_python.framework.fastapi import get_middleware
from supertokens_python.recipe.session import SessionRecipe
from .supertokens_config import setup_supertokens

from .database import engine, Base
from .api.v1 import auth, leases, schedules, payments

import sys
from dotenv import load_dotenv

load_dotenv()

# Initialize SuperTokens BEFORE FastAPI app starts
setup_supertokens()

app = FastAPI(
    title="Lease Accounting API",
    description="""
## Lease Accounting API with SuperTokens Authentication

This API provides lease accounting schedule generation for ASC 842 (US GAAP) and IFRS 16 (International) standards.

### Authentication

All endpoints except `/auth/signup` and `/auth/signin` require authentication using Bearer tokens.

**To get started:**
1. Use `/api/v1/auth/signup` to create an account
2. Use `/api/v1/auth/signin` to obtain session tokens (stored in cookies)
3. Click the **🔓 Authorize** button below and the authentication will work automatically via cookies
4. Or manually add `Bearer <token>` to the Authorization header

SuperTokens automatically manages session tokens via HTTP-only cookies for browser clients.
    """,
    version="1.0.0",
    swagger_ui_parameters={
        "persistAuthorization": True,
    }
)

# Custom OpenAPI schema to add security definitions
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter the Bearer token from SuperTokens session (usually handled via cookies automatically)"
        },
        "Cookie": {
            "type": "apiKey",
            "in": "cookie",
            "name": "sAccessToken",
            "description": "SuperTokens session cookie (set automatically after signin)"
        }
    }

    # Apply security to all endpoints except auth endpoints
    if "paths" in openapi_schema:
        for path, path_item in openapi_schema["paths"].items():
            # Skip auth endpoints (signup, signin)
            if "/auth/signup" in path or "/auth/signin" in path:
                continue

            # Apply security to all methods in this path
            for method in path_item:
                if method in ["get", "post", "put", "delete", "patch"]:
                    # Add security requirement - try Cookie first, then Bearer
                    path_item[method]["security"] = [
                        {"Cookie": []},
                        {"Bearer": []}
                    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add SuperTokens middleware
app.add_middleware(get_middleware())


@app.on_event("startup")
def on_startup():
    """Create database tables on application startup (not when importing module)"""
    # Only create tables if not running tests
    if "pytest" not in sys.modules:
        Base.metadata.create_all(bind=engine)


# CORS (SuperTokens requires credentials=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kontracts-ui.vadlakonda.in"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "*",
        *SessionRecipe.get_instance().get_all_cors_headers(),
    ],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(leases.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "Lease Accounting API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
