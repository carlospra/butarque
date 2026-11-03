/*
 * Mapa vivo de Butarque · app móvil web (PWA)
 *
 * VERSIÓN ESTÁTICA (GitHub Pages): sin servidor ni base de datos.
 * El contenido sale de ficheros JSON de la carpeta datos/, exportados de la
 * API del servidor de contenidos. No se pueden enviar recuerdos.
 * En el navegador solo se guardan los puntos visitados (pasaporte).
 *
 * Parámetros de prueba en la URL:
 *   ?simular=1    tocar el mapa simula tu posición (para probar "cerca de mí" sin salir a la calle)
 *   ?p=<id>       abre directamente la ficha de un punto (lo que abren los QR)
 */
"use strict";

const DATOS = "datos";
const TESELAS = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATRIBUCION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
const RADIO_AVISO_M = 40;                 // geovalla: a esta distancia se avisa del punto
const CENTRO = [40.3480, -3.6780];

const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const params = new URLSearchParams(location.search);

const estado = {
  capas: [], puntos: [], activas: new Set(), anios: [], hasta: null,
  marcadores: new Map(), seleccionado: null,
  ruta: null, capaRuta: null,
  siguiendo: false, posicion: null, marcaYo: null, vigilancia: null, avisados: new Set(),
  simular: params.has("simular"),
  visitados: new Set(leerLocal("visitados", [])),
};

function leerLocal(clave, defecto) {
  try { return JSON.parse(localStorage.getItem(clave)) ?? defecto; } catch { return defecto; }
}
function guardarLocal(clave, valor) {
  try { localStorage.setItem(clave, JSON.stringify(valor)); } catch { /* modo privado */ }
}

// Traduce cada ruta de la API a su fichero JSON en datos/ (mismas respuestas, sin servidor)
async function api(ruta) {
  const [camino, consulta] = ruta.split("?");
  if (camino === "/cercanos") return cercanos(new URLSearchParams(consulta));
  const r = await fetch(`${DATOS}${camino}.json`);
  if (!r.ok) throw Object.assign(new Error(`Error ${r.status}`), { estado: r.status });
  const datos = await r.json();
  if (camino.startsWith("/puntos/")) datos.url = urlPunto(datos.id);
  return datos;
}

// Lo que hacía GET /api/cercanos en el servidor, calculado en el navegador
function cercanos(q) {
  const pos = { lat: +q.get("lat"), lon: +q.get("lon") }, radio = +q.get("radio") || 1500;
  return estado.puntos
    .map((p) => ({ ...p, distancia_m: Math.round(distancia(pos, p)) }))
    .filter((p) => p.distancia_m <= radio)
    .map((p) => ({ ...p, minutos: Math.round(p.distancia_m / 1000 / 4.5 * 60) }))
    .sort((a, b) => a.distancia_m - b.distancia_m);
}

// Dirección de la ficha de un punto en esta misma web (vale en cualquier usuario o repositorio)
function urlPunto(id) {
  return `${location.origin}${location.pathname}?p=${encodeURIComponent(id)}`;
}
function urlConParams(id) {
  const q = new URLSearchParams(location.search);
  id ? q.set("p", id) : q.delete("p");
  const t = q.toString();
  return location.pathname + (t ? "?" + t : "");
}

