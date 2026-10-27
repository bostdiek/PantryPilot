---
title: Authentication session limits
description: Explicit one-hour consent, isolated refresh cookies, and production same-site setup.
---

## Session policy

Signing in authorizes a one-hour session window. Five minutes before its end,
PantryPilot displays a warning. Only choosing **Stay signed in** authorizes
another hour, measured from that confirmation, and never beyond the 12-hour
absolute limit. Ignoring the prompt expires the session. At the absolute limit,
you must sign in again.

Choose **Not now** or press Escape to dismiss the warning and keep working
within the remaining authorized time, including at the absolute cap. Dismissal
does not renew credentials or extend the deadline. The same warning stays
dismissed until the session identity or authorized deadline changes; expiration
and recovery still run at the original deadline.

Access tokens default to 15 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`). Transparent
renewal and background requests may rotate credentials within the authorized
window, but do not extend it. Typing, scrolling, navigation, assistant output,
and returning focus do not extend consent. The browser rechecks its clock on
focus and visibility changes; the server remains authoritative after sleep
or timer throttling.

Both window and absolute limits are enforced against the `auth_sessions` row
for protected requests and renewal. The existing `last_activity_at` column now
means the last explicit confirmation time, initially the sign-in time. The first
session rollout requires Alembic revision `20261021_21`, which creates
`auth_sessions`; explicit confirmation reuses that schema and adds no further
migration. Signed `session_exp` and `absolute_exp` claims give
the frontend deadline hints; they do not replace server validation.

## Credential and account isolation

Login creates an HttpOnly, SameSite=Lax cookie named
`pantrypilot_session_<session UUID>`, scoped to `/api/v1/auth`. Cookies are
Secure in production. Refresh and logout require `X-Session-ID` to select that
session's cookie; the header is not a credential and cannot replace the cookie.
Missing or malformed selectors are rejected, never inferred from another cookie.

The refresh secret is derived using HMAC-SHA256 from the server secret, session
ID, and generation. Only its SHA-256 digest is stored in the database.
Rotation's 30-second overlap lets concurrent requests converge on the current
credential. Reusing an older credential after overlap revokes the session.
Cookies expire within the 12-hour absolute limit.

Session-qualified names ensure a delayed response from session A cannot replace
or delete session B's credential after a newer login, including a login in
another tab. Renewal must also return the initiating session and subject.
Protected requests retain that identity through renewal and a single retry, so
delayed responses cannot replay a write under a new login.

An explicit confirmation gates protected requests immediately, even when it is
queued behind silent renewal. Both HTTP transports wait for the entire
confirmation chain; repeated confirmations share it. A different session does
not wait for or install the old session's response.

Network failures and non-authentication refresh errors (such as HTTP 503)
surface a retryable request error without clearing the session. Rejected
credentials (HTTP 401/403) and a known expired consent deadline remain terminal.
A raw-fetch authentication retry waits for queued confirmation again and uses
the latest installed token, just like the API client.

Other tabs accept a later consent deadline for the same session without
importing a different account into open forms. An older deadline cannot undo a
newer confirmation. Cross-account changes invalidate stale tabs.

Renewal, logout, and final expiry decisions use row locks. Logout revokes the
selected session and clears only its cookie; racing requests cannot use that
session's access token after revocation. Suspected expiry re-reads locked state
before revoking it, preserving a concurrent successful confirmation.

Successful password reset revokes every active session for that account in the
same transaction as the password change. Pre-reset refresh cookies and
session-bound access tokens are rejected afterward; other accounts are
unaffected. Rejected resets or rolled-back password updates do not revoke
sessions. Login and password reset lock and reload the same account row, holding
that lock through credential verification/session creation or password
change/revocation. A concurrent login cannot use a stale pre-reset password to
create a session after the reset commits.
Legacy access tokens without a session identifier remain subject to
their original short expiration.

## Same-tab recovery

When a session expires, recoverable non-password, non-file controls are saved
in that tab's `sessionStorage` for at most two hours. Matching controls restore
after the original account signs in again.

Recipe creation and editing preserve the structured draft, including ingredient
and instruction rows, category, and difficulty. Creation and edit recovery wait for the
profile's account ID before considering the draft. Another account cannot
restore it. Deferred native-control restoration is canceled on route or
session changes and checks current route and account before writing values.
Unsaved profile/preferences and Nibble-memory editors are captured as structured
state and reopen in edit mode. Pending instruction-import dialogs preserve edited
rows, removals, original pasted text and their insertion target; the parent recipe
draft is recovered alongside them. Delayed profile and memory loads cannot
overwrite recovered edits.

Manual logout does not save form data, including in other tabs: the persisted
logout reason distinguishes explicit sign-out from expiry. Actual expiry still
captures each tab's recoverable input without writing stale authentication state
back over the originating tab.

## Production same-site setup on the Free plan

The production frontend uses `https://smartmealplanner.app` and calls
`https://api.smartmealplanner.app`. Both are HTTPS sites under the same
registrable domain, so SameSite=Lax cookies work without relying on third-party
cookie support. Requests still cross origins, so exact-origin CORS with
credentials remains required.

