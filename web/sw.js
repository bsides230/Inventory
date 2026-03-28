const CACHE_VERSION = 'v4';
const STATIC_CACHE = `falcones-static-${CACHE_VERSION}`;
const API_CACHE = `falcones-api-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/style.css',
  '/app.js',
  '/manifest.json',
  '/assets/icon-32.png',
  '/assets/icon-192.png',
  '/assets/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(STATIC_CACHE).then((cache) => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(
      keys
        .filter((key) => ![STATIC_CACHE, API_CACHE].includes(key))
        .map((key) => caches.delete(key))
    );
    await self.clients.claim();
  })());
});

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

function offlineApiResponse() {
  return new Response(
    JSON.stringify({ success: false, message: 'Offline: API unavailable. Please reconnect and try again.' }),
    {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    }
  );
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') {
    if (request.url.includes('/api/')) {
      event.respondWith(fetch(request).catch(() => offlineApiResponse()));
    }
    return;
  }

  const requestUrl = new URL(request.url);
  const isApi = requestUrl.pathname.startsWith('/api/');

  if (isApi) {
    event.respondWith((async () => {
      try {
        const networkResponse = await fetch(request);
        const cache = await caches.open(API_CACHE);
        cache.put(request, networkResponse.clone());
        return networkResponse;
      } catch (_error) {
        const cached = await caches.match(request);
        return cached || offlineApiResponse();
      }
    })());
    return;
  }

  event.respondWith((async () => {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }

    const networkResponse = await fetch(request);
    const cache = await caches.open(STATIC_CACHE);
    cache.put(request, networkResponse.clone());
    return networkResponse;
  })());
});
