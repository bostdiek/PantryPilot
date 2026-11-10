import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { test } from "node:test";
import {
  apiOrigin,
  frontendOrigin,
  prepareSnapshot,
  verifySnapshot,
} from "./dev-hosting.mjs";

const root = new URL("../", import.meta.url);
const read = (path) => readFileSync(new URL(path, root), "utf8");
const environmentId =
  "/subscriptions/test/resourceGroups/rg-pantrypilot-dev/providers/Microsoft.App/managedEnvironments/pantrypilot-env-dev-abc123";
const certificateId = `${environmentId}/managedCertificates/dev-api`;
const sites = [
  {
    name: "pantrypilot-frontend-dev-abc123",
    defaultHostname: "real.azurestaticapps.net",
  },
];
const hostnames = [{ domainName: "dev.smartmealplanner.app", status: "Ready" }];
const backend = {
  fqdn: "real.centralus.azurecontainerapps.io",
  environmentId,
  corsPolicy: { allowedOrigins: [frontendOrigin], allowCredentials: true },
  customDomains: [
    {
      name: "api-dev.smartmealplanner.app",
      bindingType: "SniEnabled",
      certificateId,
    },
    { name: "another.example.com", bindingType: "Disabled" },
  ],
};

test("preserves every binding and certificate ID, including Disabled entries", () => {
  const snapshot = prepareSnapshot(sites, backend, hostnames, "true");
  assert.equal(snapshot.suffix, "abc123");
  assert.equal(snapshot.frontendOrigin, frontendOrigin);
  assert.equal(snapshot.apiOrigin, apiOrigin);
  assert.equal(snapshot.customDomains.length, 2);
  assert.deepEqual(
    snapshot.customDomains.find(
      ({ name }) => name === "api-dev.smartmealplanner.app",
    ),
    backend.customDomains[0],
  );
  verifySnapshot(snapshot, structuredClone(snapshot));
  assert.throws(
    () => verifySnapshot(snapshot, { ...snapshot, customDomains: [] }),
    /bindings changed/,
  );
  assert.throws(
    () =>
      verifySnapshot(snapshot, {
        ...snapshot,
        customDomains: snapshot.customDomains.map((domain) => ({
          ...domain,
          certificateId: "changed",
        })),
      }),
    /bindings changed/,
  );
  assert.throws(
    () => verifySnapshot(snapshot, { ...snapshot, hostnames: [] }),
    /bindings changed/,
  );
});

test("bootstrap-off accepts explicit empty bindings without canonicalizing old hosting", () => {
  const snapshot = prepareSnapshot(
    sites,
    { ...backend, customDomains: [] },
    [],
    "false",
  );
  assert.equal(snapshot.frontendOrigin, "");
  assert.equal(
    snapshot.apiOrigin,
    "https://real.centralus.azurecontainerapps.io",
  );
  assert.deepEqual(snapshot.customDomains, []);
});

test("fails closed for missing metadata, ambiguous resources and malformed bindings", () => {
  for (const domains of [
    undefined,
    null,
    {},
    [{ name: "api-dev.smartmealplanner.app", bindingType: "SniEnabled" }],
    [{ name: "bad\nhostname", bindingType: "Disabled" }],
  ]) {
    assert.throws(() =>
      prepareSnapshot(
        sites,
        { ...backend, customDomains: domains },
        hostnames,
        "false",
      ),
    );
  }
  assert.throws(() => prepareSnapshot([], backend, hostnames, "false"));
  assert.throws(() =>
    prepareSnapshot([...sites, ...sites], backend, hostnames, "false"),
  );
  assert.throws(() =>
    prepareSnapshot(
      sites,
      { ...backend, environmentId: "wrong" },
      hostnames,
      "false",
    ),
  );
  assert.throws(() => prepareSnapshot(sites, backend, hostnames, "TRUE"));
});

test("activation requires the exact API TLS binding and ready frontend domain", () => {
  assert.throws(
    () =>
      prepareSnapshot(
        sites,
        { ...backend, customDomains: [] },
        hostnames,
        "true",
      ),
    /Bootstrap the API/,
  );
  assert.throws(
    () => prepareSnapshot(sites, backend, [], "true"),
    /Bootstrap the SWA/,
  );
  assert.throws(() =>
    prepareSnapshot(
      sites,
      backend,
      [{ ...hostnames[0], status: "Validating" }],
      "true",
    ),
  );
  assert.throws(() =>
    prepareSnapshot(
      sites,
      backend,
      [{ domainName: "smartmealplanner.app", status: "Ready" }],
      "true",
    ),
  );
});

