import os
from supertokens_python import init, SupertokensConfig, InputAppInfo
from supertokens_python.recipe import session, emailpassword
from supertokens_python.recipe.emailpassword import EmailPasswordRecipe
from supertokens_python.recipe.session import SessionRecipe


def setup_supertokens():
    init(
        framework="fastapi",
        supertokens_config=SupertokensConfig(
            connection_uri=os.getenv("SUPERTOKENS_URI", "https://st-dev-fdf12c91-9afd-11f0-9aaa-5376855ce515.aws.supertokens.io")
        ),
        app_info = InputAppInfo(
            app_name="Lease Accounting API",
            api_domain="http://localhost:8000",
            # website_domain="http://localhost:3000",
            website_domain="https://kontracts-ui.vadlakonda.in",
            api_base_path="/auth",
            website_base_path="/auth",
        ),
        recipe_list=[
            emailpassword.init(),         # Email/password login
            session.init(cookie_secure=False),               # Enable sessions
        ],
    )
