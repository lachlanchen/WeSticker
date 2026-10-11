import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { chromium } from "playwright-core";

const origin = process.env.WESTICKER_PUBLIC_URL || "https://westicker.lazying.art";
const out = process.env.WESTICKER_QA_OUT || ".runtime/creator-edge-qa";
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome" });
const context = await browser.newContext();
const page = await context.newPage();
const errors = [];
page.on("pageerror", e => errors.push(e.message));
const checks = [];
try {
  for (const width of [390, 1360]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(origin);
    await page.locator(".collection-link").first().waitFor();
    await page.waitForFunction(() => document.querySelector(".sticker-preview img")?.src.includes("/motion/"));
    await page.locator(".sticker-preview img").first().evaluate(img => img.decode());
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: `${out}/catalog-${width}.png` });
    await page.getByRole("button", { name: "Create", exact: true }).first().click();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: `${out}/create-${width}.png` });
    checks.push({ width, animatedPreview: true, noOverflow: true, create: true });
  }
  const health = await context.request.get(origin + "/api/health");
  assert.equal(health.status(), 200);
  const boot = await context.request.get(origin + "/api/bootstrap");
  assert.equal(boot.status(), 200);
  assert.equal(boot.headers()["cache-control"], "no-store");
  const state = await boot.json();
  assert.equal(state.local_accounts, false);
  for (const path of ["/api/workspace", "/api/assets/not-owned"]) {
    const r = await context.request.get(origin + path, { headers: {
      Authorization: "Bearer not-a-session", "X-Westicker-Relay": "impostor",
      "X-Westicker-Client-Authorization": "Bearer impostor", "X-Westicker-Client-IP": "127.0.0.1",
    } });
    assert.equal(r.status(), 401);
  }
  const csrf = await context.request.post(origin + "/api/account/consent", {
    headers: { Origin: "https://untrusted.example" }, data: { adult: true, terms: true },
  });
  assert.equal(csrf.status(), 403);
  assert.equal((await context.request.get(origin + "/.env")).status(), 404);
  assert.equal((await context.request.delete(origin + "/api/workspace")).status(), 405);
  assert.equal((await context.request.get(origin + "/terms.html")).status(), 200);
  assert.equal((await context.request.get(origin + "/privacy.html")).status(), 200);
  assert.deepEqual(errors, []);
  const result = { checks, privateAccessRejected: true, spoofedHeadersRejected: true,
    foreignOriginRejected: true, apiNoStore: true, capabilities: state.capabilities,
    providers: state.providers, tlsVerified: true, generationInvoked: false };
  await writeFile(`${out}/result.json`, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
