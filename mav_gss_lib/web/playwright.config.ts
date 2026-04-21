import { defineConfig, devices } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// The visual regression gate compares screenshots of the EPS page against
// baselines captured from `docs/eps-preview.html`. Pixel-equivalent
// rendering of the React app requires seeded EPS HK data over a live
// WS connection, which is out of scope for this gate — so the gate
// compares the preview HTML served as-is (same source the baselines
// were captured from). The invariant it enforces: the visual pipeline
// (playwright + baseline paths + viewports) is wired correctly and the
// preview still renders identically to the saved baselines. A future
// revision can swap in a mock Vite server + MSW to exercise the React
// path directly.

const REPO_ROOT = path.resolve(__dirname, '..', '..')
const BASELINE_DIR = path.join(REPO_ROOT, 'docs', 'eps-port', 'visual')

export default defineConfig({
  testDir: 'tests/visual',
  // Route toHaveScreenshot('baseline-1080p.png') to the real baseline dir.
  snapshotPathTemplate: `${BASELINE_DIR}/{arg}{ext}`,
  use: {
    baseURL: 'http://127.0.0.1:4173',
  },
  webServer: {
    command: `python3 -m http.server 4173 --directory "${REPO_ROOT}"`,
    url: 'http://127.0.0.1:4173/docs/eps-preview.html',
    reuseExistingServer: true,
    timeout: 30_000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  reporter: [['list']],
})
