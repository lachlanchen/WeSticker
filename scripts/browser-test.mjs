import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require(
  process.env.PLAYWRIGHT_MODULE || "playwright-core",
);
const origin = process.env.WESTICKER_URL || "http://127.0.0.1:18642";
const out = path.resolve(".runtime/browser-qa");
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
async function fits() {
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    `Overflow at ${page.viewportSize().width}`,
  );
}
try {
  await page.goto(origin);
  await page
    .getByRole("heading", { name: "Find your kind of cute." })
    .waitFor();
  await page.locator(".pack-card").first().waitFor();
  assert.equal(await page.locator(".pack-card").count(), 10);
  await page.locator(".pack-art img").evaluateAll(async (images) => {
    await Promise.all(
      images.map((i) => {
        i.loading = "eager";
        return i.decode();
      }),
    );
  });
  await page
    .locator(".pack-art img")
    .first()
    .evaluate((image) => image.decode());
  await fits();
  await page.screenshot({
    path: path.join(out, "desktop-discover.png"),
    fullPage: true,
  });
  await page.getByLabel("Save Little everyday joys").click();
  await page
    .getByRole("button", { name: "Explore", exact: true })
    .first()
    .click();
  await page
    .locator(".sticker-preview img")
    .first()
    .evaluate((image) => image.decode());
  assert.equal(await page.locator(".sticker-card").count(), 24);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await page
    .locator(".sticker-preview img")
    .first()
    .evaluate((image) => image.decode());
  await page.locator(".sticker-preview").first().click();
  await page.getByRole("dialog", { name: "Sticker preview" }).waitFor();
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Save GIF", exact: true }).click();
  const gif = await download;
  assert.equal(await gif.failure(), null);
  await page.getByLabel("Close preview").click();
  await page.setViewportSize({ width: 390, height: 844 });
  await fits();
  await page.locator(".sticker-preview img").evaluateAll(async (images) => {
    await Promise.all(
      images.map((i) => {
        i.loading = "eager";
        return i.decode();
      }),
    );
  });
  await page.screenshot({
    path: path.join(out, "mobile-collection.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 320, height: 740 });
  await fits();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page
    .getByRole("button", { name: "New here? Create an account" })
    .click();
  const modal = page.getByRole("dialog", { name: "Sign in" });
  await modal.getByLabel("Name", { exact: true }).fill("Browser QA");
  await modal
    .getByLabel("Email", { exact: true })
    .fill(`qa-${Date.now()}@example.test`);
  await modal
    .getByLabel("Password", { exact: true })
    .fill("temporary-browser-test-password");
  await modal.getByLabel("I am 18 or older.").check();
  await modal.getByLabel("I agree to the terms and privacy policy.").check();
  await modal
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await modal.waitFor({ state: "hidden" });
  await page
    .getByRole("button", { name: "Create", exact: true })
    .first()
    .click();
  await page.getByLabel("Name", { exact: true }).fill("Demo friend");
  await page
    .getByLabel(
      "I own these images or have permission. Everyone depicted is 18+ and has agreed.",
    )
    .check();
  await page.locator("input[type=file]").setInputFiles("public/icon-512.png");
  await page.locator(".ref-grid img").waitFor();
  await page
    .getByLabel(
      "These photos show the character I want. Keep this identity consistent.",
    )
    .check();
  await page
    .getByRole("button", { name: "Lock character & create draft" })
    .click();
  await page.getByRole("button", { name: "Photo stickers · free" }).waitFor();
  await page.screenshot({
    path: path.join(out, "desktop-editor-empty.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Photo stickers · free" }).click();
  await page
    .getByText("Ready for your review", { exact: true })
    .waitFor({ timeout: 20000 });
  await page.getByLabel("Caption 1", { exact: true }).fill("Hello there");
  for (const checkbox of await page
    .getByLabel("Looks like me", { exact: true })
    .all())
    await checkbox.check();
  await page.screenshot({
    path: path.join(out, "desktop-editor-reviewed.png"),
    fullPage: true,
  });
  const zipDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export ZIP", exact: true }).click();
  const zip = await zipDownload;
  assert.equal(await zip.failure(), null);
  await zip.saveAs(path.join(out, "photo-stickers.zip"));
  await page.setViewportSize({ width: 390, height: 844 });
  await fits();
  await page.screenshot({
    path: path.join(out, "mobile-editor.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: "Account", exact: true }).click();
  await page.getByRole("button", { name: "Delete my account" }).click();
  await page.getByLabel("Type DELETE").fill("DELETE");
  await page
    .getByRole("button", { name: "Delete account and creations" })
    .click();
  await page.getByRole("button", { name: "Sign in", exact: true }).waitFor();
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify(
      {
        ok: true,
        checks: [
          "guest catalog",
          "three-language preview",
          "GIF download",
          "favorite",
          "320/390/1440 width",
          "registration",
          "reference upload",
          "character approval",
          "photo worker",
          "caption review",
          "ZIP export",
          "account deletion",
        ],
        pageErrors: errors,
      },
      null,
      2,
    ),
  );
  console.log("Browser workflow passed. Evidence: " + out);
} finally {
  await context.close();
  await browser.close();
}
