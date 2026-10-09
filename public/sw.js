const CACHE='westicker-shell-__BUILD_HASH__';
self.addEventListener('install',event=>{event.waitUntil((async()=>{
 const manifest=await fetch('/asset-manifest.json').then(r=>r.json());
 const cache=await caches.open(CACHE);await cache.addAll(['/',...manifest.files]);
 await self.skipWaiting();
})())});
self.addEventListener('activate',event=>{event.waitUntil((async()=>{
 for(const key of await caches.keys())if(key.startsWith('westicker-shell-')&&key!==CACHE)await caches.delete(key);
 await self.clients.claim();
})())});
self.addEventListener('fetch',event=>{
 const u=new URL(event.request.url);
 if(event.request.method!=='GET'||u.origin!==location.origin||u.pathname.startsWith('/api')||u.pathname.startsWith('/auth'))return;
 if(event.request.mode==='navigate')event.respondWith(fetch(event.request).catch(()=>caches.match('/')));
 else event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request)));
});