test("post-deploy credentialed CORS rejects production and arbitrary sibling origins", () => {
  const before = prepareSnapshot(sites, backend, hostnames, "true");
  for (const origin of [
    "https://smartmealplanner.app",
    "https://api-dev.smartmealplanner.app",
    "https://other.smartmealplanner.app",
    "*",
    "http://localhost:5173",
  ]) {
    assert.throws(
      () =>
        verifySnapshot(before, {
          ...before,
          corsPolicy: {
            allowedOrigins: [frontendOrigin, origin],
            allowCredentials: true,
          },
        }),
      /Unexpected credentialed dev CORS/,
    );
  }
  assert.throws(
    () =>
      verifySnapshot(before, {
        ...before,
        corsPolicy: {
          allowedOrigins: [frontendOrigin],
          allowCredentials: false,
        },
      }),
    /Credentialed CORS/,
  );
});

test("missing Azure CLI fails instead of producing an empty successful snapshot", () => {
  const result = spawnSync(
    process.execPath,
    [
      new URL("./dev-hosting.mjs", import.meta.url).pathname,
      "snapshot",
      "/unused-snapshot.json",
    ],
    { env: { PATH: "", AZURE_SUBSCRIPTION_ID: "test" }, encoding: "utf8" },
  );
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Dev hosting preflight failed/);
});

test("hosting deployment uses only the chosen ref's migrations and preserves the rollback", () => {
  const dev = read(".github/workflows/deploy-dev.yml");
  assert.match(dev, /needs: \[inspect-dev-hosting, run-migrations\]/);
  assert.match(dev, /needs: inspect-dev-hosting/);
  assert.match(
    dev,
    /DEV_BACKEND_CUSTOM_DOMAINS: \$\{\{ steps.hosting.outputs.backend-domains \}\}/,
  );
  assert.doesNotMatch(
    dev,
    /needs\.inspect-dev-hosting\.outputs\.(backend-domains|snapshot)/,
  );
  assert.match(dev, /uv run alembic -c src\/alembic.ini upgrade head/);
  assert.doesNotMatch(dev, /dev-migrations|SOURCE=|TARGET=|sha256sum/);
  assert.doesNotMatch(dev, /alembic[^\n]*(?:downgrade|stamp)/);
  assert.match(dev, /SELECT version_num FROM alembic_version/);
  assert.match(dev, /SELECT to_regclass\('public.auth_sessions'\) IS NULL/);
  assert.match(
    dev,
    /ScriptDirectory.from_config\(Config\("src\/alembic.ini"\)\)/,
  );
  assert.match(dev, /validate_dev_migration_state\(scripts, revisions,/);
  assert.doesNotMatch(dev, /hashFiles\(/);
  const guard = read("apps/backend/src/core/migration_preflight.py");
  assert.match(guard, /set\(scripts.get_heads\(\)\) == \{"20260928_20"\}/);
  assert.match(guard, /scripts.walk_revisions\(\)/);
  assert.doesNotMatch(
    read(".github/workflows/deploy-prod.yml"),
    /dev-migrations/,
  );
});

test("dev parameters require a live snapshot and build wires both custom origins", () => {
  const params = read("infra/parameters/main.dev.bicepparam");
  assert.match(
    params,
    /json\(readEnvironmentVariable\('DEV_BACKEND_CUSTOM_DOMAINS'\)\)/,
  );
  assert.match(params, /readEnvironmentVariable\('AZURE_UNIQUE_SUFFIX'\)/);
  const dev = read(".github/workflows/deploy-dev.yml");
  assert.match(
    dev,
    /VITE_API_URL: \$\{\{ needs.inspect-dev-hosting.outputs.api-origin \}\}/,
  );
  assert.match(
    dev,
    /VITE_CANONICAL_ORIGIN: \$\{\{ needs.inspect-dev-hosting.outputs.frontend-origin \}\}/,
  );
  const main = read("infra/main.bicep");
  assert.match(
    main,
    /var corsOrigins = environmentName == 'dev' && isDevCustomHostingEnabled \? \[\s*'https:\/\/dev.smartmealplanner.app'\s*\]/,
  );
  assert.match(main, /environmentName == 'dev' && isDevCustomHostingEnabled/);
  assert.match(main, /param backendCustomDomains array\?\s/);
  assert.doesNotMatch(
    read("infra/parameters/main.prod.bicepparam"),
    /isDevCustomHostingEnabled|backendCustomDomains/,
  );
});
