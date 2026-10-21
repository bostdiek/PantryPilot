# Authentication session limits

PantryPilot uses a 30-minute inactivity timeout and a 12-hour absolute session
limit. Both limits are enforced against the `auth_sessions` database row for
every protected request and every renewal; the access-token lifetime remains
short and is configured separately by `ACCESS_TOKEN_EXPIRE_MINUTES`.

Login creates a server-side session and places a refresh credential in an
HttpOnly, SameSite=Lax cookie scoped to `/api/v1/auth`. The credential is
derived with HMAC-SHA256 from the server secret, session ID, and generation;
the database stores only its SHA-256 digest. The cookie is Secure in
production. Each renewal rotates the credential and issues a new short-lived
access token. A 30-second previous-credential grace window lets concurrent
requests and tabs converge on the same current credential; reuse after that
window revokes the session. The session row is locked while renewal and logout
are processed. Logout revokes the session and clears the cookie; a request
racing with logout cannot use its access token after revocation.

Only explicit user input signals activity: pointer or keyboard interaction,
form input/change/submission, wheel or touch scrolling, browser history
navigation, and returning focus to the visible tab. The frontend coalesces
these signals. Background requests, assistant output, and renewals without an
activity signal do not advance `last_activity_at`. An untouched page therefore
expires normally.

When a session ends, the frontend explains that inactivity or the maximum
duration requires sign-in. Before clearing the expired session, it saves
non-password, non-file form controls for at most two hours in that tab's
`sessionStorage`; matching controls are restored after sign-in. Manual logout
does not save form data.
