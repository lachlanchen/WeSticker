import {chromium} from "playwright-core";
import {mkdir, writeFile} from "node:fs/promises";
import assert from "node:assert/strict";

const browser = await chromium.launch({executablePath: process.env.CHROME || "/usr/bin/google-chrome", headless: true, args: ["--no-sandbox"]});
const context = await browser.newContext({serviceWorkers: "block"});
const page = await context.newPage();
const errors = [], requests = [];
const out = ".runtime/guest-chat-qa";
await mkdir(out, {recursive: true});
page.on("pageerror", e => errors.push(e.message));
await page.route("**/api/guest/chat", async route => {
  requests.push(route.request().postDataJSON());
  await route.fulfill({json: {reply: "Let's make a cheerful waving sticker. What kind of character do you have in mind?\n\n| Caption | Gesture |\n| --- | --- |\n| Hello! | A small wave |\n\n<script>window.unsafeMarkdown=true</script>![tracking](https://untrusted.invalid/image.png)"}});
});
try {
  await page.goto(process.env.WESTICKER_TEST_URL);
  await page.getByRole("button", {name: "Create", exact: true}).first().click();
  await page.getByLabel("Message Aya", {exact: true}).fill("Help me make a cheerful sticker.");
  assert.equal(await page.locator(".studio-login").count(), 0);
  await page.getByRole("button", {name: "Send message", exact: true}).click();
  await page.getByText("Let's make a cheerful waving sticker.", {exact: false}).waitFor();
  assert.equal(requests.length, 1);
  assert.deepEqual(requests[0].history, []);
  await page.locator(".chat-markdown table").waitFor();
  assert.equal(await page.locator(".chat-markdown table").count(), 1);
  assert.equal(await page.locator(".chat-markdown img").count(), 0);
  assert.equal(await page.evaluate(() => window.unsafeMarkdown), undefined);
  for (const width of [320, 390, 768, 1360]) {
    await page.setViewportSize({width, height: 900});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    assert.equal(await page.locator("nav").getByRole("button", {name: "Characters", exact: true}).count(), 0);
    await page.screenshot({path: `${out}/chat-${width}.png`, fullPage: true});
  }
  await page.reload();
  await page.getByRole("button", {name: "Create", exact: true}).first().click();
  await page.getByText("Let's make a cheerful waving sticker.", {exact: false}).waitFor();
  await page.getByRole("button", {name: "New chat", exact: true}).click();
  await page.getByRole("heading", {name: "What shall we make?"}).waitFor();
  await page.screenshot({path: `${out}/empty-desktop.png`, fullPage: true});
  assert.deepEqual(errors, []);
  await writeFile(`${out}/result.json`, JSON.stringify({passed: true, auth: "anonymous", provider: "browser fixture; no AI call", widths: [320, 390, 768, 1360]}, null, 2));
  console.log("Guest chat layout, persistence and navigation passed.");
} finally {await browser.close();}
