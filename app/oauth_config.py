"""
Auth0 OAuth2 Configuration
"""
import os
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

load_dotenv()

# Auth0 OAuth2 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "")
AUTH0_REDIRECT_URI = os.getenv("AUTH0_REDIRECT_URI", "http://localhost:8001/api/v1/auth/callback")

def _clean_audience(raw: str) -> str:
    """Sanitize audience env (ignore commented placeholder values)."""
    val = (raw or "").strip()
    if not val:
        return ""
    if val.startswith("#"):
        return ""
    if "optional api identifier" in val.lower():
        return ""
    return val

AUTH0_AUDIENCE = _clean_audience(os.getenv("AUTH0_AUDIENCE", ""))
AUTH0_USERINFO_URL = f"https://{AUTH0_DOMAIN}/userinfo" if AUTH0_DOMAIN else ""

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
TOKEN_ISSUER = os.getenv("TOKEN_ISSUER", "lease-accounting-api")
TOKEN_AUDIENCE = os.getenv("TOKEN_AUDIENCE", "lease-accounting-api")


# Initialize OAuth
oauth = OAuth()

# Register Auth0 OAuth2 provider
if AUTH0_DOMAIN:
    oauth.register(
        name='auth0',
        client_id=AUTH0_CLIENT_ID,
        client_secret=AUTH0_CLIENT_SECRET,
        server_metadata_url=f'https://{AUTH0_DOMAIN}/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid profile email offline_access'
        }
    )
