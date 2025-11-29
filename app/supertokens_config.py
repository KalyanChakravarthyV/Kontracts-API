import os
from supertokens_python import init, SupertokensConfig, InputAppInfo
from supertokens_python.recipe import session, emailpassword
from supertokens_python.recipe.emailpassword import EmailPasswordRecipe
from supertokens_python.recipe.session import SessionRecipe
from app import config


# -----------------------
# Supertokens Setup
# -----------------------
def setup_supertokens():
    init(
        framework="fastapi",
        supertokens_config=SupertokensConfig(
            connection_uri=config.SUPERTOKENS_CONNECTION_URI,
            api_key=config.SUPERTOKENS_API_KEY
        ),
        app_info=InputAppInfo(
            app_name="Lease Accounting API",
            api_domain=config.API_DOMAIN,
            website_domain=config.WEBSITE_DOMAIN,
            api_base_path=config.API_BASE_PATH,
            website_base_path=config.WEBSITE_BASE_PATH,
        ),
        recipe_list=[
            emailpassword.init(),
            # session.init(cookie_secure=False),
            session.init(
                cookie_secure=False,
                cookie_same_site="none"
            )

        ],
    )