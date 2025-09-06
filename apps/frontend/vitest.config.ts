import { webcrypto as nodeWebcrypto } from 'node:crypto';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import svgr from 'vite-plugin-svgr';

// Provide Web Crypto globally before Vite/Vitest server bootstraps.
// Vitest executes this config in Node, so setting it here ensures availability
// during early Vite initialization where crypto.getRandomValues() is used.
if (
  typeof (globalThis as any).crypto === 'undefined' ||
  typeof (globalThis as any).crypto?.getRandomValues !== 'function'
) {
  (globalThis as any).crypto = nodeWebcrypto as any;
}

// Dynamically import vitest config AFTER polyfill so Vite sees global crypto
const { mergeConfig, defineConfig } = await import('vitest/config');

// Ensure Vitest uses the same plugin pipeline (especially @vitejs/plugin-react)
// as the main Vite config so JSX is transformed with the automatic runtime.
// We explicitly recreate the minimal plugin list here because calling the
// exported vite config factory with a fake mode object can be brittle across upgrades.

const sharedPlugins = [svgr(), react(), tailwindcss()];

export default mergeConfig(
  // Base Vite build/test options (without invoking dynamic mode logic)
  defineConfig({
    plugins: sharedPlugins,
  }),
  defineConfig({
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts', './src/setupTests.ts'],
      include: ['**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
      exclude: ['**/e2e/**', '**/node_modules/**'],
      css: true,
      coverage: {
        provider: 'v8',
        reporter: ['text', 'json', 'html', 'lcov'],
        exclude: [
          'node_modules/',
          'src/test/',
          '**/*.d.ts',
          '**/*.config.*',
          'dist/',
        ],
      },
    },
  })
);
