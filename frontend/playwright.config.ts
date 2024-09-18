import type { PlaywrightTestConfig } from "@playwright/test";
import { devices } from "@playwright/test";
const config: PlaywrightTestConfig = {
  expect: {
    timeout: 15 * 1000,
  },
  fullyParallel: true,
  outputDir: "playwright-report/",
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "edge",
      use: { ...devices["Desktop Edge"] },
    },
  ],
  testDir: "testing",
  testMatch: /.*\.test\.ts/,
  timeout: 1.5 * 60 * 1000,
  use: {
    baseURL: "http://localhost:3000/next",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: 'retain-on-failure',
  },
  webServer: {
    command: "yarn && yarn dev",
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
    url: "http://localhost:3000/",
  },
  workers: "75%",
};
export default config;
