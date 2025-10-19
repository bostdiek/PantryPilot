import js from '@eslint/js';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';

// Provide a minimal structuredClone polyfill for environments where it's missing (e.g. some Node runtimes).
// This affects only the ESLint process and does not impact application/runtime code.
if (typeof globalThis.structuredClone !== 'function') {
  globalThis.structuredClone = (obj) => JSON.parse(JSON.stringify(obj));
}

// Flat ESLint config using @typescript-eslint recommendedTypeChecked configs
export default [
  {
    ignores: ['dist', 'coverage'],
  },
  js.configs.recommended,
  // include type-checked recommended configs if available
  ...(tsPlugin.configs && tsPlugin.configs.recommendedTypeChecked
    ? [tsPlugin.configs.recommendedTypeChecked]
    : []),
  ...(tsPlugin.configs && tsPlugin.configs.strictTypeChecked
    ? [tsPlugin.configs.strictTypeChecked]
    : []),
  ...(tsPlugin.configs && tsPlugin.configs.stylisticTypeChecked
    ? [tsPlugin.configs.stylisticTypeChecked]
    : []),
  {
    files: ['**/*.{ts,tsx}'],
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
      },
      // Include both browser and node globals to support test files and
      // runtime checks that reference `process` or `global` during test runs.
      globals: { ...globals.browser, ...globals.node },
    },
  },

  // Test-specific globals: vitest/jest style names (describe, it, expect, vi, etc.)
  {
    files: ['**/__tests__/**/*.{ts,tsx}', '**/*.{test,spec}.{ts,tsx}'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.jest,
        vi: 'readonly',
      },
    },
  },
  // Enable projectService for type-checked rules and relax unused-vars to warnings
  {
    // Ensure the plugin is available in this config object when applying rules
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    languageOptions: {
      parserOptions: {
        tsconfigRootDir: import.meta.dirname,
        // Include both general and test-specific tsconfigs so test files are part of the program
        project: ['./tsconfig.eslint.json', './tsconfig.test.json'],
      },
    },
    ignores: [
      '**/__tests__/**',
      '**/*.test.ts',
      '**/*.test.tsx',
      '**/*.spec.ts',
      '**/*.spec.tsx',
    ],
    rules: {
      // disable core rule and let typescript-eslint handle it
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          varsIgnorePattern: '^_',
          argsIgnorePattern: '^_',
          ignoreRestSiblings: true,
        },
      ],
    },
  },
  // Override for test files: avoid project-based parsing errors by disabling project lookup
  {
    files: ['**/__tests__/**/*.{ts,tsx}', '**/*.{test,spec}.{ts,tsx}'],
    languageOptions: {
      parserOptions: {
        tsconfigRootDir: import.meta.dirname,
        // Omit project to parse with isolated file mode for tests
      },
    },
    rules: {
      // Disable unused vars entirely for tests (helpers and inline mock params often unused)
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': 'off',
    },
  },
  reactHooks.configs['recommended-latest'],
  reactRefresh.configs.vite,
];
