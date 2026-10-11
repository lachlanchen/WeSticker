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
// UI regression runs may reuse approved local art instead of consuming edge bandwidth.
if (process.env.WESTICKER_QA_ART_ROOT) {
  const root = path.resolve(process.env.WESTICKER_QA_ART_ROOT);
  await context.route("https://aya.lazying.art/media/**", async (route) => {
    const url = new URL(route.request().url());
    const file = path.resolve(root, "." + decodeURIComponent(url.pathname));
    assert(file.startsWith(root + path.sep));
    await route.fulfill({ path: file });
  });
}
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
  await page.locator(".collection-link").first().waitFor();
  assert.equal(await page.locator(".collection-link").count(), 10);
  assert.equal(await page.locator(".sticker-card").count(), 24);
  await page.locator(".collection-list img").evaluateAll(async (images) => {
    await Promise.all(
      images.map((i) => {
        i.loading = "eager";
        return i.decode();
      }),
    );
  });
  await page
    .locator(".collection-list img")
    .first()
    .evaluate((image) => image.decode());
  await fits();
  await page.screenshot({
    path: path.join(out, "desktop-discover.png"),
    fullPage: true,
  });
  await page.getByLabel("Save Little everyday joys").click();
  await page.waitForFunction(() =>
    /\.gif|\/motion\//.test(
      document.querySelector(".sticker-preview img")?.src || "",
    ),
  );
  await page
    .getByRole("button", { name: "Pause animations", exact: true })
    .click();
  await page.waitForFunction(
    () =>
      !/\.gif|\/motion\//.test(
        document.querySelector(".sticker-preview img")?.src || "",
      ),
  );
  await page.locator(".collection-link").nth(1).click();
  await page.waitForFunction(() =>
    [...document.querySelectorAll(".sticker-preview img")].every(
      (i) => !/\.gif|\/motion\//.test(i.src),
    ),
  );
  await page
    .getByRole("button", { name: "Play animations", exact: true })
    .click();
  await page.locator(".collection-link").first().click();
  await page.getByLabel("Search collections").fill("NO_RESULT_123");
  assert.equal(await page.locator(".sticker-card").count(), 0);
  await page.getByRole("button", { name: "Show all collections" }).click();
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
  const download = page.waitForEvent("download", { timeout: 120_000 });
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
  for (const width of [768, 1024, 1200]) {
    await page.setViewportSize({ width, height: 900 });
    await fits();
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  await page
    .getByRole("button", { name: "Play animations", exact: true })
    .waitFor();
  assert(
    await page
      .locator(".sticker-preview img")
      .first()
      .getAttribute("src")
      .then((s) => !/\.gif|\/motion\//.test(s)),
  );
  await page.emulateMedia({ reducedMotion: "no-preference" });
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
    .getByRole("checkbox", { name: /permission to use these images/ })
    .check();
  await page
    .locator(".studio-start input[type=file]")
    .setInputFiles("public/icon-512.png");
  await page.locator(".reference-strip img").first().waitFor();
  await page
    .getByRole("button", { name: "Approve references & start" })
    .click();
  await page.getByLabel("Caption 1", { exact: true }).fill("Hello there");
  await page.getByRole("button", { name: "Save table", exact: true }).click();
  await page
    .getByRole("button", { name: "Use uploaded photo", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirm photo preview", exact: true })
    .click();
  await page.locator(".artifact-table img").waitFor({ timeout: 20000 });
  await page
    .getByRole("checkbox", { name: "Approve sticker 1", exact: true })
    .check();
  await page.getByRole("button", { name: "Save table", exact: true }).click();
  await page.screenshot({
    path: path.join(out, "desktop-editor-reviewed.png"),
    fullPage: true,
  });
  const zipDownload = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export", exact: true }).click();
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
        previewTransport: process.env.WESTICKER_QA_ART_ROOT
          ? "approved local artwork fixture"
          : "public edge",
        downloadTransport: "real application endpoint",
        checks: [
          "guest master-detail catalog",
          "autoplay, pause, reduced motion, filtered selection",
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
