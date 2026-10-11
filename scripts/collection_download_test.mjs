// Access/navigation fixtures; not a provider purchase or a production entitlement.
import assert from 'node:assert/strict';
import {mkdir, writeFile} from 'node:fs/promises';
import {chromium} from 'playwright-core';

const origin = process.env.WESTICKER_PUBLIC_URL || 'http://127.0.0.1:18642';
const out = '.runtime/collection-download-qa';
await mkdir(out, {recursive: true});
const browser = await chromium.launch({executablePath: '/usr/bin/google-chrome', headless: true});
const evidence = [];
try {
  for (const scenario of ['guest', 'free', 'expired', 'paid', 'offline', 'revoked', 'zip-error']) {
    const context = await browser.newContext({serviceWorkers: 'block', acceptDownloads: true});
    try {
      const page = await context.newPage();
      const errors = [], zipRequests = [], storeNavigations = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('request', r => {
        if (r.isNavigationRequest() && r.url().startsWith('https://aya.lazying.art/pack/'))
          storeNavigations.push(r.url());
      });
      let bootstrapRequests = 0;
      await page.route('**/api/**', async route => {
        const path = new URL(route.request().url()).pathname;
        if (path === '/api/bootstrap') {
          bootstrapRequests++;
          if (scenario === 'offline') return route.fulfill({status: 503, contentType: 'application/json',
            body: JSON.stringify({error: 'Account service temporarily unavailable.'})});
          return route.fulfill({contentType: 'application/json', body: JSON.stringify({
            user: scenario === 'guest' ? null : {id: 'download-fixture', name: 'Creator',
              consented: 1, plan: scenario === 'free' ? 'free' : 'pocket', credits: 3,
              expires: ['paid', 'revoked', 'zip-error'].includes(scenario) ? Date.now() / 1000 + 3600 : 0},
            csrf: 'fixture', providers: ['lazyingart'], local_accounts: false,
            capabilities: {web_checkout: true}, plans: [], themes: {},
          })});
        }
        if (path === '/api/billing/status') return route.fulfill({contentType: 'application/json',
          body: JSON.stringify({attempts: [], manage: false})});
        if (/^\/api\/default\/[^/]+\/download\/(zh|en|ja)$/.test(path)) {
          zipRequests.push(path);
          if (scenario === 'revoked') return route.fulfill({status: 402,
            contentType: 'application/json', body: JSON.stringify({error: 'Access expired.'})});
          if (scenario === 'zip-error') return route.fulfill({status: 503,
            contentType: 'application/json', body: JSON.stringify({error: 'Temporarily unavailable.'})});
          return route.fulfill({contentType: 'application/zip', headers: {
            'Content-Disposition': 'attachment; filename="WeSticker-fixture.zip"',
          }, body: Buffer.from('PK\x05\x06' + '\0'.repeat(18), 'binary')});
        }
        throw Error('Unexpected API request: ' + path);
      });
      await page.goto(origin);
      await page.getByRole('button', {name: 'Get collection', exact: true}).waitFor();
      assert.equal(bootstrapRequests, 0, 'Browsing remains anonymous without account traffic');
      if (scenario === 'paid') {
        for (const [label, language] of [['中文', 'zh'], ['English', 'en'], ['日本語', 'ja']]) {
          await page.getByRole('button', {name: label, exact: true}).click();
          const downloaded = page.waitForEvent('download');
          await page.getByRole('button', {name: 'Get collection', exact: true}).click();
          const file = await downloaded;
          assert.equal(await file.failure(), null);
          assert(zipRequests.at(-1).endsWith('/download/' + language));
        }
      } else {
        await page.getByRole('button', {name: 'Get collection', exact: true}).click();
        if (scenario === 'guest') {
          await page.getByRole('heading', {name: 'Welcome to WeSticker'}).waitFor();
          assert((await page.getByRole('link', {name: 'Continue with LazyingArt'}).getAttribute('href')).includes('view=account'));
        } else if (scenario === 'offline' || scenario === 'zip-error') {
          await page.getByRole('alert').waitFor();
          assert(await page.getByRole('button', {name: 'Get collection', exact: true}).isVisible());
        } else await page.getByRole('heading', {name: 'Account', exact: true}).waitFor();
        assert.equal(zipRequests.length, ['revoked', 'zip-error'].includes(scenario) ? 1 : 0);
      }
      assert.deepEqual(storeNavigations, []);
      assert.deepEqual(errors, []);
      evidence.push({scenario, zipRequests, noAyaCheckout: true});
    } finally {await context.close();}
  }
  await writeFile(out + '/result.json', JSON.stringify({fixtureOnly: true, evidence}, null, 2));
  console.log('Collection access, language ZIPs and independent-store routing passed.');
} finally {await browser.close();}
