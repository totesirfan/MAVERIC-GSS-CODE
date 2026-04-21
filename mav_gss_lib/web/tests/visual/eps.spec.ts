// Playwright visual-regression spec for the EPS port.
//
// Baselines live alongside this spec (`baseline-*.png`). The first run
// against a freshly-ported EpsPage produces the actual screenshots;
// the comparison is then byte-diff against baselines at three
// viewports. Use capture-baseline.sh to (re)generate baselines from
// the preview HTML — that is the ground truth.
//
// Copy this file into a project-appropriate location (e.g.
// mav_gss_lib/web/tests/visual/eps.spec.ts). The baselines stay in
// docs/eps-port/visual/ so the port artifacts remain self-contained.

import { expect, test } from "@playwright/test";

const VIEWPORTS = [
  { name: "1080p",  width: 1920, height: 1080 },
  { name: "mbp14",  width: 1512, height:  982 },
  { name: "4k",     width: 3840, height: 2160 },
] as const;

// PIXEL_TOLERANCE = 0.002 → up to 0.2% of pixels may differ before the
// test fails. Tight enough to catch layout drift (missing drop line,
// mis-aligned pill column) but loose enough that font subpixel
// rendering differences between CI and a dev machine do not flake.
const PIXEL_TOLERANCE = 0.002;

test.describe("EPS Live dashboard visual regression", () => {
  for (const vp of VIEWPORTS) {
    test(`matches ${vp.name} baseline`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/docs/eps-preview.html?page=eps&tab=live");
      // Wait for first replay frame from on_client_connect to paint.
      // Selector is preview-compatible (no .eps-page scope) so the same
      // test runs against both the preview (current) and a future React
      // app that wraps its DOM in .eps-page.
      await page.locator(".flow-bus-rail .bus-badge").waitFor();
      await page.waitForTimeout(200);
      // Pause the flow-dash animation so pixel-diffs are deterministic.
      await page.addStyleTag({
        content: `.flow-drop path.flow,
                  .animate-pulse-text,
                  .flash-caution,
                  .flash-danger { animation: none !important; }`,
      });
      await expect(page).toHaveScreenshot(
        `baseline-${vp.name}.png`,
        {
          fullPage: true,
          maxDiffPixelRatio: PIXEL_TOLERANCE,
          animations: "disabled",
        },
      );
    });
  }
});
