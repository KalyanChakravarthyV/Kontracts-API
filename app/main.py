from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

from .database import engine, Base
from .api.v1 import auth, leases, schedules, payments
from .oauth_config import SECRET_KEY, AUTH0_DOMAIN, AUTH0_CLIENT_ID

import sys
from dotenv import load_dotenv

load_dotenv()

swagger_ui_init_oauth = {
    "usePkceWithAuthorizationCodeGrant": True,
    "scopes": "openid profile email offline_access",
    "clientSecret": "",  # hide/clear client secret field
}
if AUTH0_CLIENT_ID:
    swagger_ui_init_oauth["clientId"] = AUTH0_CLIENT_ID

app = FastAPI(
    title="Lease Accounting API",
    description="""
## Lease Accounting API with Auth0 Authentication

This API provides lease accounting schedule generation for ASC 842 (US GAAP) and IFRS 16 (International) standards.

### Authentication

All endpoints except `/auth/login` and `/auth/callback` require authentication using Bearer tokens issued after Auth0 login.

**To get started:**
1. Visit `/api/v1/auth/login` to initiate Auth0 login
2. After successful login, you'll receive a JWT access token from this API
3. Click the **🔓 Authorize** button and enter your token
4. Or add `Bearer <token>` to the Authorization header manually

### OAuth2 Flow
1. User visits `/api/v1/auth/login`
2. Redirected to Auth0 login page
3. After login, redirected back to `/api/v1/auth/callback`
4. Receive JWT token in response
5. Use token for all subsequent API calls
    """,
    version="1.0.0",
    swagger_ui_parameters={
        "persistAuthorization": True,
    },
    swagger_ui_init_oauth=swagger_ui_init_oauth,
    docs_url=None,  # custom docs route below to hide client_id/secret inputs
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
            "description": "Enter the Bearer token returned after Auth0 login"
        },
        "Auth0OAuth2": {
            "type": "oauth2",
            "description": "Auth0 OAuth2 (authorization code with PKCE). Use Authorize to start the login redirect.",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": f"https://{AUTH0_DOMAIN}/authorize" if AUTH0_DOMAIN else "/api/v1/auth/login",
                    "tokenUrl": f"https://{AUTH0_DOMAIN}/oauth/token" if AUTH0_DOMAIN else "/api/v1/auth/callback",
                    "scopes": {
                        "openid": "OpenID",
                        "profile": "Profile",
                        "email": "Email",
                        "offline_access": "Refresh tokens",
                    },
                },
            },
        },
    }

    # Apply security to all endpoints except auth login and callback
    if "paths" in openapi_schema:
        for path, path_item in openapi_schema["paths"].items():
            # Skip auth endpoints (login, callback)
            if "/auth/login" in path or "/auth/callback" in path:
                continue

            # Apply security to all methods in this path
            for method in path_item:
                if method in ["get", "post", "put", "delete", "patch"]:
                    # Add security requirement - Bearer token
                    path_item[method]["security"] = [
                        {"Bearer": []}
                    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add session middleware for OAuth2
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


@app.get("/docs", include_in_schema=False)
async def overridden_swagger():
    """
    Custom Swagger UI that hides client_id/client_secret inputs.
    """
    html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Docs",
        swagger_ui_parameters={
            "persistAuthorization": True,
            "oauth2RedirectUrl": "http://localhost:8001/api/v1/auth/callback",
            "initOAuth": swagger_ui_init_oauth,
        },
    )
    hide_inputs_script = """
    <script>
    (function() {
      function hideInputs() {
        const selectors = [
          "input[name='client_id']",
          "input[name='clientId']",
          "input[aria-label='client_id']",
          "input[placeholder='client id']",
          "input[name='client_secret']",
          "input[aria-label='client_secret']",
          "input[placeholder='client secret']"
        ];
        selectors.forEach(sel => {
          document.querySelectorAll(sel).forEach(el => {
            const wrapper = el.closest('div');
            if (wrapper) { wrapper.style.display = 'none'; }
          });
        });
      }
      const obs = new MutationObserver(hideInputs);
      obs.observe(document.body, { childList: true, subtree: true });
      hideInputs();
    })();
    </script>
    """
    # Remove original Content-Length because we append script
    headers = {k: v for k, v in html.headers.items() if k.lower() != "content-length"}
    return HTMLResponse(
        content=html.body.decode() + hide_inputs_script,
        status_code=html.status_code,
        headers=headers,
        media_type="text/html",
    )


@app.get("/docs/oauth2-redirect", include_in_schema=False)
async def swagger_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.on_event("startup")
def on_startup():
    """Create database tables on application startup (not when importing module)"""
    # Only create tables if not running tests
    if "pytest" not in sys.modules:
        Base.metadata.create_all(bind=engine)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kontracts-ui.vadlakonda.in", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
