import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source = readFileSync(new URL('../deploy/legacy-catalog-retirement/sw.js', import.meta.url), 'utf8');

function worker(scope = 'https://aya.lazying.art/westicker/') {
  const listeners = {}, removed = [], navigated = [];
  let unregistered = 0, skipped = 0;
  const urls = ['https://aya.lazying.art/westicker/?legacy=1#private',
    'https://aya.lazying.art/westicker/library', 'https://aya.lazying.art/',
    'https://aya.lazying.art/receipt#private', 'https://aya.lazying.art/westicker-other/',
    'https://westicker.lazying.art/'];
  const clients = urls.map(url => ({url, navigate: async destination => navigated.push([url, destination])}));
  vm.runInNewContext(source, {
    URL, Response,
    caches: {keys: async () => ['westicker-shell-old', 'westicker-shell-old-viewed', 'aya-orders', 'other-app'],
      delete: async key => removed.push(key)},
    self: {addEventListener: (name, handler) => {listeners[name] = handler;},
      skipWaiting: async () => skipped++, clients: {matchAll: async () => clients},
      registration: {scope, unregister: async () => unregistered++}},
  });
  return {listeners, removed, navigated, get unregistered() {return unregistered;},
    get skipped() {return skipped;}, async activate() {
      let done; listeners.activate({waitUntil: promise => {done = promise;}}); await done;
    }};
}

test('retires only old caches, its registration and legacy windows', async () => {
  const w = worker(); await w.activate();
  assert.deepEqual(w.removed, ['westicker-shell-old', 'westicker-shell-old-viewed']);
  assert.equal(w.unregistered, 1);
  assert.equal(w.navigated.length, 2);
  assert(w.navigated.every(([, destination]) => destination === 'https://westicker.lazying.art/'));
  assert(!source.includes('localStorage') && !source.includes('indexedDB'));
});

for (const scope of ['https://aya.lazying.art/', 'https://westicker.lazying.art/westicker/']) {
  test(`does not clean an unrelated scope ${scope}`, async () => {
    const w = worker(scope); await w.activate();
    assert.equal(w.unregistered, 0); assert.deepEqual(w.removed, []);
    assert.deepEqual(w.navigated, []);
  });
}

test('waiting legacy navigation redirects but other requests are untouched', async () => {
  const w = worker(); let result;
  w.listeners.fetch({request: {url: 'https://aya.lazying.art/westicker/', mode: 'navigate'},
    respondWith: value => {result = value;}});
  const response = await result;
  assert.equal(response.status, 308);
  assert.equal(response.headers.get('Location'), 'https://westicker.lazying.art/');
  for (const [url, mode] of [['https://aya.lazying.art/', 'navigate'],
    ['https://aya.lazying.art/westicker/sw.js', 'same-origin']]) {
    w.listeners.fetch({request: {url, mode}, respondWith: () => assert.fail('unrelated request intercepted')});
  }
});

test('old deployment CLI stops before touching a release or ingress', async () => {
  const { spawnSync } = await import('node:child_process');
  const result = spawnSync('python3', ['scripts/deploy_catalog_edge.py'], {encoding: 'utf8'});
  assert.equal(result.status, 1);
  assert.match(result.stderr, /retired.*westicker.lazying.art/);
});
