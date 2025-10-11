from typing import Any, Dict
from supertokens_python import (
    InputAppInfo,
    SupertokensConfig,
)
from supertokens_python.recipe import emailpassword, session
from supertokens_python.recipe.emailpassword.interfaces import APIInterface, APIOptions
from supertokens_python.recipe.emailpassword.types import FormField
from supertokens_python.recipe.session.interfaces import APIInterface as SessionAPIInterface
import os
from dotenv import load_dotenv

load_dotenv()

# Get configuration from environment variables
SUPERTOKENS_CONNECTION_URI = os.getenv("SUPERTOKENS_CONNECTION_URI", "https://try.supertokens.com")
SUPERTOKENS_API_KEY = os.getenv("SUPERTOKENS_API_KEY", "")
API_DOMAIN = os.getenv("API_DOMAIN", "http://localhost:8000")
WEBSITE_DOMAIN = os.getenv("WEBSITE_DOMAIN", "http://localhost:3000")
API_BASE_PATH = os.getenv("API_BASE_PATH", "/auth")
WEBSITE_BASE_PATH = os.getenv("WEBSITE_BASE_PATH", "/auth")


def get_supertokens_config() -> SupertokensConfig:
    """Returns SuperTokens configuration"""
    return SupertokensConfig(
        connection_uri=SUPERTOKENS_CONNECTION_URI,
        api_key=SUPERTOKENS_API_KEY
    )


def get_app_info() -> InputAppInfo:
    """Returns app info for SuperTokens"""
    return InputAppInfo(
        app_name="Lease Accounting API",
        api_domain=API_DOMAIN,
        website_domain=WEBSITE_DOMAIN,
        api_base_path=API_BASE_PATH,
        website_base_path=WEBSITE_BASE_PATH,
    )


def get_recipe_list():
    """Returns list of SuperTokens recipes (authentication methods)"""
    return [
        emailpassword.init(),
        session.init(),
    ]
