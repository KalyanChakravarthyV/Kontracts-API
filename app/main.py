from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

from .database import engine, Base
from .api.v1 import leases, schedules, payments

import sys
import logging
import logging
from dotenv import load_dotenv

load_dotenv()

# Basic logging to console for FastAPI/uvicorn output
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# Basic logging to console for FastAPI/uvicorn output
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

swagger_ui_init_oauth = {
    "usePkceWithAuthorizationCodeGrant": True,
    "scopes": "openid profile email offline_access",
    "clientSecret": "",  # hide/clear client secret field
}

app = FastAPI(
    title="Lease Accounting API",
    description="""
## Lease Accounting API with Auth0 Authentication

This API provides lease accounting schedule generation for ASC 842 (US GAAP) and IFRS 16 (International) standards.

### Authentication

All endpoints require authentication using Bearer tokens issued by Auth0.
All endpoints require authentication using Bearer tokens issued by Auth0.

**To get started:**
1. Obtain an Auth0 access token for your API audience.
2. Click the **🔓 Authorize** button and enter your token
3. Or add `Bearer <token>` to the Authorization header manually
1. Obtain an Auth0 access token for your API audience.
2. Click the **🔓 Authorize** button and enter your token
3. Or add `Bearer <token>` to the Authorization header manually

### OAuth2 Flow
Use your Auth0-issued token for all API calls.
Use your Auth0-issued token for all API calls.
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
            "description": "Enter the Bearer token issued by Auth0"
        },
    }
            "description": "Enter the Bearer token issued by Auth0"
        },
    }

    # Apply security to all endpoints
    # Apply security to all endpoints
    if "paths" in openapi_schema:
        for path, path_item in openapi_schema["paths"].items():
            for method in path_item:
                if method in ["get", "post", "put", "delete", "patch"]:
                    path_item[method]["security"] = [
                        {"Bearer": []}
                    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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
