import { execFileSync } from "node:child_process";
import { appendFileSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";

export const frontendOrigin = "https://dev.smartmealplanner.app";
export const apiOrigin = "https://api-dev.smartmealplanner.app";
const resourceGroup = "rg-pantrypilot-dev";
const backendName = "pantrypilot-backend-dev";

function azure(...args) {
  assert.ok(
    process.env.AZURE_SUBSCRIPTION_ID,
    "AZURE_SUBSCRIPTION_ID is required",
  );
  return JSON.parse(
    execFileSync(
      "az",
      [
        ...args,
        "--subscription",
        process.env.AZURE_SUBSCRIPTION_ID,
        "--output",
        "json",
        "--only-show-errors",
      ],
      {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "inherit"],
      },
    ),
  );
}

function bindings(domains) {
  assert.ok(
    Array.isArray(domains),
    "Expected an explicit ingress domain array",
  );
  const result = domains.map(({ name, bindingType, certificateId }) => {
    assert.match(name, /^[a-z0-9.-]+$/i, "Invalid binding hostname");
    assert.ok(
      ["Disabled", "SniEnabled", "Auto"].includes(bindingType),
      "Unknown binding type",
    );
    if (bindingType !== "Disabled") {
      assert.match(
        certificateId,
        /^\/subscriptions\/[^/\s]+\/resourceGroups\/[^/\s]+\/providers\/Microsoft\.App\/managedEnvironments\/[^/\s]+\/(?:managedCertificates|certificates)\/[^/\s]+$/i,
      );
    }
    return {
      name,
      bindingType,
      ...(certificateId ? { certificateId } : {}),
    };
  });
  assert.equal(new Set(result.map(({ name }) => name)).size, result.length);
  return result.sort((a, b) => a.name.localeCompare(b.name));
}

// Only projections without container configuration or secrets enter this snapshot.
export function prepareSnapshot(sites, backend, hostnames, enabled) {
  assert.ok(
    ["true", "false"].includes(enabled),
    "Activation must be true or false",
  );
  const matches = sites.filter(({ name }) =>
    name.startsWith("pantrypilot-frontend-dev-"),
  );
  assert.equal(
    matches.length,
    1,
    "Expected exactly one existing dev Static Web App",
  );
  const site = matches[0];
  const suffix = site.name.slice("pantrypilot-frontend-dev-".length);
  assert.match(suffix, /^[a-z0-9]+$/);
  assert.ok(
    backend.environmentId
      .toLowerCase()
      .endsWith(`/pantrypilot-env-dev-${suffix}`),
    "SWA and backend resource suffixes disagree",
  );
  assert.match(site.defaultHostname, /^[a-z0-9.-]+\.azurestaticapps\.net$/);
  assert.match(backend.fqdn, /^[a-z0-9.-]+\.azurecontainerapps\.io$/);
  assert.ok(Array.isArray(hostnames), "Expected SWA hostname metadata");
  const customDomains = bindings(backend.customDomains);
  if (enabled === "true") {
    assert.ok(
      customDomains.some(
        ({ name, bindingType, certificateId }) =>
          name === new URL(apiOrigin).hostname &&
          bindingType === "SniEnabled" &&
          certificateId,
      ),
      "Bootstrap the API hostname and managed certificate before activation",
    );
    assert.ok(
      hostnames.some(
        ({ domainName, status }) =>
          domainName === new URL(frontendOrigin).hostname && status === "Ready",
      ),
      "Bootstrap the SWA hostname and wait for Ready before activation",
    );
  }
  return {
    suffix,
    siteName: site.name,
    defaultHostname: site.defaultHostname,
    environmentId: backend.environmentId,
    customDomains,
    corsPolicy: backend.corsPolicy,
    hostnames: hostnames.map(({ domainName }) => domainName).sort(),
    enabled,
    frontendOrigin: enabled === "true" ? frontendOrigin : "",
    apiOrigin: enabled === "true" ? apiOrigin : `https://${backend.fqdn}`,
  };
}