function distancia(a, b) {
  const R = 6371000, rad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * rad, dLon = (b.lon - a.lon) * rad;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

let ocultarAviso;
function aviso(texto, accion) {
  const el = $("#aviso");
  el.innerHTML = `<span>${esc(texto)}</span>`;
  if (accion) {
    const b = document.createElement("button");
    b.textContent = accion.texto;
    b.onclick = () => { el.hidden = true; accion.fn(); };
    el.append(b);
  }
  el.hidden = false;
  clearTimeout(ocultarAviso);
  ocultarAviso = setTimeout(() => (el.hidden = true), accion ? 8000 : 3500);
}

/* ------------------------------------------------------------------ mapa */
const mapa = L.map("mapa", { zoomControl: false, attributionControl: true }).setView(CENTRO, 15);
L.control.zoom({ position: "topright" }).addTo(mapa);
L.tileLayer(TESELAS, { maxZoom: 19, attribution: ATRIBUCION }).addTo(mapa);
mapa.attributionControl.setPrefix(false);

function ajustarAltoBarra() {
  document.documentElement.style.setProperty("--alto-barra", $(".barra").offsetHeight + "px");
  mapa.invalidateSize();
}
window.addEventListener("resize", ajustarAltoBarra);

function crearMarcador(p) {
  const m = L.circleMarker([p.lat, p.lon], {
    radius: 9, color: "#fff", weight: 2.5, fillColor: p.color, fillOpacity: 1,
    dashArray: p.anio == null ? "3 3" : null,
  });
  m.bindTooltip(p.titulo_corto || p.titulo, { direction: "top", offset: [0, -8] });
  m.on("click", () => abrirFicha(p.id));
  estado.marcadores.set(p.id, m);
  return m;
}

function visible(p) {
  if (!estado.activas.has(p.capa_id)) return false;
  if (estado.ruta) return estado.ruta.paradas.some((s) => s.id === p.id);
  return estado.hasta == null || p.anio == null || p.anio <= estado.hasta;
}

function pintar() {
  for (const p of estado.puntos) {
    const m = estado.marcadores.get(p.id);
    const ver = visible(p);
    if (ver && !mapa.hasLayer(m)) m.addTo(mapa);
    if (!ver && mapa.hasLayer(m)) m.remove();
    const sel = estado.seleccionado === p.id;
    m.setStyle({ radius: sel ? 13 : 9, weight: sel ? 4 : 2.5, color: sel ? "#2b2620" : "#fff" });
    if (sel) m.bringToFront();
  }
  if (!$("#lista").hidden) pintarLista();
}

function encuadrar(puntos) {
  if (!puntos.length) return;
  const limites = L.latLngBounds(puntos.map((p) => [p.lat, p.lon]));
  const tapa = !$("#hoja").hidden && window.innerWidth < 760 ? $("#hoja").offsetHeight : $("#dock").offsetHeight;
  const abajo = tapa + 30;
  mapa.fitBounds(limites, { paddingTopLeft: [30, 30], paddingBottomRight: [30, abajo], maxZoom: 17 });
}

function centrarEnPunto(p) {
  // deja el punto visible por encima de la hoja inferior
  const hoja = $("#hoja").hidden ? 0 : $("#hoja").offsetHeight;
  const z = Math.max(mapa.getZoom(), 16);
  const destino = mapa.project([p.lat, p.lon], z).add([0, window.innerWidth >= 760 ? 0 : hoja / 2.6]);
  mapa.flyTo(mapa.unproject(destino, z), z, { duration: 0.5 });
}

/* ------------------------------------------------------------------ capas */
function pintarCapas() {
  const nav = $("#capas");
  nav.innerHTML = "";
  for (const c of estado.capas) {
    const b = document.createElement("button");
    b.className = "chip";
    b.setAttribute("aria-pressed", estado.activas.has(c.id));
    b.innerHTML = `<span class="chip__punto" style="background:${esc(c.color)}"></span>${esc(c.nombre_corto || c.nombre)}`;
    b.title = c.nombre;
    b.setAttribute("aria-label", `${c.nombre}: ${c.puntos} puntos`);
    b.onclick = () => {
      estado.activas.has(c.id) ? estado.activas.delete(c.id) : estado.activas.add(c.id);
      b.setAttribute("aria-pressed", estado.activas.has(c.id));
      pintar();
    };
    nav.append(b);
  }
}

/* ------------------------------------------------------------------ línea del tiempo */
function prepararTiempo() {
  estado.anios = [...new Set(estado.puntos.filter((p) => p.anio != null).map((p) => p.anio))].sort((a, b) => a - b);
  const d = $("#deslizador");
  d.max = estado.anios.length;        // la última posición es "todo"
  d.value = estado.anios.length;
  d.oninput = () => fijarTiempo(+d.value);
  fijarTiempo(+d.value);
}

function etiquetaAnio(anio) {
  const p = estado.puntos.find((x) => x.anio === anio);
  return p?.fecha_texto || String(anio);
}

function fijarTiempo(i) {
  const n = estado.anios.length;
  estado.hasta = i >= n ? null : estado.anios[i];
  const visibles = estado.puntos.filter((p) => p.anio != null && (estado.hasta == null || p.anio <= estado.hasta)).length;
  $("#tiempo-valor").textContent = estado.hasta == null ? "Todo" : `hasta ${etiquetaAnio(estado.hasta)}`;
  $("#deslizador").setAttribute("aria-valuetext", `${$("#tiempo-valor").textContent}, ${visibles} hitos`);
  pintar();
}

let reproduciendo = null;
function reproducir() {
  const b = $("#btn-reproducir"), d = $("#deslizador");
  if (reproduciendo) { clearInterval(reproduciendo); reproduciendo = null; b.textContent = "▶"; return; }
  if (estado.ruta) salirDeRuta();
  d.value = 0; fijarTiempo(0); b.textContent = "⏸";
  reproduciendo = setInterval(() => {
    const v = +d.value + 1;
    d.value = v; fijarTiempo(v);
    if (v >= estado.anios.length) { clearInterval(reproduciendo); reproduciendo = null; b.textContent = "▶"; }
  }, 900);
}

/* ------------------------------------------------------------------ hoja inferior */
function mostrarHoja(html, compacta = false) {
  $("#hoja-contenido").innerHTML = html;
  $("#hoja").classList.toggle("hoja--compacta", compacta);
  $("#hoja").hidden = false;
  $("#hoja-contenido").scrollTop = 0;
}

function cerrarHoja(cambiarUrl = true) {
  $("#hoja").hidden = true;
  estado.seleccionado = null;
  pintar();
  if (cambiarUrl && rutaDeUrl()) history.pushState(null, "", urlConParams(null));
}

async function abrirFicha(id, cambiarUrl = true) {
  let p;
  try { p = await api(`/puntos/${encodeURIComponent(id)}`); }
  catch (e) { aviso(e.estado === 404 ? "Ese punto no existe o no está publicado" : "No se pudo cargar el punto"); return; }
  estado.seleccionado = p.id;
  if (cambiarUrl) history.pushState({ id: p.id }, "", urlConParams(p.id));

  const imagenes = p.recursos.filter((r) => r.tipo === "imagen");
  const audios = p.recursos.filter((r) => r.tipo === "audio");
  const videos = p.recursos.filter((r) => r.tipo === "video");
  const juegos = p.recursos.filter((r) => r.tipo === "juego");
  const enlaces = p.recursos.filter((r) => r.tipo === "enlace" || r.tipo === "documento");
  const parrafos = p.descripcion ? p.descripcion.split("\n\n").map((t) => `<p>${esc(t)}</p>`).join("")
    : `<p class="vacio">Este lugar aún no tiene descripción. ¿Lo conoces? Cuéntanos abajo qué recuerdas de él.</p>`;
  const visitado = estado.visitados.has(p.id);

  mostrarHoja(`
    <article class="ficha">
      ${imagenes.map((r) => `
        <figure class="ficha__foto">
          <img src="${esc(r.url)}" alt="${esc(r.texto_alt || r.titulo)}" loading="lazy">
          <figcaption>Foto: ${esc(r.autoria)}</figcaption>
        </figure>`).join("")}
      <h2>${esc(p.titulo)}</h2>
      <div class="meta">
        <span class="etiqueta"><span class="chip__punto" style="background:${esc(p.capa.color)}"></span>${esc(p.capa.nombre)}</span>
        ${p.fecha_texto ? `<span class="etiqueta etiqueta--fecha">${esc(p.fecha_texto)}</span>` : `<span class="etiqueta">Sin fecha</span>`}
        ${visitado ? `<span class="etiqueta visitado">✓ Visitado</span>` : ""}
      </div>
      ${audios.map((r) => `
        <div class="audio">
          <audio controls preload="none" src="${esc(r.url)}" aria-label="${esc(r.titulo)}"></audio>
          <small>${esc(r.titulo)} · ${esc(r.autoria)}</small>
        </div>`).join("")}
      ${parrafos}
      ${videos.map((r) => `<video controls preload="none" src="${esc(r.url)}" style="width:100%"></video><small>${esc(r.titulo)} · ${esc(r.autoria)}</small>`).join("")}
      ${juegos.length ? `<h3>Juega en el Arcade de Butarque</h3>` + juegos.map((r) =>
        `<a class="boton-juego" href="${esc(r.url)}" target="_blank" rel="noopener">▶ ${esc(r.titulo.replace(/^Juega:\s*/, ""))}</a>`).join("") : ""}
      ${enlaces.length ? `<h3>Para saber más</h3>` + enlaces.map((r) =>
        `<a class="enlace" href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.titulo)} ↗</a>`).join("") : ""}
      ${p.rutas.length ? `<h3>Forma parte de</h3><div class="rutas-del-punto">` + p.rutas.map((r) =>
        `<button class="boton boton--claro" data-ruta="${esc(r.id)}">🥾 ${esc(r.nombre)} · parada ${r.orden + 1}</button>`).join("") + "</div>" : ""}
      <h3>Recuerdos del barrio</h3>
      ${p.recuerdos.length ? p.recuerdos.map((r) => `
        <blockquote class="recuerdo"><p>${esc(r.texto)}</p><footer>${esc(r.nombre || "Anónimo")} · ${esc(r.fecha)}</footer></blockquote>`).join("")
        : `<p class="vacio">Todavía no hay recuerdos de este lugar.</p>`}
      <p class="vacio">En esta versión de demostración no se pueden enviar recuerdos: hace falta el servidor de contenidos.</p>
      <div class="fila-botones">
        <button class="boton boton--claro" id="btn-compartir">↗ Compartir</button>
        <button class="boton boton--claro" id="btn-qr">▦ Código QR</button>
      </div>
      <p class="fuente">Fuente: ${esc(p.fuente)}</p>
    </article>`);

  $("#hoja-contenido").querySelectorAll("[data-ruta]").forEach((b) => (b.onclick = () => elegirRuta(b.dataset.ruta)));
  $("#btn-compartir").onclick = () => compartir(p);
  $("#btn-qr").onclick = () => {
    $("#qr-titulo").textContent = p.titulo_corto || p.titulo;
    const qr = qrcode(0, "M"); qr.addData(p.url); qr.make();
    $("#qr-imagen").src = qr.createDataURL(8, 2);
    $("#qr-imagen").alt = `Código QR que abre ${p.url}`;
    $("#dialogo-qr").showModal();
  };
  pintar();
  centrarEnPunto(p);
}

