import js from '@eslint/js';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';

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
      globals: globals.browser,
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
        project: ['./tsconfig.eslint.json'],
      },
    },
    rules: {
      // disable core rule and let typescript-eslint handle it
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          varsIgnorePattern: '^_',
          argsIgnorePattern: '^_',
          ignoreRestSiblings: true,
        },
      ],
    },
  },
  reactHooks.configs['recommended-latest'],
  reactRefresh.configs.vite,
];
