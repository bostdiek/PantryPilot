---
title: Authentication session limits
description: Bounded session renewal, account isolation, and same-tab input recovery.
---

PantryPilot uses a 30-minute inactivity timeout and a 12-hour absolute session
limit. Both limits are enforced against the `auth_sessions` database row for
every protected request and every renewal; the access-token lifetime remains
short and is configured separately by `ACCESS_TOKEN_EXPIRE_MINUTES`.

Login creates a server-side session and places a refresh credential in an
HttpOnly, SameSite=Lax cookie scoped to `/api/v1/auth`. The credential is
derived with HMAC-SHA256 from the server secret, session ID, and generation;
the database stores only its SHA-256 digest. The cookie is Secure in
production. Renewal rotates the credential and issues a new short-lived
access token. Further renewals during the rotation's 30-second overlap reuse
the current credential rather than rotating again. This lets concurrent
requests and tabs converge on the same current credential; reuse after that
window revokes the session. The session row is locked while renewal and logout
are processed. Logout revokes the session and clears the cookie; a request
racing with logout cannot use its access token after revocation.
Protected requests that appear expired re-read the row under the same lock
before revoking it, so a concurrent successful renewal is not overwritten.
The expiry check releases its lock before the protected endpoint runs.

Renewal must return the same session ID and subject as the initiating access
token. Protected requests retain that identity through renewal and a single
retry, so delayed responses cannot replay a write under a new login.
Cross-tab account changes invalidate stale tabs without importing the new
account into their open forms.

Only explicit user input signals activity: pointer or keyboard interaction,
form input/change/submission, wheel or touch scrolling, browser history
navigation, and returning focus to the visible tab. The frontend coalesces
these signals with a leading report and a single trailing report for input
received within its one-minute throttle window. Pending activity belongs to
the initiating session and is canceled on session changes. No recurring
activity is scheduled on an untouched page. Background requests, assistant
output, and renewals without an activity signal do not advance
`last_activity_at`. An untouched page therefore expires normally.

When a session ends, the frontend explains that inactivity or the maximum
duration requires sign-in. Before clearing the expired session, it saves
non-password, non-file form controls for at most two hours in that tab's
`sessionStorage`; matching controls are restored after the original account
signs in again. Recipe creation and editing save the structured React draft,
including all ingredient and instruction rows, category, and difficulty,
instead of matching controls by position. Deferred native-control restoration
is canceled on route or session changes and checks the current route and
account before writing values. Manual logout does not save form data.
