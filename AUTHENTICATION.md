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
AUTH0_CLIENT_ID=<your-client-id>
AUTH0_CLIENT_SECRET=<your-client-secret>
AUTH0_REDIRECT_URI=http://localhost:8001/api/v1/auth/callback
# AUTH0_AUDIENCE is optional (API Identifier)
AUTH0_AUDIENCE=
SECRET_KEY=<jwt-signing-key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
TOKEN_ISSUER=lease-accounting-api
TOKEN_AUDIENCE=lease-accounting-api
```

## Using the token
1) Hit `/api/v1/auth/login` in the browser and complete Auth0 auth.  
2) Copy the `access_token` returned by `/api/v1/auth/callback`.  
3) Send it as `Authorization: Bearer <token>` to protected endpoints or via the 🔓 Authorize button in Swagger UI.

### Logout
- `POST /api/v1/auth/logout` revokes the Auth0 token via `https://<AUTH0_DOMAIN>/oauth/revoke` and invalidates the JWT (process-local; uses `jti` if present, otherwise hashes the raw token). Clients should still discard the token. For multi-instance deployments, back the JWT revocation store with shared infra (e.g., Redis).
