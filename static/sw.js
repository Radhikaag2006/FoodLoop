/* Minimal offline shell: cache static assets, always go to network for data. */
const V = "fl-v14";
const SHELL = ["/", "/static/css/app.css?v=12"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(V).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== V).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.origin !== location.origin || u.pathname.startsWith("/api/")) return;
  if (u.pathname.startsWith("/static/")) {
    e.respondWith(caches.open(V).then(async (c) => {
      // network first so updated JS/CSS is never masked by a stale cache
      try { const res = await fetch(r); if (res.ok) c.put(r, res.clone()); return res; }
      catch (e) { const hit = await c.match(r); if (hit) return hit; throw e; }
    }));
    return;
  }
  if (r.mode === "navigate") {
    e.respondWith(fetch(r).catch(() => caches.match("/")));
  }
});
