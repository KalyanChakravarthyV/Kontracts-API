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
AUTH0_HTTPX_VERIFY_SSL=true
```

## API Endpoints
- Obtain Auth0 access tokens via your Auth0 tenant (no auth endpoints hosted here).
- Use `Authorization: Bearer <access_token>` for all protected endpoints.

## Testing
1. Open `http://localhost:8001/docs`.
2. Use the 🔓 Authorize button to paste a valid Auth0 access token for your API audience.

## Production Checklist
- Use HTTPS everywhere.
- Rotate Auth0 client secrets periodically.
