# Manual Testing Guide: Authentication Session Handling

This guide documents how to manually test the improved session handling for expired/invalid access tokens.

## Test Scenarios

### Scenario 1: Token Expiration with Short-Lived Tokens

1. **Setup**: Set a very short token expiry in the backend configuration
   ```bash
   # In apps/backend/.env or environment config
   ACCESS_TOKEN_EXPIRE_MINUTES=1  # 1 minute for testing
   ```

2. **Test Steps**:
   - Start the application: `make dev`
   - Log in through the frontend UI
   - Wait for the token to expire (>1 minute)
   - Try to perform an API action (navigate to recipes, create a recipe, etc.)

3. **Expected Behavior**:
   - User is automatically logged out
   - Toast message appears: "Your session has expired. Please log in again."
   - User is redirected to login page
   - No error banners appear on authenticated pages
   - Previous location is preserved for redirect after re-login

### Scenario 2: Invalid Token via Backend Response Simulation

1. **Test Steps**:
   - Log in to the application
   - Use browser dev tools to modify the stored auth token to an invalid value
   - Navigate to any protected page or try an API action

2. **Expected Behavior**:
   - Same as Scenario 1: automatic logout, toast message, redirect to login

### Scenario 3: Network Errors vs Authentication Errors

1. **Test Steps**:
   - Log in to the application
   - Simulate a 500 server error (can be done by temporarily breaking backend)
   - Simulate a 401 authentication error

2. **Expected Behavior**:
   - 500 errors: Show error message but user remains logged in
   - 401 errors: Automatic logout with session expired message

## Verification Checklist

- [ ] 401 HTTP status triggers immediate logout
- [ ] Backend "Could not validate credentials" message with 401 triggers logout  
- [ ] Canonical error type "unauthorized" triggers logout
- [ ] User sees friendly toast: "Your session has expired. Please log in again."
- [ ] User is redirected to login page automatically
- [ ] Previous location is preserved in URL (`?next=/previous-route`)
- [ ] No error banners appear on authenticated pages after logout
- [ ] Non-401 errors (400, 500, etc.) do not trigger logout
- [ ] Manual logout still works normally (from user menu)
- [ ] After re-login, user is redirected to their previous location

## Backend Error Response Format

The backend now returns structured error responses for 401 cases:

```json
{
  "success": false,
  "message": "An HTTP error occurred", 
  "error": {
    "type": "unauthorized",
    "correlation_id": "uuid-123"
  }
}
```

## Testing with Browser Dev Tools

1. **View Auth State**:
   ```javascript
   // In browser console
   JSON.parse(localStorage.getItem('auth'))
   ```

2. **Trigger 401 Response**:
   ```javascript
   // Corrupt the token to trigger 401
   const auth = JSON.parse(localStorage.getItem('auth'))
   auth.token = 'invalid-token'
   localStorage.setItem('auth', JSON.stringify(auth))
   // Then try any API action
   ```

3. **Monitor API Calls**:
   - Open Network tab in dev tools
   - Look for 401 responses
   - Verify logout behavior occurs immediately

## Notes

- The `ProtectedRoute` component automatically redirects when authentication state changes
- Toast notifications appear for ~4.3 seconds
- All auth state is cleared from localStorage on logout
- The solution maintains backward compatibility with existing error handling