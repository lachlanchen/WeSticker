import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { chromium } from "playwright-core";

const url =
  process.env.WESTICKER_PUBLIC_URL || "https://aya.lazying.art/westicker/";
const out = process.env.WESTICKER_QA_OUT || ".runtime/public-catalog-qa";
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
});
const context = await browser.newContext();
const requests = [];
context.on("request", (r) => requests.push(r.url()));
const evidence = [];
try {
  const page = await context.newPage();
  for (const width of [390, 1360]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(url);
    await page.locator(".collection-link").first().waitFor();
    assert.equal(await page.locator(".collection-link").count(), 10);
    if (width === 390) {
      await page.waitForFunction(
        () =>
          document
            .querySelector(".sticker-preview img")
            ?.src.includes("/motion/"),
        null,
        { timeout: 45_000 },
      );
    }
    await page
      .locator(".sticker-preview img")
      .first()
      .evaluate((img) => img.decode());
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    assert.equal(
      await page.getByRole("button", { name: "Sign in", exact: true }).count(),
      0,
    );
    await page.locator(".sticker-preview img").evaluateAll(async (images) => {
      await Promise.all(
        images
          .filter((img) => img.getBoundingClientRect().top < innerHeight)
          .map((img) => img.decode()),
      );
    });
    await page.screenshot({ path: `${out}/catalog-${width}.png` });
    await page.locator(".sticker-preview").first().click();
    await page.getByRole("dialog").waitFor();
    const href = await page
      .getByRole("link", { name: "Save GIF", exact: true })
      .getAttribute("href");
    assert(href.startsWith("https://aya.lazying.art/media/"));
    await page.getByRole("button", { name: "Close preview" }).click();
    await page
      .getByRole("button", { name: "Pause animations", exact: true })
      .click();
    evidence.push({ width, noOverflow: true, preview: true, directGif: true });
  }
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller)
      await new Promise((resolve) =>
        navigator.serviceWorker.addEventListener("controllerchange", resolve, {
          once: true,
        }),
      );
  });
  await context.setOffline(true);
  await page.reload();
  await page.locator(".collection-link").first().waitFor();
  await page
    .locator(".sticker-preview img")
    .first()
    .evaluate((img) => img.decode());
  assert(
    !requests.some((u) => new URL(u).pathname.match(/^\/(api|auth)(\/|$)/)),
  );
  const scope = await page.evaluate(
    async () => (await navigator.serviceWorker.ready).scope,
  );
  assert.equal(scope, url);
  await writeFile(
    `${out}/result.json`,
    JSON.stringify(
      { evidence, offline: true, scope, noBackendRequests: true },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({ evidence, offline: true, scope, noBackendRequests: true }),
  );
} finally {
  await context.close();
  await browser.close();
}
