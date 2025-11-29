from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supertokens_python.framework.fastapi import get_middleware
from supertokens_python.recipe.session import SessionRecipe
from .supertokens_config import setup_supertokens

from .database import engine, Base
from .api.v1 import leases, schedules, payments

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Initialize SuperTokens BEFORE FastAPI app starts
setup_supertokens()

app = FastAPI(
    title="Lease Accounting API",
    description="API for generating ASC 842 and IFRS 16 lease accounting schedules",
    version="1.0.0",
)

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
