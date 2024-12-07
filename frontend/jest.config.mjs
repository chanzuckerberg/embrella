import nextJest from "next/jest.js";

const createJestConfig = nextJest({
  dir: "./",
});

export default createJestConfig({
  testEnvironment: "jsdom",
  testMatch: [
    "<rootDir>/app/**/*.test.{ts,tsx}",
    "<rootDir>/__tests__/**/*.test.{ts,tsx}",
  ],
});
