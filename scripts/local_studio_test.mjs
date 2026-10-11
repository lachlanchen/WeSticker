import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { chromium } from "playwright-core";
const url = process.env.WESTICKER_PUBLIC_URL || "http://127.0.0.1:18642/";
const out = ".runtime/local-studio-qa";
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: "/usr/bin/google-chrome",
});
try {
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  const outgoing = [];
  page.on("request", (r) => {
    if (r.method() !== "GET") outgoing.push(r.url());
  });
  await page.goto(url);
  await page
    .getByRole("button", { name: "Create", exact: true })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Saved local photo draft", exact: true })
    .click();
  await page.getByLabel("Caption 1", { exact: true }).waitFor();
  assert(
    await page
      .getByRole("button", { name: "Export photo sticker" })
      .isDisabled(),
  );
  await page.locator('input[type="file"]').setInputFiles("public/icon-512.png");
  await page.waitForFunction(() =>
    JSON.parse(
      localStorage.getItem("westicker-local-studio-v1"),
    ).photo.startsWith("data:image/png"),
  );
  await page.getByLabel("I have permission to use this photo").check();
  await page.getByLabel("Keep this character reference").check();
  await page.getByLabel("Character name", { exact: true }).fill("Aya & Lala");
  await page.getByLabel("Pack title", { exact: true }).fill("A sunny workday");
  await page.getByRole("button", { name: "Ask Agent", exact: true }).click();
  await page
    .getByLabel("Pack brief", { exact: true })
    .fill("Office work with our friends");
  await page.getByRole("button", { name: "Prepare captions" }).click();
  assert.match(
    await page.locator(".caption-plan h3").innerText(),
    /8 captions · Work/,
  );
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "Apply to draft" }).click();
  assert.equal(
    await page.getByLabel("Caption 1", { exact: true }).inputValue(),
    "On it",
  );
  for (const width of [320, 390, 768, 1360]) {
    await page.setViewportSize({ width, height: 900 });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `Overflow at ${width}`,
    );
    await page.screenshot({
      path: `${out}/create-${width}.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: "Ask Agent", exact: true }).click();
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({ path: `${out}/agent-${width}.png` });
    await page.getByRole("button", { name: "Edit draft", exact: true }).click();
  }
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export photo sticker" }).click();
  await (await download).saveAs(`${out}/photo-sticker.png`);
  await page.reload();
  await page
    .getByRole("button", { name: "Create", exact: true })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Saved local photo draft", exact: true })
    .click();
  assert.equal(
    await page.getByLabel("Character name", { exact: true }).inputValue(),
    "Aya & Lala",
  );
  assert.equal(
    await page.getByLabel("Caption 1", { exact: true }).inputValue(),
    "On it",
  );
  assert(await page.getByLabel("Keep this character reference").isChecked());
  await page.getByLabel("I have permission to use this photo").uncheck();
  assert(
    await page
      .getByRole("button", { name: "Export photo sticker" })
      .isDisabled(),
  );
  assert.equal(outgoing.length, 0, "Photo/draft must never leave this device");
  await writeFile(
    `${out}/result.json`,
    JSON.stringify(
      {
        native: false,
        viewports: [320, 390, 768, 1360],
        photoImport: true,
        permissionGuard: true,
        planner: true,
        export: true,
        persistence: true,
        uploads: 0,
      },
      null,
      2,
    ),
  );
  console.log("Local creator: all checks passed");
} finally {
  await browser.close();
}
