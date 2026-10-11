// Browser recovery fixtures, not proof of a real Stripe charge.
import assert from 'node:assert/strict';
import {mkdir, writeFile} from 'node:fs/promises';
import {chromium} from 'playwright-core';

const origin = process.env.WESTICKER_URL || 'http://127.0.0.1:18642';
const out = '.runtime/web-billing-ui';
await mkdir(out, {recursive: true});
const browser = await chromium.launch({executablePath: '/usr/bin/google-chrome', headless: true});
try {
  for (const scenario of ['closed', 'lost-reply', 'bad-destination']) {
    const context = await browser.newContext({viewport: {width: 1360, height: 1000}, serviceWorkers: 'block'});
    const page = await context.newPage();
    const errors = [], submitted = [];
    page.on('pageerror', error => errors.push(error.message));
    let attempts = [];
    await page.route('**/api/**', async route => {
      const pathname = new URL(route.request().url()).pathname;
      let data = {}, status = 200;
      if (pathname === '/api/bootstrap') data = {
        user: {id: 'billing-ui-fixture', name: 'Creator', plan: 'free', credits: 0, expires: 0, consented: 1},
        csrf: 'fixture', providers: [], local_accounts: false, themes: {},
        capabilities: {web_checkout: scenario !== 'closed'},
        plans: [{id: 'pocket', name: 'Pocket', cents: 99, credits: 3, features: []},
          {id: 'creator', name: 'Creator', cents: 999, credits: 50, features: []}],
      };
      else if (pathname === '/api/billing/status') data = {attempts, manage: false};
      else if (pathname === '/api/billing/subscribe') {
        const body = route.request().postDataJSON();
        submitted.push(body);
        attempts = [{...body, state: 'reserved'}];
        if (scenario === 'lost-reply') {status = 503; data = {error: 'Response interrupted. Resume your checkout.'};}
        else data = {url: 'https://checkout.stripe.com.attacker.invalid/unsafe'};
      }
      else if (pathname === '/api/workspace') data = {packs: [], characters: [], jobs: [],
        limits: {plan: 'free', credits: 0, pack_size: 1, packs: 1, characters: 1, trial_images: 1}};
      else if (pathname === '/api/catalog') return route.continue();
      else throw Error('Unexpected request ' + pathname);
      return route.fulfill({status, contentType: 'application/json', body: JSON.stringify(data)});
    });
    async function openPlans() {
      await page.goto(origin);
      await page.locator('.sidebar,.public-shell,.studio-shell').first().waitFor();
      const full = page.getByRole('button', {name: 'Plans & credits', exact: true});
      if (await full.count()) await full.click();
      else {
        await page.getByRole('button', {name: 'Create', exact: true}).first().click();
        await page.getByRole('button', {name: 'Your account', exact: true}).click();
      }
      await page.locator('.web-plan-row').first().waitFor();
    }
    await openPlans();
    if (scenario === 'closed') {
      assert(await page.getByRole('button', {name: 'Choose', exact: true}).first().isDisabled());
    } else {
      await page.getByRole('button', {name: 'Choose', exact: true}).first().click();
      await page.getByRole('alert').waitFor();
      assert.equal(submitted.length, 1);
      assert.equal(new URL(page.url()).origin, origin);
      if (scenario === 'lost-reply') {
        await openPlans();
        await page.getByRole('button', {name: 'Resume', exact: true}).click();
        await page.getByRole('alert').waitFor();
        assert.equal(submitted.length, 2);
        assert.equal(submitted[0].attempt, submitted[1].attempt);
        assert(await page.getByRole('button', {name: 'Choose', exact: true}).isDisabled());
      } else assert.match(await page.getByRole('alert').innerText(), /destination/);
    }
    for (const width of [320, 390, 1360]) {
      await page.setViewportSize({width, height: 1000});
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      await page.screenshot({path: `${out}/${scenario}-${width}.png`, fullPage: true});
    }
    assert.deepEqual(errors, []);
    await context.close();
  }
  await writeFile(`${out}/result.json`, JSON.stringify({passed: true, fixture_only: true,
    tests: ['disabled sales', 'durable attempt after reload', 'no second checkout', 'URL pinning', 'mobile fit']}));
  console.log('Web billing browser recovery passed; no provider payment made.');
} finally {await browser.close();}