The production build sets `VITE_API_URL` to the custom API URL and
`VITE_CANONICAL_ORIGIN` to the canonical frontend origin. Opening the default
Static Web Apps hostname (or `www`) redirects to the canonical origin,
preserving the path, query, and fragment. Development builds leave the canonical
origin unset. Authentication state is origin-scoped, so the first visit after
switching origins may require sign-in again.

This keeps Static Web Apps on its existing Free plan. Container Apps supports a
free managed certificate; there is no intended additional fixed hosting charge
for adding this subdomain. Existing Container Apps, DNS-provider, domain
registration, traffic, and database charges still apply.

Before deploying this change:

1. In the existing production Container App, obtain its default ingress FQDN
   and custom-domain verification ID. Do not expose credentials.
2. At your DNS provider, add a CNAME for `api.smartmealplanner.app` pointing to
   that Container App's default ingress FQDN. Add the `asuid.api` TXT
   verification record using the value Azure supplies.
3. Add `api.smartmealplanner.app` to the Container App's custom domains.
   Request and bind the free managed certificate with SNI enabled. Keep the
   DNS validation records required for automatic renewal.
4. Confirm `https://api.smartmealplanner.app/api/v1/health` returns HTTP 200
   with a valid public TLS certificate. Keep both canonical frontend origins
   in the backend's allowed-origin list; do not enable wildcard credentials.
5. Confirm the existing production Key Vault contains the current
   `dbConnectionString` secret. Its name follows
   `ppkv${DEPLOY_ENV}${AZURE_UNIQUE_SUFFIX}` (currently `ppkvprodprod001`).
   If database credentials have been rotated, update this secret before
   starting the workflow; it must be usable before any infrastructure update.
6. Run the production workflow. It applies Alembic migrations against that
   existing database before deploying any infrastructure or backend revision.
   Failed, canceled or skipped migrations prevent infrastructure, backend and
   frontend publication. The workflow requires the bound domain, preserves
   existing custom-domain/certificate bindings, and checks custom-domain HTTPS
   health before publishing the frontend.

The workflow intentionally stops if the required binding is absent. It does
not fall back to the cross-site Container Apps hostname or provision DNS.
For a first-ever environment deployment, bootstrap the database, Key Vault
secret, Container App and domain binding before enabling this production
publication gate. The production parameter file also
accepts `BACKEND_CUSTOM_DOMAINS` as the JSON ingress binding array for manual
Bicep deployments; supply existing bindings to avoid removing them.

See Microsoft's [custom domain and free managed certificate guide](https://learn.microsoft.com/azure/container-apps/custom-domains-managed-certificates).
The alternative [linked Static Web Apps backend](https://learn.microsoft.com/azure/static-web-apps/apis-container-apps)
requires the paid Standard plan and is not enabled here.

## Development deployment

The development workflow also applies migrations before any infrastructure or
backend update. It reads the existing `dbConnectionString` from
`ppkvdevdev001`; missing credentials or failed migrations block publication.
Bootstrap new environments before using this workflow.

To deploy a PR branch without merging, manually run **Build Container Images**
on that branch with environment `dev`. After it succeeds, manually run
**Deploy to Dev** on the same branch. This replaces the shared dev deployment,
not production. Check that no other build overwrites the mutable `dev` image
tag between those runs. A failed backend health check blocks frontend
publication.

The default dev frontend and API hostnames are cross-site. This deployment
does not certify SameSite=Lax refresh-cookie behavior; that acceptance requires
the same-site domains described above.

## Coordinated rollback

Keep the additive `auth_sessions` table when rolling back application code.
Do not downgrade its migration while any deployed backend revision still
depends on it. Roll back compatible backend and frontend versions together;
preserve the same-site domain and TLS bindings. A rollback to older session
code can invalidate current cookies and require a new sign-in.

Before rollout, verify the migration on a staging PostgreSQL database, including
refresh versus reset/expiry races. If migration fails, correct it before retrying
publication; do not bypass the dependency gate. Database health alone does not
prove the required schema exists.

## Production browser acceptance

Local tests cannot certify DNS, TLS, and production browser cookie behavior.
After configuring and deploying the same-site domains:

1. Use the canonical frontend in a browser that blocks third-party cookies.
   Sign in and inspect that the API response sets a session-qualified HttpOnly,
   Secure, SameSite=Lax cookie.
2. Confirm refresh POSTs include that cookie and `X-Session-ID`, and that an
   ordinary renewal does not move `session_exp`.
3. At the five-minute warning, confirm that **Stay signed in** extends the
   effective deadline by an hour, bounded by the original absolute limit.
   Check another tab updates without switching account identity.
   Also test Escape and **Not now**: the warning closes without extending time
   or reopening on a timer tick, and still expires at the deadline.
4. Ignore a later warning or sleep past the deadline. Confirm expiration and
   matching-account draft recovery after sign-in.
5. Sign out and confirm server revocation, not merely a local route change.
   Confirm the same cookie is deleted and subsequent use is unauthorized.
6. Delay session A's refresh response while signing into B in another tab.
   Deliver A's response and confirm B can still refresh and sign out.
7. Reset the password with sessions open in multiple tabs or browsers. Confirm
   all pre-reset sessions lose protected access and cannot renew, while a new
   sign-in with the replacement password succeeds.
