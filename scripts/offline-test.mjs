import assert from "node:assert/strict";
import { chromium } from "playwright-core";

const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
});
const context = await browser.newContext();
try {
  const page = await context.newPage();
  await page.goto(
    process.env.WESTICKER_PRODUCTION_URL || "http://127.0.0.1:18641",
  );
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
  assert.equal(await page.locator(".collection-link").count(), 10);
  assert.equal(await page.locator(".sticker-card").count(), 24);
  await page
    .locator(".sticker-preview img")
    .first()
    .evaluate((img) => img.decode());
  const cached = await page.evaluate(async () => {
    const paths = [];
    for (const key of await caches.keys())
      for (const r of await (await caches.open(key)).keys())
        paths.push(new URL(r.url).pathname);
    return paths;
  });
  assert(
    !cached.some((path) => path.startsWith("/api") || path.startsWith("/auth")),
  );
  console.log(
    "Production offline shell: ten collections and local artwork load; no API/auth data cached.",
  );
} finally {
  await context.close();
  await browser.close();
}
