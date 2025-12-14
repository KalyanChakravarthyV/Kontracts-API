from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    auth0_domain: str
    auth0_api_audience: str
    auth0_issuer: str
    auth0_algorithms: str
    auth0_valid_client_ids: List[str]
    
    HTTPX_VERIFY_SSL: bool = True

    class Config:
        env_file = ".auth0.env"

@lru_cache()
def get_settings():
    return Settings()