import { chromium } from "playwright-core";
import { mkdir, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";
import { createHash, randomBytes } from "node:crypto";

const browser = await chromium.launch({
  executablePath: process.env.CHROME || "/usr/bin/google-chrome",
  headless: true,
  args: ["--no-sandbox"],
});
const context = await browser.newContext({ serviceWorkers: "block" });
const page = await context.newPage();
const errors = [],
  anonymousRequests = [];
const out = ".runtime/login-entry-qa";
await mkdir(out, { recursive: true });
page.on("pageerror", (e) => errors.push(e.message));
page.on("request", (r) => {
  if (new URL(r.url()).pathname === "/api/guest/chat")
    anonymousRequests.push(r.url());
});
const origin = process.env.WESTICKER_TEST_URL;
try {
  // Availability fixture tests the four-button layout, not live provider login.
  const methods = await browser.newContext({ serviceWorkers: "block" });
  const methodsPage = await methods.newPage();
  const providerStarts = [];
  let availableMethods = ["google", "apple", "github", "lazyingart"];
  methodsPage.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/auth/"))
      providerStarts.push(request.url());
  });
  await methodsPage.route("**/api/bootstrap", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    await route.fulfill({
      response,
      json: {
        ...data,
        user: null,
        local_accounts: false,
        providers: availableMethods,
      },
    });
  });
  await methodsPage.goto(origin + "?view=account");
  for (const provider of ["Google", "Apple", "GitHub", "LazyingArt"]) {
    const link = methodsPage.getByRole("link", {
      name: "Continue with " + provider,
      exact: true,
    });
    await link.waitFor();
    assert.equal(
      await link.getAttribute("href"),
      "/auth/" + provider.toLowerCase() + "/start?view=account",
    );
  }
  for (const width of [320, 390, 1360]) {
    await methodsPage.setViewportSize({ width, height: 900 });
    assert(
      await methodsPage.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    );
    await methodsPage.screenshot({
      path: `${out}/provider-layout-fixture-${width}.png`,
      fullPage: true,
    });
  }
  assert.equal(await methodsPage.locator(".app nav").count(), 0);
  assert.deepEqual(providerStarts, []);
  availableMethods = [];
  await methodsPage.reload();
  await methodsPage
    .getByRole("status")
    .filter({ hasText: "Sign-in is temporarily unavailable." })
    .waitFor();
  assert(
    await methodsPage
      .getByRole("button", { name: "Try again", exact: true })
      .isVisible(),
  );
  availableMethods = ["lazyingart"];
  await methodsPage
    .getByRole("button", { name: "Try again", exact: true })
    .click();
  await methodsPage
    .getByRole("link", { name: "Continue with LazyingArt", exact: true })
    .waitFor();
  assert.equal(
    await methodsPage
      .getByRole("button", { name: "Try again", exact: true })
      .count(),
    0,
  );
  await methods.close();
  await page.goto(origin);
  assert.equal(await page.locator(".sign-in-screen").count(), 0);
  await page
    .getByRole("button", { name: "Create", exact: true })
    .first()
    .click();
  await page.getByRole("heading", { name: "Welcome to WeSticker" }).waitFor();
  assert.equal(await page.locator(".authentication-page").count(), 1);
  assert.equal(await page.locator(".app nav").count(), 0);
  assert.equal(await page.locator(".studio-composer").count(), 0);
  assert.equal(
    await page.getByRole("heading", { name: "Create", exact: true }).count(),
    0,
  );
  for (const width of [320, 390, 768, 1360]) {
    await page.setViewportSize({ width, height: 900 });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    );
    assert.equal(
      await page
        .locator("nav")
        .getByRole("button", { name: "Characters", exact: true })
        .count(),
      0,
    );
    await page.screenshot({
      path: `${out}/login-${width}.png`,
      fullPage: true,
    });
  }
  await page
    .getByRole("button", { name: "Back to stickers", exact: true })
    .click();
  assert.equal(await page.locator(".sign-in-screen").count(), 0);
  for (const destination of ["Library", "Account"]) {
    const button = page
      .getByRole("button", {
        name:
          destination === "Library" &&
          !(await page.locator(".public-catalog").count())
            ? "My library"
            : destination,
        exact: true,
      })
      .first();
    await button.click();
    await page.getByRole("heading", { name: "Welcome to WeSticker" }).waitFor();
    assert.equal(await page.locator(".authentication-page").count(), 1);
    assert.equal(await page.locator(".app nav").count(), 0);
    await page
      .getByRole("button", { name: "Back to stickers", exact: true })
      .click();
  }
  await page
    .getByRole("button", { name: "Create", exact: true })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Create an account", exact: true })
    .click();
  await page
    .getByLabel("Email", { exact: true })
    .fill(`login-gate-${Date.now()}@example.invalid`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Disposable gate test 123!");
  await page
    .getByRole("button", { name: "Show password", exact: true })
    .click();
  assert.equal(
    await page.getByLabel("Password", { exact: true }).getAttribute("type"),
    "text",
  );
  await page
    .getByRole("button", { name: "Hide password", exact: true })
    .click();
  await page.getByRole("checkbox", { name: /I am 18/ }).check();
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await page.getByRole("heading", { name: "What shall we make?" }).waitFor();
  assert.equal(await page.locator(".sign-in-screen").count(), 0);
  const verifier = randomBytes(32).toString("base64url");
  const challenge = createHash("sha256").update(verifier).digest("base64url");
  const device = await browser.newContext({ serviceWorkers: "block" });
  const made = await device.request.post(origin + "/api/native/link", {
    data: { challenge },
    headers: { Origin: new URL(origin).origin },
  });
  assert.equal(made.status(), 200);
  const link = await made.json();
  const completion = await context.newPage();
  const workspaceRequests = [];
  completion.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/workspace")
      workspaceRequests.push(request.url());
  });
  await completion.goto(link.url);
  await completion
    .getByRole("heading", { name: "Return to WeSticker", exact: true })
    .waitFor();
  assert.equal(
    await completion.locator(".app nav,.studio-composer").count(),
    0,
  );
  await completion
    .getByRole("button", { name: "Connect device", exact: true })
    .click();
  await completion
    .getByRole("heading", { name: "You're connected", exact: true })
    .waitFor();
  assert.deepEqual(workspaceRequests, []);
  const exchanged = await device.request.post(
    origin + `/api/native/link/${link.id}/exchange`,
    { data: { verifier }, headers: { Origin: new URL(origin).origin } },
  );
  assert.equal(exchanged.status(), 200);
  await completion.close();
  await device.close();
  await page
    .getByLabel("Message your sticker assistant")
    .fill("A cheerful hello sticker");
  for (const width of [390, 1360]) {
    await page.setViewportSize({ width, height: 900 });
    const box = await page
      .getByRole("button", { name: "Send message", exact: true })
      .boundingBox();
    assert(
      box &&
        box.x >= 0 &&
        box.x + box.width <= width &&
        box.y + box.height <= 900,
    );
    await page.screenshot({ path: `${out}/chat-${width}.png`, fullPage: true });
  }
  // Simulate expiry before a protected action. The composer must yield to sign-in.
  await context.clearCookies();
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await page.getByRole("heading", { name: "Welcome to WeSticker" }).waitFor();
  assert.equal(await page.locator(".studio-composer").count(), 0);
  assert.deepEqual(anonymousRequests, []);
  assert.deepEqual(errors, []);
  await writeFile(
    `${out}/result.json`,
    JSON.stringify(
      {
        passed: true,
        authenticated: "isolated local account; no live provider call",
        widths: [320, 390, 768, 1360],
        tests: [
          "public catalog",
          "four-provider layout and destinations (availability fixture only)",
          "empty provider discovery offers retry rather than a blank login",
          "Create sign-in gate",
          "one global login outside tabs for Create/Library/Account",
          "native completion outside chat with real isolated PKCE exchange",
          "back to browsing",
          "registration returns to chat",
          "password visibility",
          "expired session returns to login",
          "no anonymous requests",
        ],
      },
      null,
      2,
    ),
  );
  console.log("Public catalog and protected Create entry passed.");
} finally {
  await browser.close();
}
