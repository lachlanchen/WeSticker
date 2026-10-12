// Retire only the former AYA catalog worker. Preserve local drafts and accounts.
const LEGACY_ORIGIN = 'https://aya.lazying.art';
const LEGACY_PATH = '/westicker/';
const DESTINATION = 'https://westicker.lazying.art/';

self.addEventListener('install', event => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const scope = new URL(self.registration.scope);
    if (scope.origin !== LEGACY_ORIGIN || scope.pathname !== LEGACY_PATH) return;
    for (const key of await caches.keys()) {
      if (key.startsWith('westicker-shell-')) await caches.delete(key);
    }
    const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    await self.registration.unregister();
    for (const client of clients) {
      const url = new URL(client.url);
      if (url.origin === LEGACY_ORIGIN &&
          (url.pathname === '/westicker' || url.pathname.startsWith(LEGACY_PATH))) {
        // Do not carry legacy query parameters, authentication or private fragments.
        await client.navigate(DESTINATION).catch(() => {});
      }
    }
  })());
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.mode === 'navigate' && url.origin === LEGACY_ORIGIN &&
      (url.pathname === '/westicker' || url.pathname.startsWith(LEGACY_PATH))) {
    event.respondWith(Promise.resolve(Response.redirect(DESTINATION, 308)));
  }
});