async function compartir(p) {
  const datos = { title: p.titulo, text: `${p.titulo} · Mapa vivo de Butarque`, url: p.url };
  try {
    if (navigator.share) await navigator.share(datos);
    else { await navigator.clipboard.writeText(p.url); aviso("Enlace copiado"); }
  } catch { /* cancelado */ }
}

/* ------------------------------------------------------------------ rutas */
async function abrirRutas() {
  const rutas = await api("/rutas");
  mostrarHoja(`
    <h2>Rutas a pie</h2>
    <p>Recorridos por la historia del barrio. Elige uno para verlo en el mapa.</p>
    ${rutas.map((r) => `
      <button class="ruta" data-ruta="${esc(r.id)}" style="border-left-color:${esc(r.color)}">
        <strong>${esc(r.nombre)}</strong>
        <span>${r.paradas} paradas · ${(r.distancia_m / 1000).toFixed(1).replace(".", ",")} km · unos ${r.minutos} min a pie</span>
      </button>`).join("")}`);
  $("#hoja-contenido").querySelectorAll("[data-ruta]").forEach((b) => (b.onclick = () => elegirRuta(b.dataset.ruta)));
}

async function elegirRuta(id) {
  const r = await api(`/rutas/${encodeURIComponent(id)}`);
  salirDeRuta(false);
  estado.ruta = r;
  $("#btn-rutas").setAttribute("aria-pressed", "true");
  estado.capaRuta = L.layerGroup().addTo(mapa);
  L.polyline(r.paradas.map((p) => [p.lat, p.lon]), { color: r.color, weight: 5, opacity: 0.8, dashArray: "8 8" }).addTo(estado.capaRuta);
  r.paradas.forEach((p, i) => {
    L.marker([p.lat, p.lon], {
      icon: L.divIcon({ className: "", html: `<div class="marca-parada" style="background:${esc(r.color)}">${i + 1}</div>`, iconSize: [30, 30], iconAnchor: [15, 15] }),
      title: `Parada ${i + 1}: ${p.titulo_corto || p.titulo}`,
    }).on("click", () => abrirFicha(p.id)).addTo(estado.capaRuta);
  });
  pintar();
  mostrarHoja(`
    <h2>${esc(r.nombre)}</h2>
    <p>${esc(r.descripcion)}<br><strong>${(r.distancia_m / 1000).toFixed(1).replace(".", ",")} km · unos ${r.minutos} min a pie</strong></p>
    <ol class="paradas">
      ${r.paradas.map((p, i) => `
        <li><span class="num" style="background:${esc(r.color)}">${i + 1}</span>
          <button data-punto="${esc(p.id)}">${esc(p.titulo_corto || p.titulo)}
            <small>${esc(p.fecha_texto || "Sin fecha")}${p.tramo_m ? ` · ${p.tramo_m} m desde la anterior` : ""}
            ${estado.visitados.has(p.id) ? ' · <span class="visitado">✓ visitado</span>' : ""}</small></button></li>`).join("")}
    </ol>
    <button class="boton boton--claro" id="btn-salir-ruta">Salir de la ruta</button>`, true);
  $("#hoja-contenido").querySelectorAll("[data-punto]").forEach((b) => (b.onclick = () => abrirFicha(b.dataset.punto)));
  $("#btn-salir-ruta").onclick = () => { salirDeRuta(); cerrarHoja(); };
  encuadrar(r.paradas);
}

