from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from .database import engine, Base
from .api.v1 import leases, schedules, payments

import sys
import logging
from dotenv import load_dotenv  

load_dotenv()

# Basic logging to console for FastAPI/uvicorn output
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(
    title="Lease Accounting API",
    description=(
        "Lease Accounting API with Auth0 authentication.\n\n"
        "This API provides lease accounting schedule generation for ASC 842 (US GAAP) "
        "and IFRS 16 (International) standards.\n\n"
        "Authentication: All endpoints require Bearer tokens issued by Auth0 for your "
        "API audience. Generate tokens via your Auth0 tenant and authorize requests with "
        "`Authorization: Bearer <token>`."
    ),
    version="1.0.0",
    swagger_ui_parameters={
        "persistAuthorization": True,
    },
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
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter the Bearer token issued by Auth0",
    }

    # Apply security to all endpoints
    if "paths" in openapi_schema:
        for _, path_item in openapi_schema["paths"].items():
            for method in path_item:
                if method in ["get", "post", "put", "delete", "patch"]:
                    path_item[method]["security"] = [{"Auth0Bearer": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

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
