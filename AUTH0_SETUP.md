# Auth0 OAuth2 Setup Guide

This guide explains how to configure Auth0 authentication for the Lease Accounting API.

## Auth0 Application Configuration

### URLs to Configure in Auth0

**Allowed Callback URLs (Redirect URI)**
```
http://localhost:8001/api/v1/auth/callback
```
Add your production callback URL as well:
```
https://your-api-domain.com/api/v1/auth/callback
```

**Allowed Logout URLs (optional)**
```
http://localhost:8001
https://your-api-domain.com
```

**Allowed Web Origins (if using Swagger UI/Browser)**
```
http://localhost:8001
https://your-api-domain.com
```

### Create an Auth0 Application
1. Go to the Auth0 Dashboard → **Applications** → **Create Application**.
2. Choose **Regular Web Application**.
3. Set the callback/logout/web origins above.

### Scopes
Use the standard OpenID scopes:
- `openid`
- `profile`
- `email`
- `offline_access` (for refresh tokens; optional if you need them)

### Get Your Credentials
Copy these from the Auth0 dashboard:
- **Domain** (e.g., `your-tenant.auth0.com`)
- **Client ID**
- **Client Secret**

### Environment Variables
Set these in your `.env` (see `.env.example`):
```
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=your-api-identifier   # optional
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## API Endpoints
- `GET /api/v1/auth/login` – redirect to Auth0 login.
- `GET /api/v1/auth/callback` – handles the code exchange, returns API JWT.
- `GET /api/v1/auth/me` – returns claims from the API JWT.
- `POST /api/v1/auth/logout` – revokes Auth0 token (refresh/access) and invalidates the API JWT.

## Testing
1. Open `http://localhost:8001/docs`.
2. Click **Authorize** and follow the Auth0 login.
3. Use the returned JWT for protected endpoints.

## Production Checklist
- Add production callback/logout URLs in Auth0.
- Use HTTPS everywhere.
- Rotate `CLIENT_SECRET` periodically.
- Move JWT revocation storage to shared infra (e.g., Redis) if running multiple instances.
