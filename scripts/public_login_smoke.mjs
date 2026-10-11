// Read-only live smoke: no account creation, model requests or purchases.
import { chromium } from "playwright-core";
import { mkdir, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";

const origin =
  process.env.WESTICKER_PUBLIC_URL || "https://westicker.lazying.art";
const out = ".runtime/protected-create-live";
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  executablePath: process.env.CHROME || "/usr/bin/google-chrome",
  headless: true,
});
try {
  const context = await browser.newContext({ serviceWorkers: "block" });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(origin);
  await page.locator(".sticker-card").first().waitFor();
  const nav = page.getByRole("navigation", { name: "App navigation" });
  assert.deepEqual(await nav.getByRole("button").allTextContents(), [
    "Stickers",
    "Create",
    "Library",
    "Account",
  ]);
  assert.equal(await page.locator(".sign-in-screen").count(), 0);
  await nav.getByRole("button", { name: "Create", exact: true }).click();
  await page.getByRole("heading", { name: "Welcome to WeSticker" }).waitFor();
  assert.equal(await page.locator(".authentication-page").count(), 1);
  assert.equal(await page.locator(".app nav").count(), 0);
  const link = page.getByRole("link", {
    name: "Continue with LazyingArt",
    exact: true,
  });
  assert.match(
    await link.getAttribute("href"),
    /^\/auth\/lazyingart\/start\?view=create$/,
  );
  assert.equal(await page.locator(".studio-composer").count(), 0);
  for (const width of [390, 1360]) {
    await page.setViewportSize({ width, height: 900 });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    );
    await page.screenshot({
      path: `${out}/login-${width}.png`,
      fullPage: true,
    });
  }
  await page
    .getByRole("button", { name: "Back to stickers", exact: true })
    .click();
  await page.locator(".sticker-card").first().waitFor();
  await nav.getByRole("button", { name: "Account", exact: true }).click();
  await page.getByText("Sign in to your account.", { exact: true }).waitFor();
  const status = await page.evaluate(async () => {
    const retired = await fetch("/api/guest/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "retired-route-check" }),
    });
    const protectedWorkspace = await fetch("/api/workspace");
    return { retired: retired.status, workspace: protectedWorkspace.status };
  });
  assert.deepEqual(status, { retired: 410, workspace: 401 });
  const invalidReturn = await page.goto(
    origin + "/auth/lazyingart/callback?state=invalid",
  );
  assert.equal(invalidReturn.status(), 401);
  await page.getByRole("heading", { name: "Let's reconnect" }).waitFor();
  await page
    .getByRole("link", { name: "Back to sign in", exact: true })
    .click();
  await page.getByRole("heading", { name: "Welcome to WeSticker" }).waitFor();
  assert.deepEqual(errors, []);
  await writeFile(
    `${out}/result.json`,
    JSON.stringify(
      {
        passed: true,
        origin,
        ...status,
        no_account_or_model_action: true,
        widths: [390, 1360],
      },
      null,
      2,
    ),
  );
  console.log(
    "Live public browsing, dedicated sign-in, four tabs and protected endpoints passed.",
  );
} finally {
  await browser.close();
}
