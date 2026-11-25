// Permite abrir el sitio sin conexión con los últimos datos vistos.
// Siempre intenta primero la red (los datos cambian a diario); si no hay conexión, usa la copia guardada.
const CACHE = "seguimiento-v1";
const BASICOS = ["./", "index.html", "estilos.css", "js/app.js", "js/logica.js", "js/vistas.js", "logo-ucr.svg",
  "data/indice.json", "data/novedades.json", "data/estado.json", "data/glosario.json"];

self.addEventListener("install", (ev) => {
  ev.waitUntil(caches.open(CACHE).then((c) => c.addAll(BASICOS)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (ev) => {
  const req = ev.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  ev.respondWith(
    fetch(req)
      .then((resp) => {
        if (resp.ok) {
          const copia = resp.clone();
          caches.open(CACHE).then((c) => c.put(req, copia));
        }
        return resp;
      })
      .catch(() => caches.match(req, { ignoreSearch: true }).then((r) => r || Response.error())),
  );
});
