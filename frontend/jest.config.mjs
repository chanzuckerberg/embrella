import nextJest from "next/jest.js";

const createJestConfig = nextJest({
  dir: "./",
});

export default createJestConfig({
  setupFiles: ["./testing/setup.ts"]
});
