/**
 * Service Worker for Cache Management and Version Control
 * Handles cache invalidation when new versions are deployed
 * Enhanced PWA functionality with offline support
 */

const CACHE_VERSION = 'v1.0.9';
const CACHE_NAME = `physioprism-${CACHE_VERSION}`;
const OFFLINE_CACHE = `physioprism-offline-${CACHE_VERSION}`;

// Resources to cache immediately (shell assets)
const STATIC_RESOURCES = [
  '/static/style.css',
  '/static/logo.png',
  '/static/assessmentProgress.css',
  '/static/main.js',
  '/static/assessmentProgress.js',
  '/static/draftAutoSave.js',
  '/static/form-change-tracker.js',
  '/static/version-check.js'
  // Note: manifest.json and pwa-install.js intentionally not cached
];

// Offline fallback page
const OFFLINE_PAGE = '/offline';

// API endpoints to never cache
const API_PATTERNS = [
  '/api/',
  '/auth/',
  '/login',
  '/logout',
  '/register'
];

// Install event - cache static resources and offline page
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing version:', CACHE_VERSION);

  event.waitUntil(
    Promise.all([
      // Cache static resources
      caches.open(CACHE_NAME)
        .then((cache) => {
          console.log('[Service Worker] Caching static resources');
          // Cache files individually to avoid failing on missing files
          return Promise.allSettled(
            STATIC_RESOURCES.map(url =>
              cache.add(url).catch(err => {
                console.warn('[Service Worker] Failed to cache:', url, err);
              })
            )
          );
        }),
      // Cache offline page separately
      caches.open(OFFLINE_CACHE)
        .then((cache) => {
          console.log('[Service Worker] Caching offline page');
          return cache.add(OFFLINE_PAGE).catch(err => {
            console.warn('[Service Worker] Failed to cache offline page:', err);
          });
        })
    ])
    .then(() => {
      // Force the waiting service worker to become the active service worker
      return self.skipWaiting();
    })
    .catch((error) => {
      console.error('[Service Worker] Installation error:', error);
      // Continue anyway
      return self.skipWaiting();
    })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating version:', CACHE_VERSION);

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            // Keep current cache and offline cache
            if (cacheName !== CACHE_NAME && cacheName !== OFFLINE_CACHE) {
              console.log('[Service Worker] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        // Take control of all pages immediately
        return self.clients.claim();
      })
  );
});

// Helper function to check if URL should be cached
function shouldCache(url) {
  // Don't cache API endpoints
  for (const pattern of API_PATTERNS) {
    if (url.pathname.includes(pattern)) {
      return false;
    }
  }
  return true;
}

// Fetch event - serve from cache or network with offline fallback
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests
  if (url.origin !== self.location.origin) {
    return;
  }

  // Skip API calls (always fetch from network)
  if (!shouldCache(url)) {
    return;
  }

  // Network-first strategy for HTML pages
  if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Clone the response
          const responseClone = response.clone();

          // Update cache only for successful responses
          if (response && response.status === 200) {
            caches.open(CACHE_NAME)
              .then((cache) => cache.put(request, responseClone));
          }

          return response;
        })
        .catch(async () => {
          // Try to get from cache
          const cachedResponse = await caches.match(request);
          if (cachedResponse) {
            return cachedResponse;
          }

          // If not in cache, return offline page
          const offlineResponse = await caches.match(OFFLINE_PAGE);
          if (offlineResponse) {
            return offlineResponse;
          }

          // Last resort: return a basic offline response
          return new Response(
            '<html><body><h1>Offline</h1><p>You are currently offline. Please check your connection.</p></body></html>',
            {
              status: 503,
              statusText: 'Service Unavailable',
              headers: new Headers({
                'Content-Type': 'text/html'
              })
            }
          );
        })
    );
    return;
  }

  // Cache-first strategy for static resources
  event.respondWith(
    caches.match(request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          // Return cached version and update in background
          fetch(request)
            .then((response) => {
              if (response && response.status === 200) {
                caches.open(CACHE_NAME)
                  .then((cache) => cache.put(request, response));
              }
            })
            .catch(() => {
              // Ignore fetch errors for background updates
            });

          return cachedResponse;
        }

        // Not in cache, fetch from network
        return fetch(request)
          .then((response) => {
            // Don't cache if not successful
            if (!response || response.status !== 200) {
              return response;
            }

            // Clone the response
            const responseClone = response.clone();

            // Add to cache
            caches.open(CACHE_NAME)
              .then((cache) => cache.put(request, responseClone));

            return response;
          })
          .catch(() => {
            // Return a fallback response for failed static resource loads
            return new Response('Resource not available offline', {
              status: 503,
              statusText: 'Service Unavailable'
            });
          });
      })
  );
});

// Message event - handle commands from clients
self.addEventListener('message', (event) => {
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys()
        .then((cacheNames) => {
          return Promise.all(
            cacheNames.map((cacheName) => caches.delete(cacheName))
          );
        })
        .then(() => {
          // Notify client
          event.ports[0].postMessage({ success: true });
        })
    );
  }
});
