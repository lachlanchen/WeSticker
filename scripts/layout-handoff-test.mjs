// Read-only acceptance checks for the two independently owned sticker browsers.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright-core";

const out = path.resolve(
  process.env.LAYOUT_EVIDENCE || ".runtime/layout-handoff",
);
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
});
const report = {
  checked: new Date().toISOString(),
  sites: [],
  compatibility: [],
};
const digest = (data) => createHash("sha256").update(data).digest("hex");

async function frames(locator, name, count = 5) {
  const hashes = [];
  for (let i = 0; i < count; i++) {
    const bytes = await locator.screenshot({
      path: path.join(out, `${name}-${i}.png`),
    });
    hashes.push(digest(bytes));
    await new Promise((resolve) => setTimeout(resolve, 270));
  }
  return hashes;
}

try {
  for (const site of [
    {
      id: "aya",
      url: process.env.AYA_URL || "https://aya.lazying.art",
      image: "[data-gif]",
      preview: "[data-preview]",
    },
    {
      id: "westicker",
      url: process.env.WESTICKER_URL || "http://127.0.0.1:18642",
      image: ".sticker-preview img",
      preview: ".sticker-preview",
    },
  ]) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
      locale: "en-US",
    });
    const page = await context.newPage();
    const errors = [],
      requestedGifs = new Set();
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("request", (r) => {
      if (new URL(r.url()).pathname.endsWith(".gif"))
        requestedGifs.add(r.url());
    });
    await page.goto(site.url);
    const packs = page.locator(".collection-link");
    const firstImage = page.locator(site.image).first();
    await firstImage.waitFor();
    assert.equal(await packs.count(), 10);
    assert.equal(await page.locator(site.image).count(), 24);
    await page.waitForFunction((selector) => {
      const i = document.querySelector(selector);
      return i?.src.endsWith(".gif") && i.complete && i.naturalWidth > 0;
    }, site.image);
    assert(
      [...requestedGifs].every((url) =>
        new URL(url).pathname.startsWith("/media/vol-01/"),
      ),
    );
    const motion = await frames(firstImage, `${site.id}-playing`);
    assert(new Set(motion).size > 1, `${site.id}: GIF pixels did not move`);
    await page.screenshot({
      path: path.join(out, `${site.id}-desktop.png`),
      fullPage: true,
    });

    await packs.first().focus();
    await page.keyboard.press("Tab");
    assert(await packs.nth(1).evaluate((e) => e === document.activeElement));
    await page.keyboard.press("Enter");
    await page.waitForFunction(() =>
      document
        .querySelectorAll(".collection-link")[1]
        ?.hasAttribute("aria-current"),
    );
    const selected = await page
      .locator(".collection-link[aria-current]")
      .innerText();
    await page
      .getByRole("button", { name: "Pause animations", exact: true })
      .focus();
    await page.keyboard.press("Space");
    await page.waitForFunction(
      (selector) =>
        [...document.querySelectorAll(selector)].every(
          (i) => !i.src.endsWith(".gif") && i.complete,
        ),
      site.image,
    );
    const paused = await frames(firstImage, `${site.id}-paused`, 3);
    assert.equal(new Set(paused).size, 1, `${site.id}: paused pixels moved`);

    await page.locator(site.preview).first().focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog");
    await dialog.waitFor();
    await page.keyboard.press("Escape");
    await dialog.waitFor({ state: "hidden" });
    const widths = [];
    for (const width of [1440, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth + 1,
      );
      assert(!overflow, `${site.id}: overflow at ${width}`);
      widths.push({ width, overflow });
      if (width === 390)
        await page.screenshot({
          path: path.join(out, `${site.id}-mobile.png`),
          fullPage: true,
        });
    }
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(site.url);
    await page
      .getByRole("button", { name: "Play animations", exact: true })
      .waitFor();
    assert(await firstImage.evaluate((i) => !i.src.endsWith(".gif")));
    assert.deepEqual(errors, []);
    report.sites.push({
      id: site.id,
      url: site.url,
      packs: 10,
      initialStickers: 24,
      keyboardSelected: selected,
      keyboardPause: true,
      keyboardPreviewAndEscape: true,
      playingFrameHashes: motion,
      pausedFrameHashes: paused,
      reducedMotion: true,
      initialGifScope: "selected pack only",
      widths,
      errors,
    });
    await context.close();
  }
  const request = await browser.newContext();
  for (const resource of [
    "/pack/vol-01",
    "/pack/vol-04",
    "/media/vol-01/banner.jpg",
    "/media/vol-04/banner.jpg",
    ...[
      "01-aya-morning",
      "02-lala-arrive",
      "04-sasa-go",
      "03-zhuangzi-received",
    ].flatMap((id) =>
      ["png", "gif"].map((extension) => `/media/vol-01/en/${id}.${extension}`),
    ),
  ]) {
    const response = await request.request.get(
      new URL(resource, process.env.AYA_URL || "https://aya.lazying.art").href,
    );
    assert.equal(response.status(), 200, resource);
    report.compatibility.push({ path: resource, status: response.status() });
    await response.dispose();
  }
  await request.close();
  report.ok = true;
} finally {
  await writeFile(
    path.join(out, "report.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  await browser.close();
}
console.log(`Layout handoff passed for both sites. Evidence: ${out}`);
