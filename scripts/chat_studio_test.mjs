import { chromium } from "playwright-core";
import { mkdir, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";

const base = process.env.WESTICKER_TEST_URL || "http://127.0.0.1:18642";
const browser = await chromium.launch({
  executablePath: process.env.CHROME || "/usr/bin/google-chrome",
  headless: true,
  args: ["--no-sandbox"],
});
const context = await browser.newContext({
  viewport: { width: 1360, height: 1000 },
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const out = ".runtime/chat-studio-qa";
await mkdir(out, { recursive: true });
let account = false;
try {
  await page.goto(base);
  await page
    .getByRole("button", { name: "Create", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "New account", exact: true }).click();
  await page
    .getByLabel("Email", { exact: true })
    .fill(`studio-qa-${Date.now()}@example.invalid`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Disposable studio test 123!");
  await page.getByRole("checkbox", { name: /I am 18/ }).check();
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  account = true;
  await page.getByRole("heading", { name: "Who are we creating?" }).waitFor();
  await page.getByLabel("Name", { exact: true }).fill("Studio review mascot");
  await page.getByRole("checkbox", { name: /permission to use/ }).check();
  await page
    .locator(".studio-start input[type=file]")
    .setInputFiles("public/icon-192.png");
  await page.locator(".reference-strip img").first().waitFor();
  await page.getByLabel("Collection name").fill("A small hello");
  await page
    .getByRole("button", { name: "Approve references & start" })
    .click();
  await page.getByLabel("Caption 1", { exact: true }).waitFor();
  assert(
    await page
      .getByRole("button", { name: "Add word", exact: true })
      .isDisabled(),
  );
  await page
    .getByLabel("Message your sticker assistant")
    .fill("change 1 to Hello there");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await page.getByRole("button", { name: "Apply table", exact: true }).click();
  await page.waitForFunction(
    () =>
      document.querySelector('[aria-label="Caption 1"]').value ===
      "Hello there",
  );
  await page
    .getByLabel("Action 1", { exact: true })
    .fill("Lift one hand, wave twice, blink and relax.");
  await page.getByRole("button", { name: "Save table", exact: true }).click();
  await page.waitForFunction(
    () => document.querySelector(".artifact-actions .primary") === null,
  );
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
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export", exact: true }).click();
  await (await download).saveAs(out + "/reviewed.zip");
  await page
    .getByRole("button", { name: "Version history", exact: true })
    .click();
  await page.locator(".version-dialog img").first().waitFor();
  await page.getByRole("button", { name: "Close version history" }).click();
  for (const width of [390, 768, 1360]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.screenshot({
      path: `${out}/create-${width}.png`,
      fullPage: true,
    });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
      `overflow at ${width}`,
    );
  }
  await page.reload();
  await page.getByRole("button", { name: "My library", exact: true }).click();
  await page.getByRole("button", { name: /A small hello/ }).click();
  await page.waitForFunction(
    () =>
      document.querySelector('[aria-label="Caption 1"]')?.value ===
      "Hello there",
  );
  await page.getByRole("button", { name: "Characters", exact: true }).click();
  await page.getByRole("heading", { name: "Studio review mascot" }).waitFor();
  assert.deepEqual(errors, []);
  await writeFile(
    out + "/result.json",
    JSON.stringify(
      {
        passed: true,
        tested: [
          "private signup",
          "reference upload",
          "character approval",
          "chat proposal/apply",
          "direct action edit",
          "free single limit",
          "photo job/export",
          "history",
          "library persistence",
          "characters",
          "responsive layout",
        ],
        ai_provider: "not configured; no model call made",
      },
      null,
      2,
    ),
  );
  console.log(
    "Chat studio browser workflow passed. No paid generation submitted.",
  );
} finally {
  if (account)
    await page
      .evaluate(async () => {
        const b = await (await fetch("/api/bootstrap")).json();
        await fetch("/api/account/delete", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": b.csrf,
          },
          body: JSON.stringify({ confirmation: "DELETE" }),
        });
      })
      .catch(() => {});
  await browser.close();
}
