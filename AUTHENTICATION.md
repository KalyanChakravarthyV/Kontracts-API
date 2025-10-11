# Authentication with SuperTokens

This API is secured using [SuperTokens](https://supertokens.com/) with EmailPassword authentication and session management.

## Overview

All API endpoints under `/api/v1/leases` and `/api/v1/schedules` now require authentication. Users must sign up, log in, and maintain a valid session to access these endpoints.

## Authentication Endpoints

SuperTokens automatically provides the following authentication endpoints:

### Sign Up
```bash
POST http://localhost:8000/auth/signup
Content-Type: application/json

{
  "formFields": [
    {
      "id": "email",
      "value": "user@example.com"
    },
    {
      "id": "password",
      "value": "your-secure-password"
    }
  ]
}
```

### Sign In
```bash
POST http://localhost:8000/auth/signin
Content-Type: application/json

{
  "formFields": [
    {
      "id": "email",
      "value": "user@example.com"
    },
    {
      "id": "password",
      "value": "your-secure-password"
    }
  ]
}
```

### Sign Out
```bash
POST http://localhost:8000/auth/signout
```

### Check Session
```bash
GET http://localhost:8000/auth/session/refresh
```

## Using Protected Endpoints

After signing in, SuperTokens sets session cookies that are automatically sent with subsequent requests. All lease and schedule endpoints now require these session cookies.

### Example: Creating a Lease (Authenticated)

1. First, sign up or sign in:
```bash
curl -X POST http://localhost:8000/auth/signin \
  -H "Content-Type: application/json" \
  -d '{
    "formFields": [
      {"id": "email", "value": "user@example.com"},
      {"id": "password", "value": "your-password"}
    ]
  }' \
  -c cookies.txt
```

2. Then use the session cookies for API requests:
```bash
curl -X POST http://localhost:8000/api/v1/leases/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "lease_name": "Office Building Lease",
    "lessor_name": "ABC Properties",
    "lessee_name": "XYZ Corporation",
    "commencement_date": "2024-01-01",
    "lease_term_months": 60,
    "periodic_payment": 10000.00,
    "payment_frequency": "monthly",
    "initial_direct_costs": 5000.00,
    "prepaid_rent": 10000.00,
    "lease_incentives": 2000.00,
    "residual_value": 0.00,
    "incremental_borrowing_rate": 0.05,
    "discount_rate": 0.05,
    "classification": "operating"
  }'
```

## Environment Configuration

The following environment variables control SuperTokens configuration:

```env
# SuperTokens Core Service
SUPERTOKENS_CONNECTION_URI=https://try.supertokens.com
SUPERTOKENS_API_KEY=

# API Configuration
API_DOMAIN=http://localhost:8000
WEBSITE_DOMAIN=http://localhost:3000
API_BASE_PATH=/auth
WEBSITE_BASE_PATH=/auth
```

### Development Setup

For development, you can use the free demo SuperTokens service (`https://try.supertokens.com`). This is suitable for testing but not for production.

### Production Setup

For production, you should either:

1. **Self-host SuperTokens Core**: Run your own SuperTokens core service
   - Docker: `docker run -p 3567:3567 registry.supertokens.io/supertokens/supertokens-postgresql`
   - Update `SUPERTOKENS_CONNECTION_URI=http://localhost:3567`

2. **Use SuperTokens Managed Service**: Sign up at https://supertokens.com
   - Set `SUPERTOKENS_CONNECTION_URI` to your managed service URL
   - Set `SUPERTOKENS_API_KEY` to your API key
   - Update `API_DOMAIN` to your production domain

## API Response Codes

### Authentication Errors

- **401 Unauthorized**: Missing or invalid session token
- **403 Forbidden**: Valid session but insufficient permissions
- **440 Session Expired**: Session has expired (browser-specific)

### Example Error Response
```json
{
  "detail": "Unauthorized"
}
```

## Testing with Swagger UI

The interactive API documentation at `http://localhost:8000/docs` now requires authentication:

1. Open http://localhost:8000/docs
2. First use the authentication endpoints to sign up or sign in
3. The session cookies will be automatically stored by your browser
4. You can now test the protected lease and schedule endpoints

## Code Integration

### Protecting New Endpoints

To protect a new endpoint with authentication, add the `session` dependency:

```python
from fastapi import APIRouter, Depends
from supertokens_python.recipe.session import SessionContainer
from app.auth import get_current_user

router = APIRouter()

@router.get("/protected-endpoint")
async def protected_endpoint(session: SessionContainer = Depends(get_current_user)):
    user_id = session.get_user_id()
    return {"message": "This is protected", "user_id": user_id}
```

### Optional Authentication

For endpoints that should work with or without authentication:

```python
from typing import Optional
from app.auth import get_optional_user

@router.get("/optional-auth-endpoint")
async def optional_endpoint(session: Optional[SessionContainer] = Depends(get_optional_user)):
    if session:
        user_id = session.get_user_id()
        return {"authenticated": True, "user_id": user_id}
    return {"authenticated": False}
```

### Accessing User Information

```python
# Get user ID
user_id = session.get_user_id()

# Get session handle
session_handle = session.get_session_handle()

# Get access token payload
payload = session.get_access_token_payload()
```

## Frontend Integration

If you're building a frontend application, use the SuperTokens frontend SDK:

### React
```bash
npm install supertokens-auth-react
```

### Vue.js
```bash
npm install supertokens-web-js
```

### Configuration Example (React)
```javascript
import SuperTokens from "supertokens-auth-react";
import EmailPassword from "supertokens-auth-react/recipe/emailpassword";
import Session from "supertokens-auth-react/recipe/session";

SuperTokens.init({
    appInfo: {
        appName: "Lease Accounting API",
        apiDomain: "http://localhost:8000",
        websiteDomain: "http://localhost:3000",
        apiBasePath: "/auth",
        websiteBasePath: "/auth"
    },
    recipeList: [
        EmailPassword.init(),
        Session.init()
    ]
});
```

## Security Best Practices

1. **HTTPS in Production**: Always use HTTPS in production environments
2. **Strong Passwords**: Enforce strong password requirements (add custom validators)
3. **API Keys**: Never commit API keys or secrets to version control
4. **Session Duration**: Configure appropriate session timeout values
5. **CORS**: Update CORS settings to only allow your frontend domain in production

## Troubleshooting

### Issue: 401 Unauthorized on all requests
- Ensure you've signed in and received session cookies
- Check that cookies are being sent with requests (`-b cookies.txt` in curl)
- Verify SuperTokens connection URI is accessible

### Issue: CORS errors
- Check that `WEBSITE_DOMAIN` matches your frontend URL
- Ensure CORS middleware includes SuperTokens headers

### Issue: Session cookies not being set
- Verify `API_DOMAIN` and `WEBSITE_DOMAIN` are correctly configured
- In development, both should be `localhost` (not `127.0.0.1`)
- Check browser developer tools > Application > Cookies

## Additional Resources

- [SuperTokens Documentation](https://supertokens.com/docs)
- [SuperTokens FastAPI Guide](https://supertokens.com/docs/emailpassword/fastapi/guide)
- [Session Management](https://supertokens.com/docs/session/introduction)
