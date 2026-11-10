import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { test } from "node:test";
import {
  apiOrigin,
  frontendOrigin,
  prepareSnapshot,
  runHostingCommand,
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
  assert.match(result.stderr, /Dev hosting check failed/);
});

test("binding snapshots allow recovery while final HTTPS checks reject failures", async (t) => {
  const directory = mkdtempSync(join(tmpdir(), "dev-hosting-test-"));
  const previousOutput = process.env.GITHUB_OUTPUT;
  const previousEnabled = process.env.DEV_CUSTOM_DOMAINS_ENABLED;
  const snapshot = prepareSnapshot(sites, backend, hostnames, "true");
  let apiStatus = 503;
  let tlsError = false;
  const fetchMock = t.mock.method(globalThis, "fetch", async (url) => {
    if (tlsError) throw new Error("TLS validation failed");
    return new Response(null, {
      status: url === frontendOrigin ? 200 : apiStatus,
    });
  });

  try {
    process.env.GITHUB_OUTPUT = join(directory, "outputs");
    process.env.DEV_CUSTOM_DOMAINS_ENABLED = "true";
    const snapshotPath = join(directory, "snapshot.json");
    const discoverHosting = () => snapshot;

    await runHostingCommand("snapshot", snapshotPath, discoverHosting);
    await runHostingCommand("verify", snapshotPath, discoverHosting);
    assert.equal(fetchMock.mock.callCount(), 0);

    await assert.rejects(
      runHostingCommand("health"),
      /TLS\/HTTP readiness failed/,
    );
    apiStatus = 200;
    await runHostingCommand("health");
    tlsError = true;
    await assert.rejects(runHostingCommand("health"), /TLS validation failed/);
    const calls = fetchMock.mock.callCount();
    process.env.DEV_CUSTOM_DOMAINS_ENABLED = "false";
    await runHostingCommand("health");
    assert.equal(fetchMock.mock.callCount(), calls);
    process.env.DEV_CUSTOM_DOMAINS_ENABLED = "invalid";
    await assert.rejects(
      runHostingCommand("health"),
      /Activation must be true or false/,
    );
  } finally {
    if (previousOutput === undefined) delete process.env.GITHUB_OUTPUT;
    else process.env.GITHUB_OUTPUT = previousOutput;
    if (previousEnabled === undefined)
      delete process.env.DEV_CUSTOM_DOMAINS_ENABLED;
    else process.env.DEV_CUSTOM_DOMAINS_ENABLED = previousEnabled;
    rmSync(directory, { recursive: true, force: true });
  }
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
  assert.ok(
    dev.indexOf("node scripts/dev-hosting.mjs health") >
      dev.indexOf("uses: Azure/static-web-apps-deploy@v1"),
    "HTTPS readiness must be checked after deploying the frontend",
  );
});
