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
      // (thuang): Allow args prefixed with `_`
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
      // AWS/cloud security rules
      ...sonarjsAwsRulesOff,
      // TODO: (eslint-upgrade): triage and re-enable these as errors. Downgraded to `warn`
      // during the ESLint 10 / Next 16 / sonarjs v4 upgrade to land the tooling bump without
      // a large cross-codebase refactor. Tracked for follow-up cleanup.
      'sonarjs/no-nested-conditional': 'warn',
      'sonarjs/no-skipped-tests': 'warn',
      'sonarjs/todo-tag': 'warn',
      'sonarjs/no-commented-code': 'warn',
      'sonarjs/no-nested-functions': 'warn',
      'sonarjs/no-clear-text-protocols': 'warn',
      'sonarjs/use-type-alias': 'warn',
      'sonarjs/slow-regex': 'warn',
      'sonarjs/pseudo-random': 'warn',
      'sonarjs/redundant-type-aliases': 'warn',
      'sonarjs/no-invariant-returns': 'warn',
      'sonarjs/concise-regex': 'warn',
      'sonarjs/no-os-command-from-path': 'warn',
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
    'coverage/**',
    'playwright-report/**',
    'playwright-html-report/**',
    'testing/.auth/**',
    'next-env.d.ts',
  ]),
]);

export default eslintConfig;
