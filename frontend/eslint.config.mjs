import { defineConfig, globalIgnores } from 'eslint/config';
import js from '@eslint/js';
import nextCoreWebVitals from 'eslint-config-next/core-web-vitals';
import nextTypescript from 'eslint-config-next/typescript';
import reactHooks from 'eslint-plugin-react-hooks';
import sonarjs from 'eslint-plugin-sonarjs';
import prettier from 'eslint-config-prettier/flat';

// SonarJS `recommended` ships AWS / cloud-infrastructure security rules that aren't used in codebase
const sonarjsAwsRulesOff = Object.fromEntries(
  Object.keys(sonarjs.configs.recommended.rules)
    .filter((rule) => rule.startsWith('sonarjs/aws-'))
    .map((rule) => [rule, 'off'])
);

const eslintConfig = defineConfig([
  js.configs.recommended,
  ...nextCoreWebVitals,
  ...nextTypescript,
  sonarjs.configs.recommended,
  // Project rule overrides
  {
    files: ['**/*.{js,jsx,ts,tsx,mjs,cjs}'],
    rules: {
      '@typescript-eslint/explicit-function-return-type': 'off',
      // Allow args prefixed with `_`
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          args: 'after-used',
          argsIgnorePattern: '^_',
          ignoreRestSiblings: false,
          vars: 'all',
        },
      ],
      // keep next's defaults rather than re-declaring.
      'react/jsx-no-target-blank': 'off',
      'react/prop-types': 'off',
      'sonarjs/cognitive-complexity': 'off',
      'sonarjs/no-duplicate-string': 'off',
      'sonarjs/todo-tag': 'off',
      // AWS/cloud security rules
      ...sonarjsAwsRulesOff,
    },
  },
  {
    // test rules
    files: ['testing/**', '**/*.test.{ts,tsx}', '*.config.{ts,mjs}'],
    rules: {
      'sonarjs/no-skipped-tests': 'off',
      'sonarjs/no-clear-text-protocols': 'off',
      'sonarjs/no-os-command-from-path': 'off',
    },
  },
  {
    files: ['**/*.{js,jsx,ts,tsx,mjs,cjs}'],
    plugins: { 'react-hooks': reactHooks },
    rules: {
      'react-hooks/incompatible-library': 'warn',
    },
  },
  prettier,
  globalIgnores([
    'node_modules/**',
    '.next/**',
    'out/**',
    'build/**',
    // Never lint built/bundled output or the locally-vendored idetik viewer package.
    '**/dist/**',
    'idetik/**',
    'coverage/**',
    'playwright-report/**',
    'playwright-html-report/**',
    'testing/.auth/**',
    'next-env.d.ts',
  ]),
]);

export default eslintConfig;