export function verifySnapshot(before, after) {
  assert.equal(after.siteName, before.siteName, "SWA identity changed");
  assert.equal(
    after.environmentId,
    before.environmentId,
    "ACA environment changed",
  );
  assert.deepEqual(
    after.customDomains,
    before.customDomains,
    "API TLS bindings changed",
  );
  assert.deepEqual(
    after.hostnames,
    before.hostnames,
    "SWA domain bindings changed",
  );
  if (after.enabled === "true") {
    assert.deepEqual(
      after.corsPolicy.allowedOrigins,
      [frontendOrigin],
      "Unexpected credentialed dev CORS origins",
    );
    assert.equal(
      after.corsPolicy.allowCredentials,
      true,
      "Credentialed CORS must remain enabled",
    );
  }
}

function discover(enabled) {
  const sites = azure(
    "staticwebapp",
    "list",
    "--resource-group",
    resourceGroup,
    "--query",
    "[].{name:name,defaultHostname:defaultHostname}",
  );
  const names = sites.filter(({ name }) =>
    name.startsWith("pantrypilot-frontend-dev-"),
  );
  assert.equal(
    names.length,
    1,
    "Expected exactly one existing dev Static Web App",
  );
  const hostnames = azure(
    "staticwebapp",
    "hostname",
    "list",
    "--resource-group",
    resourceGroup,
    "--name",
    names[0].name,
  );
  const backend = azure(
    "containerapp",
    "show",
    "--resource-group",
    resourceGroup,
    "--name",
    backendName,
    "--query",
    "{environmentId:properties.environmentId,fqdn:properties.configuration.ingress.fqdn,customDomains:properties.configuration.ingress.customDomains,corsPolicy:properties.configuration.ingress.corsPolicy}",
  );
  // Azure represents no custom domains as null, but a missing ingress/FQDN is an error.
  if (backend.fqdn && backend.customDomains === null)
    backend.customDomains = [];
  return prepareSnapshot(sites, backend, hostnames, enabled);
}

async function checkHttps(snapshot) {
  if (snapshot.enabled !== "true") return;
  for (const url of [frontendOrigin, `${apiOrigin}/api/v1/health`]) {
    const response = await fetch(url, {
      signal: AbortSignal.timeout(30000),
      redirect: "error",
    });
    assert.equal(response.status, 200, `TLS/HTTP readiness failed for ${url}`);
    await response.body?.cancel();
  }
}

async function main() {
  const [command, snapshotPath] = process.argv.slice(2);
  assert.ok(
    snapshotPath,
    "Usage: node scripts/dev-hosting.mjs snapshot|verify PATH",
  );
  if (command === "snapshot") {
    const snapshot = discover(
      process.env.DEV_CUSTOM_DOMAINS_ENABLED || "false",
    );
    await checkHttps(snapshot);
    writeFileSync(snapshotPath, `${JSON.stringify(snapshot)}\n`);
    const outputs = {
      suffix: snapshot.suffix,
      "backend-domains": JSON.stringify(snapshot.customDomains),
      enabled: snapshot.enabled,
      "frontend-origin": snapshot.frontendOrigin,
      "api-origin": snapshot.apiOrigin,
    };
    assert.ok(process.env.GITHUB_OUTPUT, "GITHUB_OUTPUT is required");
    appendFileSync(
      process.env.GITHUB_OUTPUT,
      Object.entries(outputs)
        .map(([key, value]) => `${key}=${value}\n`)
        .join(""),
    );
    console.log(
      `Dev hosting snapshot verified; custom domains enabled: ${snapshot.enabled}`,
    );
  } else {
    assert.equal(command, "verify", "Unknown dev hosting command");
    const before = JSON.parse(readFileSync(snapshotPath, "utf8"));
    const after = discover(before.enabled);
    verifySnapshot(before, after);
    await checkHttps(after);
    console.log("All dev hostname and certificate bindings preserved.");
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(`Dev hosting preflight failed: ${error.message}`);
    process.exitCode = 1;
  });
}
