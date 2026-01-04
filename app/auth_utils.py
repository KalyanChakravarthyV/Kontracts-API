from typing import Optional # 

import jwt  # 
from fastapi import Depends, HTTPException, status  # 
from fastapi.security import SecurityScopes, HTTPAuthorizationCredentials, HTTPBearer  # 
from app.config import get_settings
import logging
import traceback
import requests
import json
from jwt.algorithms import RSAAlgorithm


logger = logging.getLogger(__name__)


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str, **kwargs):
        """Returns HTTP 403"""
        super().__init__(status.HTTP_403_FORBIDDEN, detail=detail)

class UnauthenticatedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Requires authentication"
        )

class VerifyToken:
    """Does all the token verification using PyJWT"""
    def __init__(self):
        self.config = get_settings()

        self.jwks_url = f'https://{self.config.auth0_domain}/.well-known/jwks.json'
        self._jwks_cache = None

    def _get_signing_key(self, token_str: str):
        """Fetch JWKS with configurable SSL verify and return signing key for kid."""
        try:
            unverified_header = jwt.get_unverified_header(token_str)
        except Exception as e:
            raise UnauthorizedException(str(e))

        kid = unverified_header.get("kid")
        if not kid:
            raise UnauthorizedException("Missing 'kid' in token header")

        # Fetch JWKS (cache per-process)
        if not self._jwks_cache:
            resp = requests.get(self.jwks_url, timeout=5, verify=self.config.auth0_httpx_verify_ssl)
            resp.raise_for_status()
            self._jwks_cache = resp.json()

        for key in self._jwks_cache.get("keys", []):
            if key.get("kid") == kid:
                return RSAAlgorithm.from_jwk(json.dumps(key))

        raise UnauthorizedException("Unable to find matching key in JWKS")
    
    async def verify(self,
                     security_scopes: SecurityScopes,
                     token: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer())
                     ):
        logger.info("Verifying token with security scopes: %s", security_scopes.scopes)
        if token is None:
            raise UnauthenticatedException

        # This gets the 'kid' from the passed token
        try:
            signing_key = self._get_signing_key(token.credentials)
            logger.info("Obtained signing key for token verification")
        except Exception as error:
            traceback_str = traceback.format_exc()
            logger.error("Exception caught! Details:\n%s", traceback_str)
            raise UnauthorizedException(str(error))

        try:
            payload = jwt.decode(
                token.credentials,
                signing_key,
                algorithms=self.config.auth0_algorithms,
                audience=self.config.auth0_api_audience,
                issuer=self.config.auth0_issuer,
            )
        except Exception as error:
            traceback_str = traceback.format_exc()
            logger.error("Exception caught! Details:\n%s", traceback_str)       
            raise UnauthorizedException(str(error))
    
        return payload
