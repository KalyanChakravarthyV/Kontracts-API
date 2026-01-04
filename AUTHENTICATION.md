# Authentication (Auth0 + JWT)

The API uses Auth0 for login and then issues a short-lived JWT for subsequent requests.

## Flow
- `GET /api/v1/auth/login`: redirect to Auth0 for consent.
- `GET /api/v1/auth/callback`: exchanges the code, fetches user info, and returns a JWT.
- `GET /api/v1/auth/me`: verify the JWT and return the user claims.
- `POST /api/v1/auth/logout`: revokes the Auth0 refresh/access token and invalidates the JWT.

## Configuration
Set these environment variables (see `.env.example`):
```
AUTH0_DOMAIN=<your-tenant>.auth0.com
# AUTH0_AUDIENCE is optional (API Identifier)
AUTH0_AUDIENCE=
AUTH0_HTTPX_VERIFY_SSL=true
TOKEN_ISSUER=lease-accounting-api
TOKEN_AUDIENCE=lease-accounting-api
```

## Using the token
1) Obtain an Auth0 access token for your API audience outside of this service.  
2) Send it as `Authorization: Bearer <token>` to protected endpoints or via the 🔓 Authorize button in Swagger UI.

### Logout
Auth0 token revocation is not hosted here; revoke tokens in Auth0 as needed. Clients should still discard tokens when logging out.
