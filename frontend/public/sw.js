// Offline shell: cache the app shell, serve the last successful API response when offline.
const SHELL = "food-alert-shell-v2";
const DATA = "food-alert-data-v1";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL).then((c) => c.addAll(["/", "/manifest.webmanifest"]).catch(() => undefined)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== SHELL && k !== DATA).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith("/api/")) {
    // network-first: fresh data wins, cached copy keeps the app usable offline
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(DATA).then((c) => c.put(request, copy)).catch(() => undefined);
          }
          return res;
        })
        .catch(async () => (await caches.match(request)) || new Response(
          JSON.stringify({ detail: "Dati temporaneamente non disponibili" }),
          { status: 503, headers: { "Content-Type": "application/json" } },
        )),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).catch(async () => (await caches.match("/")) || new Response(
      "Offline",
      { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } },
    ))),
  );
});