function salirDeRuta(repintar = true) {
  if (estado.capaRuta) estado.capaRuta.remove();
  estado.capaRuta = null;
  estado.ruta = null;
  $("#btn-rutas").setAttribute("aria-pressed", "false");
  if (repintar) pintar();
}

/* ------------------------------------------------------------------ cerca de mí y geovallas */
function alternarCerca() {
  estado.siguiendo = !estado.siguiendo;
  $("#btn-cerca").setAttribute("aria-pressed", estado.siguiendo);
  if (!estado.siguiendo) {
    if (estado.vigilancia != null) navigator.geolocation.clearWatch(estado.vigilancia);
    estado.vigilancia = null;
    $("#aviso-simulacion").hidden = true;
    if (estado.marcaYo) estado.marcaYo.remove();
    estado.marcaYo = null;
    return;
  }
  if (estado.simular) {
    $("#aviso-simulacion").hidden = false;
    aviso("Toca el mapa para simular dónde estás");
    return;
  }
  if (!navigator.geolocation) { aviso("Este navegador no permite conocer tu ubicación"); return; }
  estado.vigilancia = navigator.geolocation.watchPosition(
    (pos) => nuevaPosicion({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
    (err) => aviso(err.code === 1 ? "Sin permiso de ubicación. Puedes seguir usando el mapa." : "No se pudo obtener tu ubicación"),
    { enableHighAccuracy: true, maximumAge: 10000 }
  );
}

mapa.on("click", (ev) => {
  if (estado.simular && estado.siguiendo) nuevaPosicion({ lat: ev.latlng.lat, lon: ev.latlng.lng });
});

async function nuevaPosicion(pos) {
  const primera = !estado.posicion;
  estado.posicion = pos;
  if (!estado.marcaYo) {
    estado.marcaYo = L.marker([pos.lat, pos.lon], { icon: L.divIcon({ className: "", html: '<div class="yo"></div>', iconSize: [20, 20] }), interactive: false, keyboard: false }).addTo(mapa);
  } else estado.marcaYo.setLatLng([pos.lat, pos.lon]);

  // geovalla: avisar una sola vez de cada punto al que te acercas
  for (const p of estado.puntos) {
    if (distancia(pos, p) <= RADIO_AVISO_M && !estado.avisados.has(p.id)) {
      estado.avisados.add(p.id);
      estado.visitados.add(p.id);
      guardarLocal("visitados", [...estado.visitados]);
      aviso(`Estás junto a: ${p.titulo_corto || p.titulo}`, { texto: "Ver", fn: () => abrirFicha(p.id) });
      if (navigator.vibrate) navigator.vibrate(120);
      break;
    }
  }
  if (primera) {
    try {
      const cerca = await api(`/cercanos?lat=${pos.lat}&lon=${pos.lon}&radio=1500`);
      mostrarHoja(`
        <h2>Cerca de ti</h2>
        ${cerca.length ? `<ol class="paradas">${cerca.slice(0, 6).map((p) => `
          <li><span class="num" style="background:${esc(p.color)}">${p.minutos}′</span>
            <button data-punto="${esc(p.id)}">${esc(p.titulo_corto || p.titulo)}<small>${p.distancia_m} m · ${esc(p.fecha_texto || "sin fecha")}</small></button></li>`).join("")}</ol>`
          : "<p>No hay puntos a menos de 1,5 km. Este mapa es del barrio de Butarque (Villaverde, Madrid).</p>"}
        <p class="fuente">Visitados: ${estado.visitados.size} de ${estado.puntos.length}</p>`, true);
      $("#hoja-contenido").querySelectorAll("[data-punto]").forEach((b) => (b.onclick = () => abrirFicha(b.dataset.punto)));
      mapa.panTo([pos.lat, pos.lon]);
    } catch { aviso("No se pudieron cargar los puntos cercanos"); }
  }
}

/* ------------------------------------------------------------------ lista (alternativa accesible al mapa) */
function pintarLista() {
  const cont = $("#lista");
  cont.innerHTML = estado.capas.filter((c) => estado.activas.has(c.id)).map((c) => {
    const ps = estado.puntos.filter((p) => p.capa_id === c.id && visible(p));
    if (!ps.length) return "";
    return `<h2><span class="chip__punto" style="background:${esc(c.color)}"></span>${esc(c.nombre)}</h2><ul>${ps.map((p) => `
      <li><button data-punto="${esc(p.id)}"><span class="fecha">${esc(p.fecha_texto || "sin fecha")}</span>
        <span>${esc(p.titulo)}${p.tiene_audio ? " 🔊" : ""}${p.tiene_juego ? " 🎮" : ""}</span></button></li>`).join("")}</ul>`;
  }).join("") || "<p>No hay puntos con estos filtros.</p>";
  cont.querySelectorAll("[data-punto]").forEach((b) => (b.onclick = () => abrirFicha(b.dataset.punto)));
}

function alternarLista() {
  const lista = $("#lista"), b = $("#btn-lista");
  lista.hidden = !lista.hidden;
  b.setAttribute("aria-pressed", !lista.hidden);
  b.textContent = lista.hidden ? "☰" : "🗺";
  b.setAttribute("aria-label", lista.hidden ? "Ver los puntos en forma de lista" : "Volver al mapa");
  if (!lista.hidden) pintarLista();
}

/* ------------------------------------------------------------------ navegación y arranque */
function rutaDeUrl() {
  const id = new URLSearchParams(location.search).get("p");
  return id && /^[a-z0-9-]+$/.test(id) ? id : null;
}

window.addEventListener("popstate", () => {
  const id = rutaDeUrl();
  id ? abrirFicha(id, false) : cerrarHoja(false);
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#hoja").hidden) cerrarHoja(); });
$("#hoja-asa").onclick = () => cerrarHoja();
$("#btn-rutas").onclick = () => (estado.ruta ? elegirRuta(estado.ruta.id) : abrirRutas());
$("#btn-cerca").onclick = alternarCerca;
$("#btn-lista").onclick = alternarLista;
$("#btn-reproducir").onclick = reproducir;

function estadoRed() { $("#sin-red").hidden = navigator.onLine; }
window.addEventListener("online", estadoRed);
window.addEventListener("offline", estadoRed);

async function arrancar() {
  ajustarAltoBarra();
  estadoRed();
  try {
    [estado.capas, estado.puntos] = await Promise.all([api("/capas"), api("/puntos")]);
  } catch {
    aviso("No se pudieron cargar los datos del mapa");
    return;
  }
  estado.capas.forEach((c) => estado.activas.add(c.id));
  estado.puntos.forEach(crearMarcador);
  pintarCapas();
  ajustarAltoBarra();
  prepararTiempo();
  encuadrar(estado.puntos);
  const id = rutaDeUrl();
  if (id) abrirFicha(id, false);
  if (estado.simular) {
    aviso("Modo prueba activo: pulsa «Cerca de mí» y toca el mapa");
    window.__pruebas = { mapa, estado };        // solo en modo prueba: para las pruebas automáticas
  }
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}
arrancar();
