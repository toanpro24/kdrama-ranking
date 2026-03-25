const CACHE_NAME = "kdrama-v2";
const PRECACHE = ["/", "/favicon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  if (!e.request.url.startsWith("http")) return;
  // Skip API calls — let them go straight to network
  if (e.request.url.includes("/api/")) return;

  // Network-first for HTML and JS/CSS (ensures fresh code on reload)
  const url = new URL(e.request.url);
  const isAsset = /\.(js|css|html)$/.test(url.pathname) || e.request.mode === "navigate";

  if (isAsset) {
    // Network-first: try network, fall back to cache
    e.respondWith(
      fetch(e.request).then((res) => {
        if (res.ok && res.type === "basic") {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        }
        return res;
      }).catch(() => caches.match(e.request))
    );
  } else {
    // Cache-first for images, fonts, etc.
    e.respondWith(
      caches.match(e.request).then((cached) =>
        cached || fetch(e.request).then((res) => {
          if (res.ok && res.type === "basic") {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
          }
          return res;
        })
      )
    );
  }
});
