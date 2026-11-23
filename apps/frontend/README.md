---
title: Frontend development
description: React, TypeScript, Vite, and dependency maintenance for PantryPilot.
---

## React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      ...tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      ...tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      ...tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
]);
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x';
import reactDom from 'eslint-plugin-react-dom';

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
]);
```

## Container builds and CI

The production Docker build compiles frontend assets on Docker's native
`BUILDPLATFORM`, then copies them into the target-platform nginx image.
The static assets are architecture-independent, so building ARM64 images
does not require running TypeScript or Vite under QEMU.

The [CI Build & Test workflow](../../.github/workflows/ci-build.yml) uses one
image job to build both `linux/amd64` and `linux/arm64`. Pull requests validate
the images without logging into GHCR or publishing tags. Main-branch pushes
and manual workflow runs publish the version and `latest` tags.
The image job has a 35-minute limit, with 15 minutes for the frontend build
and 20 minutes for the backend build.

## Testing asynchronous store interactions

Component tests that use the real Zustand store must mock API calls triggered by
user interactions. For example, selecting a conversation reloads its messages;
mock `fetchMessages` even when the test only checks the selected conversation.

Await asynchronous interactions with React Testing Library's async `act` or
`waitFor`, and assert that loading has finished before the test ends. Reset store
state and restore spies between tests. Unfinished requests can log after Vitest
tears down a worker, failing CI even when every assertion passes. Do not suppress
unhandled errors or console output to hide this failure.

## Dependency maintenance

Use the configured npm registry proxy; do not bypass its release quarantine.
From the repository root, check locked package availability before installing:

```bash
node scripts/check_npm_lock_availability.mjs
cd apps/frontend
npm ci
npm run lint
npm run build
npm test -- --run
```

Keep TypeScript on the supported 6.0 release line until
[`typescript-eslint` supports TypeScript 7](https://typescript-eslint.io/users/dependency-versions/).
Do not use `--force` or `--legacy-peer-deps` to hide compiler peer conflicts.
Upgrade `vitest`, `@vitest/ui`, and `@vitest/coverage-v8` together.

After updating the lockfile, preserve the optional `@emnapi/core`,
`@emnapi/runtime`, and `@emnapi/wasi-threads` entries and their dependencies.

Run both `npm audit` and `npm audit --omit=dev` to distinguish tooling findings
from production dependencies. Zod is patched to 4.6.7. The development-tooling
[minimatch advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249) remains:
its fix requires 11.0.1 or later, but current ESLint and typescript-eslint
consumers require version 10. Do not force a major override or suppress the
finding; update when upstream consumers support a patched version.
npm can prune these entries during updates on another platform, causing
`npm ci` to fail in Linux container builds. Restore pruned entries from the
previous lockfile, retain public `registry.npmjs.org` resolved URLs, and
verify a clean `npm ci` before submitting dependency updates.
