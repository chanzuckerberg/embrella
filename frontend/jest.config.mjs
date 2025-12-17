import nextJest from 'next/jest.js';

const createJestConfig = nextJest({
  dir: './',
});

export default createJestConfig({
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
