import type { PlaywrightTestConfig } from '@playwright/test';
import { devices } from '@playwright/test';

import { STORAGE_STATE_PATH } from './testing/global-setup';

// In the devcontainer, hit nginx (port 80 on the compose network) — it fronts
// both Next.js and Django on a single origin, which matters because
// app/common/constants/api.ts derives DJANGO_URL from window.location.origin
// when the hostname isn't `localhost`. Going straight to `http://frontend:3000`
// would point API calls back at Next.js and the page would never authenticate.
// Skip the local webServer block too — the frontend container already runs
// `yarn dev`. PLAYWRIGHT_BASE_URL overrides if set; otherwise the DEVCONTAINER
// flag (set by .devcontainer/devcontainer.json) drives the switch.
const inDevcontainer = process.env.DEVCONTAINER === 'true';
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? (inDevcontainer ? 'http://nginx/' : 'http://localhost:3000/');
const config: PlaywrightTestConfig = {
  expect: {
    timeout: 15 * 1000,
  },
  fullyParallel: true,
  outputDir: 'playwright-report/',
  // create a report (open html file in /frontend/playwright-html-report)
  reporter: [['list'], ['html', { outputFolder: 'playwright-html-report', open: 'never' }]],
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Inside the devcontainer, podman's default /dev/shm is 64 MB, which
        // chromium fills under parallel test load and crashes the container.
        // Telling chromium to write shm to /tmp avoids the limit entirely.
        launchOptions: inDevcontainer ? { args: ['--disable-dev-shm-usage'] } : undefined,
      },
    },
  ],
  testDir: 'testing',
  testMatch: /.*\.test\.ts/,
  timeout: 1.5 * 60 * 1000,
  globalSetup: inDevcontainer ? require.resolve('./testing/global-setup') : undefined,
  use: {
    baseURL,
    screenshot: 'only-on-failure',
    storageState: inDevcontainer ? STORAGE_STATE_PATH : undefined,
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
  },
  webServer:
    process.env.PLAYWRIGHT_BASE_URL || inDevcontainer
      ? undefined
      : {
          command: 'yarn && yarn dev',
          reuseExistingServer: !process.env.CI,
          timeout: 120 * 1000,
          url: 'http://localhost:3000/',
        },
  workers: '25%',
};
export default config;
