import nextJest from "next/jest.js";

const createJestConfig = nextJest({
  dir: "./",
});

export default createJestConfig({
  testEnvironment: "jsdom",
  testMatch: [
    "<rootDir>/frontend/app/**/*.test.{ts,tsx}",
    "<rootDir>/frontend/__tests__/**/*.test.{ts,tsx}",
  ],
});
