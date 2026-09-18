import { defineConfig, devices } from '@playwright/test';

// Regression suite runs against an ephemeral full stack (db + backend + nginx)
// brought up by deploy/docker-compose.test.yml. BASE_URL points at the nginx
// that fronts everything, so the browser sees a single origin exactly as in
// production.
const BASE_URL = process.env.BASE_URL || 'http://localhost:8090';

export default defineConfig({
  testDir: './tests/e2e',
  // A regression gate must not hang a PR: fail loudly instead of waiting.
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  // One retry absorbs cold-start flake without hiding a genuine regression.
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  // The agent reads pw-report.json to report which cases failed; the junit.xml
  // is consumed by the Kiwi TCMS plugin to record a test run for trend
  // dashboards. Keep both paths stable — the workflow references them.
  reporter: [
    ['list'],
    ['json', { outputFile: 'pw-report.json' }],
    ['junit', { outputFile: 'junit.xml' }],
  ],
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
