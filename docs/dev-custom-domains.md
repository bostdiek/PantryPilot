---
title: Dev same-site custom domains
description: Bootstrap dev-only DNS and TLS, preserve bindings, and validate the session candidate before merging.
---

## Purpose and boundaries

Use `https://dev.smartmealplanner.app` for the existing dev Static Web App
(SWA), and `https://api-dev.smartmealplanner.app` for the existing dev Container
App (ACA). Both are HTTPS and same-site, but they are different origins.
Production sibling domains are **not trusted dev origins**. Do not change
production resources, DNS, workflows, cookie domain scope, or SameSite policy.
SWA remains on its existing Free SKU; no linked-backend integration is required.

This is the hosting prerequisite for [#635](https://github.com/bostdiek/PantryPilot/pull/635),
not the session implementation. The session branch is currently deployed to dev.
Do not merge either PR to perform this test.

> [!WARNING]
> A main-based dev deployment replaces the session candidate's frontend and
> may replace its backend with the current mutable `:dev` image. A main push can
> also rebuild that image. Schedule a dev test window, freeze other dev builds,
> deployments and manual domain edits, and record the current frontend commit,
> backend image/digest and revision before starting. Do not assume that `:dev`
> still contains #635.

## Current validation boundary

Local source checks do not establish browser-cookie acceptance. At authoring,
Azure resource reads failed with `AADSTS9002313`. No authentication/account
changes, DNS edits, cloud deployments, or production operations were performed.
No live Azure DNS target or verification token is asserted here. Obtain the
values below from the intended subscription before editing DNS; never derive
them from example resource-name suffixes.

## 1. Read existing dev values

Use an already-authorized Azure identity and the confirmed subscription used by
the GitHub `dev` environment. Do not run `az account set`, switch identities, or
retry authentication with another account. Stop on any authentication failure.
These commands are read-only and use an explicit subscription:

```bash
set -euo pipefail
: "${AZURE_SUBSCRIPTION_ID:?Set the confirmed dev subscription ID}"
export AZURE_SUBSCRIPTION_ID
RG=rg-pantrypilot-dev
API=pantrypilot-backend-dev
az group show --subscription "$AZURE_SUBSCRIPTION_ID" --name "$RG" \
  --query '{name:name,id:id}' -o json

SWA=$(az staticwebapp list --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" \
  --query "[?starts_with(name, 'pantrypilot-frontend-dev-')].name" -o json |
  jq -er 'if length == 1 then .[0] else error("Expected one dev SWA") end')
SWA_TARGET=$(az staticwebapp show --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" --name "$SWA" --query defaultHostname -o tsv)
API_TARGET=$(az containerapp show --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" --name "$API" \
  --query properties.configuration.ingress.fqdn -o tsv)
API_VERIFICATION=$(az containerapp show --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" --name "$API" \
  --query properties.customDomainVerificationId -o tsv)
ACA_ENV_ID=$(az containerapp show --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" --name "$API" --query properties.environmentId -o tsv)
test -n "$SWA_TARGET" && test -n "$API_TARGET"
test -n "$API_VERIFICATION" && test -n "$ACA_ENV_ID"
printf 'dev CNAME -> %s\napi-dev CNAME -> %s\nasuid.api-dev TXT -> %s\n' \
  "$SWA_TARGET" "$API_TARGET" "$API_VERIFICATION"

az containerapp show --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" --name "$API" \
  --query properties.configuration.ingress.customDomains -o json > dev-api-bindings-before.json
az staticwebapp hostname list --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" --name "$SWA" -o json > dev-swa-bindings-before.json
```

Save these non-secret binding inventories outside tracked source. Record the
existing image/revision in a private operational record; do not dump container
secrets or environment variables. Verify SWA and ACA are the intended existing
resources before continuing. The deployment helper also requires their naming
suffixes to agree and fails rather than provision replacement resources.

## 2. DNS and certificate bootstrap, separately approved

Request explicit authorization for the following dev-only DNS and Azure
mutations. Do not run them as part of routine application deployment.

At the DNS provider for `smartmealplanner.app`, add only:

| Type | Relative name | Exact value from step 1 |
|------|---------------|-------------------------|
| CNAME | `dev` | `$SWA_TARGET` |
| CNAME | `api-dev` | `$API_TARGET` |
| TXT | `asuid.api-dev` | `$API_VERIFICATION` |

Use the printed values, not the literal variable names. Leave TTL at the
provider's default. Do not edit the apex, `www`, `api`, or any other production
record. The API CNAME must point **directly** at ACA's generated hostname.
Disable proxying for these records; intermediate/proxied CNAMEs prevent managed
certificate issuance/renewal. Keep the TXT and CNAME records for renewal.
Check existing CAA policy against Azure's current certificate requirements;
stop for approval if a change outside these dev records is needed.

Wait for public DNS propagation, comparing results with step 1:

```bash
dig +short CNAME dev.smartmealplanner.app
dig +short CNAME api-dev.smartmealplanner.app
dig +short TXT asuid.api-dev.smartmealplanner.app
```

After authorization and propagation, bind the existing resources:

```bash
az staticwebapp hostname set --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" --name "$SWA" \
  --hostname dev.smartmealplanner.app --validation-method cname-delegation

az containerapp hostname add --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" --name "$API" --hostname api-dev.smartmealplanner.app
az containerapp hostname bind --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" --name "$API" --hostname api-dev.smartmealplanner.app \
  --environment "$ACA_ENV_ID" --validation-method CNAME
```

SWA issues its certificate after CNAME validation. ACA's bind command finds or
creates a managed certificate after the hostname exists. Do not predeclare an
empty certificate ID or make creation of the app depend on its own certificate.
Keep ACA running/publicly reachable for certificate issuance and renewal; allow
Azure's documented certificate-authority validation traffic.

Wait for SWA hostname status `Ready`, ACA `SniEnabled` with a nonempty
`certificateId`, and the referenced certificate's provisioning state `Succeeded`
in Azure. Confirm HTTPS without `--insecure`:

```bash
az staticwebapp hostname list --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" --name "$SWA" -o table
az containerapp show --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RG" --name "$API" \
  --query properties.configuration.ingress.customDomains -o json
curl --fail --show-error https://dev.smartmealplanner.app/
curl --fail --show-error https://api-dev.smartmealplanner.app/api/v1/health
```

This bootstraps hosting only. The currently deployed bundle can still call the
old API origin, and its cookie tests are not valid yet.

## 3. Enable and deploy the prerequisite

After separate approval to publish this branch/PR and deploy to dev:

1. Review the dev binding inventory, DB backup, current image/digest and test
   window. Do not downgrade or stamp the database to main's older revision.
2. Set GitHub environment `dev` variable `DEV_CUSTOM_DOMAINS_ENABLED=true`.
   Only literal `true` or `false` is accepted. Leave it unset/false until the
   bootstrap checks above pass. This is an externally visible configuration
   change and requires authorization too.
3. Before application deployment, run an authorized Azure what-if using the
   same live snapshot and dev parameters. Review all changes. In particular,
   verify no resource replacement, no certificate deletion, no SWA unrelated
   domain deletion and no production resource. Stop on unexpected differences.
   The existing deployment uses incremental mode; never use complete mode or a
   deployment stack with delete-on-unmanage for these resources.
4. Dispatch **Deploy to Dev** on this prerequisite branch, not main or #635's
   unmodified workflow. It discovers existing names and snapshots all API
   domain/certificate bindings. A failed query, mismatched resource identity,
   missing ready binding, TLS error or failed migration stops the deployment.
5. Migrations run before infrastructure. Only the exact additive migration
   `20261021_21` from #635 commit `246c875137c931af84740a4ea0c7a46379fe9b32`
   is staged from [infra/dev-migrations/](../infra/dev-migrations/) into the
   temporary dev runner when absent. Its SHA-256 is checked first.
   `upgrade head` recognizes the already-applied revision without dropping
   `auth_sessions` or stamping backward. A migration failure remains fatal.
   Production's migration tree and workflow do not use this overlay.
6. Infrastructure round-trips the **entire** live ACA domain-binding array,
   including existing certificate IDs, rather than resetting it to `[]`.
   SWA's dev hostname is declared only after bootstrap; unrelated child bindings
   and environment certificates remain outside this incremental update.
   A post-deploy comparison checks every prior hostname and certificate binding.
7. The dev build uses `VITE_API_URL=https://api-dev.smartmealplanner.app` and
   `VITE_CANONICAL_ORIGIN=https://dev.smartmealplanner.app`. SWA app settings
   alone cannot configure an already-built Vite bundle. The old SWA hostname
   redirects in JavaScript before importing the app and preserves path, query,
   and fragment. JavaScript must be enabled.
8. Custom-hosted dev permits only `https://dev.smartmealplanner.app` in ACA's
   credentialed CORS and backend `CORS_ORIGINS`. It excludes the old SWA origin,
   localhost and all production siblings. Hosted dev uses the existing
   `ENVIRONMENT=production` runtime security mode so #635 emits Secure cookies;
   this does not point dev at production data or change cookie code. CORS is
   served by ACA in this mode. Local development remains unchanged.

Routine deploys repeat the snapshot and preservation checks. Do not edit bindings
manually while a deploy is in progress. Do not deploy the unmodified #635 workflow:
its empty-default binding parameter could undo the bootstrap.

For the what-if in step 3, supply the existing dev secrets through your approved
secret mechanism; never substitute new credentials or print them. The parameter
file reads `DB_ADMIN_PASSWORD`, `SECRET_KEY` and the existing optional service
keys. From the repository root, with the confirmed subscription exported:

```bash
set -euo pipefail
: "${DB_ADMIN_PASSWORD:?Supply the existing dev secret securely}"
: "${SECRET_KEY:?Supply the existing dev secret securely}"
export DB_ADMIN_PASSWORD SECRET_KEY
export DEV_CUSTOM_DOMAINS_ENABLED=true
OUTPUT_FILE=$(mktemp)
SNAPSHOT_FILE=$(mktemp)
GITHUB_OUTPUT="$OUTPUT_FILE" node scripts/dev-hosting.mjs snapshot "$SNAPSHOT_FILE"
export AZURE_UNIQUE_SUFFIX=$(jq -er .suffix "$SNAPSHOT_FILE")
export DEV_BACKEND_CUSTOM_DOMAINS=$(jq -c .customDomains "$SNAPSHOT_FILE")
az deployment group what-if --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group rg-pantrypilot-dev --template-file infra/main.bicep \
  --parameters infra/parameters/main.dev.bicepparam
rm "$OUTPUT_FILE" "$SNAPSHOT_FILE"
```

Compare all preexisting certificate child resources with the inventories as
well as reviewing what-if. Do not interpret absence from a template as proof of
retention without the live check.

## 4. Redeploy #635 without merging either PR

1. Create a separate local validation branch from the latest #635 head and
   integrate this prerequisite branch there only. Do not merge either PR into
   main. Shared workflow/module hunks need deliberate resolution: retain this
   prerequisite's live snapshot, required dev parameters, migration-first graph,
   custom URLs, exact CORS, security mode and binding-preservation checks.
   Retain #635's session implementation. Its equivalent canonical redirect can
   be retained once, not duplicated.
2. Run the combined candidate's tests. The dev migration overlay is skipped
   when #635's real migration already exists. Keep its revision ID unchanged.
3. Obtain approval before publishing the temporary validation branch, building
   or deploying it. Dispatch **Build Container Images** on that branch with
   `environment=dev`. Record the resulting candidate commit and image digest.
   Keep other dev builds frozen because the workflow updates mutable `:dev`.
4. Dispatch **Deploy to Dev** on the same combined branch. Confirm the deployed
   revision/image resolves to the recorded candidate digest, not a later main
   build. Confirm the bundle calls the custom API and no longer the generated
   ACA origin. Complete the browser gate below before accepting #635.
5. Restore the agreed dev candidate after any intervening main deployment.
   Remove the dev-only overlay in a later cleanup once #635's identical migration
   is on main; never remove its database table or deployed Alembic revision.

If rollout fails, stop other deploys and retain DNS/certificates and DB state.
Redeploy the recorded known-good application candidate with this hosting-aware
workflow, using the current full binding snapshot. Do not use database downgrade,
certificate deletion, or an old workflow as rollback. Recover lost bindings
from the saved inventory only after explicit cloud-mutation approval.

## 5. Real-browser acceptance gate

Run on the combined #635 candidate using disposable dev test accounts in a real
browser. Record browser/version, candidate commit/digest, date, and pass/fail for
each item. Do not attach raw refresh values, bearer tokens, password-reset links,
cookie storage exports, or unredacted HAR files.

* [ ] Both custom URLs have valid, trusted TLS with no certificate warnings.
* [ ] Visiting the old SWA URL at `/reset-password?token=example#form` reaches
  the identical route, query and fragment on `dev.smartmealplanner.app`.
* [ ] Network requests use `api-dev.smartmealplanner.app`; credentialed
  preflights allow the exact dev frontend origin and credentials.
* [ ] Sign-in sets `pantrypilot_session_<session-id>` on the **API host only**,
  with HttpOnly, Secure, SameSite=Lax and path `/api/v1/auth`; no `Domain`
  attribute. JavaScript cannot read it. No refresh credential in localStorage.
* [ ] Explicit hourly confirmation renews access and rotates the matching
  session-qualified cookie. Exercise the real prompt/expiry interval; do not
  weaken server policy or pretend a CORS preflight proves renewal.
* [ ] Logout clears the matching cookie with the same scope and records
  server-side revocation. A previously captured session request cannot renew
  or authorize after logout. Check the dev DB's `revoked_at` or equivalent
  server evidence without exporting secrets.
* [ ] In two tabs, delay a session-A refresh response, then log out A and sign in
  as session B. Release A's response. Its session-qualified cookie must not
  overwrite B's cookie, restore A's bearer state or log B out. Reload and verify
  B remains active. Repeat with a delayed A failure and explicit confirmation.
* [ ] Production frontend origins, the API origin used as a frontend origin,
  the old SWA hostname and an arbitrary sibling origin are denied by dev CORS.
  #635's refresh/logout origin guard must also reject untrusted sibling Origin
  headers, even though sibling subdomains are same-site.
* [ ] Before/after domain inventories match (names, binding types and certificate
  IDs); no unrelated SWA binding or environment certificate disappeared.

TLS, DNS, certificate readiness, live what-if, deployment and this browser gate
remain pending until executed. Local automated passes must be reported separately.

## References

* [ACA custom domains and managed certificates](https://learn.microsoft.com/azure/container-apps/custom-domains-managed-certificates?pivots=azure-cli)
* [SWA custom domains with an external DNS provider](https://learn.microsoft.com/azure/static-web-apps/custom-domain-external)
