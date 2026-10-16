import { chromium } from "playwright-core";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";

const origin = process.env.WESTICKER_TEST_URL;
if (!origin || !origin.startsWith("http://127.0.0.1:"))
  throw Error("Isolated test server required");
const browser = await chromium.launch({
  executablePath: process.env.CHROME || "/usr/bin/google-chrome",
  headless: true,
  args: ["--no-sandbox"],
});
const out = ".runtime/shared-account-qa";
await mkdir(out, { recursive: true });
try {
  const context = await browser.newContext({ serviceWorkers: "block" });
  const created = await context.request.post(origin + "/api/auth/register", {
    headers: { Origin: origin },
    data: {
      name: "Test creator",
      email: "shared-ui@example.invalid",
      password: "Isolated UI password 123!",
      adult: true,
      terms: true,
    },
  });
  assert.equal(created.status(), 200);
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(origin + "/?view=account");
  const panel = page.locator(".shared-account");
  await panel.getByText("Not available yet.", { exact: true }).waitFor();
  assert.equal(await panel.getByRole("checkbox").count(), 0);
  assert.equal(await panel.getByText(/0 LAC points/).count(), 0);
  for (const width of [320, 390, 1360]) {
    await page.setViewportSize({ width, height: 900 });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    );
    await page.screenshot({
      path: `${out}/disabled-${width}.png`,
      fullPage: true,
    });
    await panel.scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${out}/account-panel-${width}.png` });
  }
  let state = "ready";
  await page.route("**/api/account/shared", (route) =>
    route.fulfill({
      json: {
        linked: true,
        can_link: false,
        points: {
          available: true,
          state:
            state === "consent_required" ? "consent_required" : "consented",
          can_disconnect: true,
        },
      },
    }),
  );
  await page.route("**/api/account/shared/points", (route) =>
    route.fulfill({
      json:
        state === "ready"
          ? {
              state: "ready",
              awarded_points: "0",
              pending_points: "2",
              as_of: Math.floor(Date.now() / 1000),
              revision: "3",
            }
          : { state },
    }),
  );
  await panel.getByRole("button", { name: "Refresh shared account" }).click();
  await panel.getByText("0 LAC points", { exact: true }).waitFor();
  state = "unavailable";
  await panel.getByRole("button", { name: "Refresh shared account" }).click();
  await panel
    .getByText("Balance unavailable. No balance is assumed.", { exact: true })
    .waitFor();
  assert.equal(
    await panel.getByText("0 LAC points", { exact: true }).count(),
    0,
  );
  state = "consent_required";
  await panel.getByRole("button", { name: "Refresh shared account" }).click();
  await panel.getByRole("checkbox").waitFor();
  assert(
    await panel
      .getByRole("button", { name: "Connect points", exact: true })
      .isDisabled(),
  );
  await panel.getByRole("checkbox").check();
  assert(
    await panel
      .getByRole("button", { name: "Connect points", exact: true })
      .isEnabled(),
  );
  await page.screenshot({ path: `${out}/consent-1360.png`, fullPage: true });
  for (const width of [390, 1360]) {
    await page.setViewportSize({ width, height: 900 });
    await panel
      .getByRole("button", { name: "Connect points", exact: true })
      .scrollIntoViewIfNeeded();
    const button = await panel
      .getByRole("button", { name: "Connect points", exact: true })
      .boundingBox();
    assert(button && button.y >= 0 && button.y + button.height < 820);
    await page.screenshot({ path: `${out}/consent-panel-${width}.png` });
  }
  assert.deepEqual(errors, []);
  await writeFile(
    `${out}/result.json`,
    JSON.stringify(
      {
        passed: true,
        widths: [320, 390, 1360],
        scope:
          "isolated local account and synthetic balance UI; no issuer or Coin request",
        tests: [
          "disabled is not zero",
          "current zero displayed",
          "outage clears old balance",
          "explicit checkbox gates consent",
          "responsive Account panel",
        ],
      },
      null,
      2,
    ),
  );
  console.log(
    "Shared account UI checks passed; no external service or financial action.",
  );
} finally {
  await browser.close();
}
