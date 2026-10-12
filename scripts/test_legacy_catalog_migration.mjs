import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import http from 'node:http';
import { chromium } from 'playwright-core';

const canonical = 'https://westicker.lazying.art/';
let retired = false, origin;
const source = await readFile(new URL('../deploy/legacy-catalog-retirement/sw.js', import.meta.url), 'utf8');
const server = http.createServer((request, response) => {
  response.setHeader('Cache-Control', 'no-store');
  if (request.url === '/westicker/sw.js') {
    response.setHeader('Content-Type', 'application/javascript');
    response.end(retired ? source.replace("'https://aya.lazying.art'", JSON.stringify(origin)) : `
      self.addEventListener('install', e => e.waitUntil(self.skipWaiting()));
      self.addEventListener('activate', e => e.waitUntil((async () => {
        await caches.open('westicker-shell-fixture');
        await caches.open('aya-orders-fixture');
        await clients.claim();
      })()));
    `);
  } else {
    response.setHeader('Content-Type', 'text/html');
    response.end('<!doctype html><title>Legacy fixture</title><main>Legacy catalog</main>');
  }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
origin = `http://127.0.0.1:${server.address().port}`;
let browser;
try {
  browser = await chromium.launch({headless: true, executablePath: '/usr/bin/google-chrome'});
  const context = await browser.newContext();
  await context.route(canonical, route => route.fulfill({contentType: 'text/html',
    body: '<!doctype html><title>Canonical fixture</title><main>WeSticker</main>'}));
  const page = await context.newPage();
  await page.goto(origin + '/westicker/');
  await page.evaluate(async () => {
    localStorage.setItem('private-draft-fixture', 'keep');
    await navigator.serviceWorker.register('/westicker/sw.js');
    await navigator.serviceWorker.ready;
  });
  await page.waitForFunction(() => navigator.serviceWorker.controller);
  retired = true;
  await page.evaluate(() => {navigator.serviceWorker.getRegistration().then(r => r.update());});
  await page.waitForURL(canonical, {timeout: 15000});
  const shop = await context.newPage();
  await shop.goto(origin + '/');
  const state = await shop.evaluate(async () => ({
    registrations: (await navigator.serviceWorker.getRegistrations()).length,
    caches: await caches.keys(), draft: localStorage.getItem('private-draft-fixture'),
  }));
  assert.equal(state.registrations, 0);
  assert.deepEqual(state.caches, ['aya-orders-fixture']);
  assert.equal(state.draft, 'keep');
  console.log(JSON.stringify({pass: true, canonicalNavigation: page.url(),
    oldWorkerUnregistered: true, oldShellRemoved: true, shopCacheAndDraftPreserved: true,
    fixtureOnly: true, productionMutations: false}));
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
