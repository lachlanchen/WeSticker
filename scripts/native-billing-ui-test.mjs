// Isolated plugin/API fixtures. These are UI contracts, not store purchase proof.
import assert from "node:assert/strict";
import { chromium } from "playwright-core";

const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
});
const product = "art.lazying.westicker.pocket.monthly";
const userId = "11111111111111111111111111111111";
const binding = "11111111-1111-1111-1111-111111111111";
const origin = process.env.WESTICKER_URL || "http://127.0.0.1:18642";
try {
  for (const scenario of [
    "purchased",
    "cancelled",
    "pending",
    "unavailable",
    "closed",
    "left-page",
  ]) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const requests = [];
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.addInitScript(
      ({ scenario, product, binding }) => {
        window.nativeCalls = [];
        window.CapacitorCustomPlatform = { name: "ios" };
        window.Capacitor = {
          PluginHeaders: [
            {
              name: "WeStickerBilling",
              methods: [
                "products",
                "purchase",
                "restore",
                "finish",
                "manage",
                "addListener",
                "removeListener",
              ].map((name) => ({ name, rtype: "promise" })),
            },
          ],
          nativePromise: async (plugin, method) => {
            window.nativeCalls.push(method);
            if (method === "products")
              return {
                products: [{ id: product, name: "Pocket", price: "$0.99" }],
              };
            if (method === "restore") return { receipts: [] };
            if (method === "purchase") {
              if (scenario === "left-page")
                await new Promise((resolve) => {
                  window.finishNativePurchase = resolve;
                });
              return {
                state: scenario,
                receipts: ["purchased", "unavailable", "left-page"].includes(
                  scenario,
                )
                  ? [
                      {
                        provider: "apple",
                        reference: "123",
                        transaction: "456",
                        environment: "Sandbox",
                        binding,
                      },
                    ]
                  : [],
              };
            }
            if (method === "addListener") return "fixture-listener";
            return {};
          },
        };
      },
      { scenario, product, binding },
    );
    await page.route("**/api/**", (route) => {
      const path = new URL(route.request().url()).pathname;
      requests.push({ path, body: route.request().postDataJSON() });
      let body = {},
        status = 200;
      if (path === "/api/bootstrap")
        body = {
          user: {
            id: userId,
            name: "Fixture",
            plan: "free",
            credits: 0,
            expires: 0,
            consented: 1,
          },
          csrf: "fixture",
          providers: [],
          local_accounts: false,
          capabilities: {},
          plans: [
            {
              id: "pocket",
              name: "Pocket",
              cents: 99,
              credits: 3,
              features: ["Three credits"],
            },
          ],
          themes: {},
        };
      else if (path === "/api/workspace")
        body = { packs: [], characters: [], jobs: [] };
      else if (path === "/api/catalog") body = { packs: [] };
      else if (path === "/api/billing/native/catalog")
        body = {
          providers: {
            apple: {
              binding,
              products: { [product]: "pocket" },
              purchase_enabled: scenario !== "closed",
            },
          },
        };
      else if (path === "/api/billing/native/prepare") body = { binding };
      else if (path === "/api/billing/native/verify") {
        if (scenario === "unavailable") {
          status = 503;
          body = {
            error:
              "Store verification unavailable. Use Restore; do not pay again.",
          };
        } else body = { verified: true, active: true };
      } else if (path === "/api/billing/native/outcome") body = { ok: true };
      else throw Error("Unexpected API call: " + path);
      return route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    });
    await page.goto(origin);
    await page
      .getByRole("button", { name: "Plans & credits", exact: true })
      .click();
    await page.getByText("$0.99", { exact: false }).waitFor();
    await page.waitForFunction(() => window.nativeCalls.includes("restore"));
    if (scenario === "closed") {
      assert(
        await page
          .getByRole("button", { name: "Purchase setup pending" })
          .isDisabled(),
      );
      assert(
        await page
          .getByRole("button", { name: "Restore purchases" })
          .isEnabled(),
      );
    } else {
      await page
        .getByRole("button", { name: "Choose Pocket", exact: true })
        .click();
      if (scenario === "left-page") {
        await page.waitForFunction(() =>
          window.nativeCalls.includes("purchase"),
        );
        await page
          .getByRole("button", { name: "Discover", exact: true })
          .click();
        await page.evaluate(async () => {
          window.finishNativePurchase();
          await new Promise(requestAnimationFrame);
        });
        const calls = await page.evaluate(() => window.nativeCalls);
        assert.equal(calls.filter((c) => c === "purchase").length, 1);
        assert.equal(calls.filter((c) => c === "finish").length, 0);
        assert.equal(
          requests.filter((r) => r.path.endsWith("/verify")).length,
          0,
        );
        assert.deepEqual(errors, []);
        await context.close();
        console.log("Native billing UI fixture passed: " + scenario);
        continue;
      }
      const message = {
        purchased: "Purchase verified.",
        cancelled: "Purchase cancelled.",
        pending: "Purchase pending approval. Do not purchase again.",
        unavailable:
          "Store verification unavailable. Use Restore; do not pay again.",
      }[scenario];
      await page.getByRole("status").filter({ hasText: message }).waitFor();
      const calls = await page.evaluate(() => window.nativeCalls);
      assert.equal(calls.filter((c) => c === "purchase").length, 1);
      assert.equal(
        calls.filter((c) => c === "finish").length,
        scenario === "purchased" ? 1 : 0,
      );
      assert.equal(
        requests.filter((r) => r.path.endsWith("/prepare")).length,
        1,
      );
      assert.equal(
        requests.filter((r) => r.path.endsWith("/verify")).length,
        ["purchased", "unavailable"].includes(scenario) ? 1 : 0,
      );
      const outcome = requests.find((r) => r.path.endsWith("/outcome"));
      if (["pending", "cancelled"].includes(scenario))
        assert.equal(outcome.body.state, scenario);
    }
    assert.deepEqual(errors, []);
    await context.close();
    console.log("Native billing UI fixture passed: " + scenario);
  }
} finally {
  await browser.close();
}
