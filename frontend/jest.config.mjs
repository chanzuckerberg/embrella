import nextJest from 'next/jest.js';

const createJestConfig = nextJest({
  dir: './',
});

const baseConfig = createJestConfig({
  testEnvironment: 'jsdom',
  testMatch: [
    '<rootDir>/app/**/*.test.{ts,tsx}',
    // TODO: colocate all tests filtes with file being tested
    '<rootDir>/__tests__/**/*.test.{ts,tsx}',
  ],
  moduleNameMapper: {
    '^@app/(.*)$': '<rootDir>/app/$1',
    '^@testing/(.*)$': '<rootDir>/testing/$1',
    '^@configs/(.*)$': '<rootDir>/configs/$1',
    '^@hooks/(.*)$': '<rootDir>/hooks/$1',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
});

// next/jest overrides transformIgnorePatterns — patch after resolution to allow nuqs (ESM-only)
export default async () => {
  const config = await baseConfig();
  config.transformIgnorePatterns = config.transformIgnorePatterns.map((pattern) =>
    pattern.includes('node_modules') ? pattern.replace('node_modules/', 'node_modules/(?!nuqs)/') : pattern
  );
  return config;
};
