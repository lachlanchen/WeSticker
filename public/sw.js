const CACHE='westicker-shell-__BUILD_HASH__';
const BASE=new URL(self.registration.scope).pathname;
const RUNTIME=CACHE+'-viewed';
self.addEventListener('install',event=>{event.waitUntil((async()=>{
 const manifest=await fetch(BASE+'asset-manifest.json').then(r=>r.json());
 const cache=await caches.open(CACHE);await cache.addAll([BASE,...manifest.files]);
 await self.skipWaiting();
})())});
self.addEventListener('activate',event=>{event.waitUntil((async()=>{
 for(const key of await caches.keys())if(key.startsWith('westicker-shell-')&&key!==CACHE&&key!==RUNTIME)await caches.delete(key);
 await self.clients.claim();
})())});
self.addEventListener('fetch',event=>{
 const u=new URL(event.request.url);
 if(event.request.method!=='GET'||u.origin!==location.origin||!u.pathname.startsWith(BASE)||u.pathname.slice(BASE.length).match(/^(api|auth)(\/|$)/))return;
 if(event.request.mode==='navigate')event.respondWith(fetch(event.request).catch(()=>caches.match(BASE)));
 else event.respondWith((async()=>{
   const cached=await caches.match(event.request);if(cached)return cached;
   const response=await fetch(event.request);
   if(response.ok&&u.pathname.startsWith(BASE+'previews/')){
     const cache=await caches.open(RUNTIME);await cache.put(event.request,response.clone());
     const keys=await cache.keys();for(const key of keys.slice(0,Math.max(0,keys.length-160)))await cache.delete(key);
   }
   return response;
 })());
});
