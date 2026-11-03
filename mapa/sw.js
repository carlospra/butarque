/*
 * Service worker: permite usar el mapa sin conexión (por ejemplo, durante una ruta).
 *   - La app (HTML, JS, CSS, Leaflet): se sirve de la caché y se actualiza en segundo plano.
 *   - Los datos (datos/*.json): primero la red; si no hay, la última copia guardada.
 * Versión estática para GitHub Pages: todas las rutas son relativas a la carpeta de la app.
 *   - Teselas del mapa, fotos y audios: de la caché si ya se vieron (hasta un límite).
 */
const VERSION = "mapa-butarque-estatico-v1";      // cambiar al publicar una versión nueva de la app
const BASE = new URL("./", self.location).pathname;          // p. ej. /butarque/mapa/
const APP = ["./", "app.js", "estilos.css", "manifest.webmanifest", "vendor/leaflet/leaflet.js",
             "vendor/leaflet/leaflet.css", "vendor/qrcode/qrcode.js", "iconos/icono-192.png"];
const MAX_TESELAS = 400;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(APP)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function recortar(nombre, max) {
  const c = await caches.open(nombre);
  const claves = await c.keys();
  for (const k of claves.slice(0, Math.max(0, claves.length - max))) await c.delete(k);
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Navegación (incluidos los enlaces ?p=... de los QR): la app, desde la red o la caché
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).catch(() => caches.match(BASE)));
    return;
  }
  // Datos: red primero
  if (url.origin === location.origin && url.pathname.startsWith(BASE + "datos/")) {
    e.respondWith(fetch(req).then((r) => {
      if (r.ok) { const copia = r.clone(); caches.open(VERSION + "-api").then((c) => c.put(req, copia)); }
      return r;
    }).catch(() => caches.match(req)));
    return;
  }
  // Teselas, fotos y audios: caché primero
  if (url.hostname.endsWith("tile.openstreetmap.org") || url.hostname.endsWith("usercontent.google.com") || url.pathname.startsWith(BASE + "media/")) {
    const nombre = VERSION + "-recursos";
    e.respondWith(caches.match(req).then((guardada) => guardada || fetch(req).then((r) => {
      if (r.ok || r.type === "opaque") {
        const copia = r.clone();
        caches.open(nombre).then((c) => c.put(req, copia)).then(() => recortar(nombre, MAX_TESELAS));
      }
      return r;
    })));
    return;
  }
  // Resto de la app: caché y actualización en segundo plano
  if (url.origin === location.origin) {
    e.respondWith(caches.match(req).then((guardada) => {
      const red = fetch(req).then((r) => {
        if (r.ok) { const copia = r.clone(); caches.open(VERSION).then((c) => c.put(req, copia)); }
        return r;
      }).catch(() => guardada);
      return guardada || red;
    }));
  }
});
