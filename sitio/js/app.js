// Ruteo por hash, carga de datos y eventos.
import { estaDesactualizado, filtrar, normalizar, ordenar, resumen } from "./logica.js";
import * as V from "./vistas.js";

const app = document.getElementById("app");
const datos = { indice: null, novedades: [], estado: null, glosario: {} };
const vista = { pestania: "fondo", tarjeta: null, texto: "", comision: "", legislador: "", limite: 30 };
let ultimaLista = "#/";

const hoyAR = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Argentina/Cordoba" }).format(new Date());

async function cargarJSON(ruta, defecto) {
  try {
    const r = await fetch(ruta, { cache: "no-cache" });
    if (!r.ok) throw new Error(r.status);
    return await r.json();
  } catch {
    if (defecto !== undefined) return defecto;
    throw new Error(`No se pudo cargar ${ruta}`);
  }
}

function expedientes(numeros) {
  return numeros.map((n) => ({ numero: n, ...datos.indice.expedientes[n] })).filter((e) => e.estado);
}

function pie() {
  const est = datos.estado;
  const fecha = est?.ultima_actualizacion_ok
    ? new Intl.DateTimeFormat("es-AR", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "America/Argentina/Cordoba" })
      .format(new Date(est.ultima_actualizacion_ok))
    : null;
  document.getElementById("pie-datos").textContent = fecha ? `Datos actualizados el ${fecha}.` : "Todavía no hay una actualización completa.";
  const aviso = document.getElementById("aviso");
  const viejo = estaDesactualizado(est, hoyAR(), datos.indice.ajustes.dias_desactualizado);
  aviso.hidden = !viejo;
  if (viejo) aviso.textContent = fecha
    ? `Los datos están desactualizados desde el ${fecha}. Pueden faltar movimientos recientes.`
    : "Los datos todavía no terminaron de cargarse por primera vez.";
}

function marcarMenu(hash) {
  document.querySelectorAll(".menu a").forEach((a) => {
    if (hash.startsWith(a.getAttribute("href"))) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
}

// --- pantallas con lista -----------------------------------------------------
function pantallaLista({ titularHTML, numeros, selectores = "", mostrarAutores = false }) {
  const hoy = hoyAR();
  const aj = datos.indice.ajustes;
  const nombres = Object.fromEntries(datos.indice.legisladores.map((l) => [l.slug, l.nombre]));
  const todos = expedientes(numeros);
  const ctx = { hoy, aj, novedades: datos.novedades, nombres, mostrarAutores };

  const dibujar = () => {
    const base = todos.filter((e) => (!vista.comision || (e.comisiones || []).includes(vista.comision))
      && (!vista.legislador || e.autores_bloque.includes(vista.legislador)));
    const r = resumen(base, datos.novedades, hoy, aj);
    let visibles = ordenar(filtrar(base, vista, datos.novedades, hoy, aj), datos.novedades, hoy);
    if (vista.tarjeta === "porCaducar") {  // lo que vence antes, primero
      visibles = visibles.sort((a, b) => a.estado.caduca_el.localeCompare(b.estado.caduca_el));
    }
    const cad = vista.tarjeta === "caducados" ? V.explicaCaducados(datos.glosario) : "";
    const cantidadCad = base.filter((e) => ["caduco", "archivado"].includes(e.estado.resultado)).length;
    const linkCad = vista.tarjeta !== "caducados" && cantidadCad
      ? `<p class="mas"><a href="" data-caducados>Ver ${cantidadCad} caducados o archivados</a></p>` : "";
    document.getElementById("zona-lista").innerHTML =
      V.botonesResumen(r, vista.tarjeta) + V.controles(vista, visibles.length) + cad + V.lista(visibles, ctx, vista.limite) + linkCad;
  };

  app.innerHTML = `${titularHTML}${selectores}<div id="zona-lista"></div>`;
  dibujar();

  app.onclick = (ev) => {
    const t = ev.target.closest("button, a[data-caducados]");
    if (!t || !app.contains(t)) return;
    if (t.dataset.tarjeta) vista.tarjeta = vista.tarjeta === t.dataset.tarjeta ? null : t.dataset.tarjeta;
    else if (t.dataset.pestania) { vista.pestania = t.dataset.pestania; vista.tarjeta = null; }
    else if ("quitar" in t.dataset) vista.tarjeta = null;
    else if ("mas" in t.dataset) vista.limite += 30;
    else if ("caducados" in t.dataset) { ev.preventDefault(); vista.tarjeta = "caducados"; }
    else return;
    if (!("mas" in t.dataset)) vista.limite = 30;
    const foco = t.dataset.tarjeta ? `[data-tarjeta="${t.dataset.tarjeta}"]` : t.dataset.pestania ? `[data-pestania="${t.dataset.pestania}"]` : null;
    dibujar();
    if (foco) app.querySelector(foco)?.focus();
  };
  app.oninput = (ev) => {
    if ("buscar" in ev.target.dataset) {
      vista.texto = ev.target.value;
      vista.limite = 30;
      const pos = ev.target.selectionStart;
      dibujar();
      const input = app.querySelector("[data-buscar]");
      input.focus();
      input.setSelectionRange(pos, pos);
    }
  };
  app.onchange = (ev) => {
    const s = ev.target;
    if (s.name === "legislador" || s.name === "comision") {
      vista[s.name] = s.value;
      vista.limite = 30;
      dibujar();
    }
  };
}

function reiniciarVista() {
  Object.assign(vista, { pestania: "fondo", tarjeta: null, texto: "", comision: "", legislador: "", limite: 30 });
}

function pantallaLegislador(slug) {
  const leg = datos.indice.legisladores.find((l) => l.slug === slug);
  if (!leg) return pantallaElegir();
  localStorage.setItem("leg", slug);
  pantallaLista({ titularHTML: V.titular(leg, leg.expedientes.length), numeros: leg.expedientes });
}

function pantallaBloque() {
  const todos = Object.keys(datos.indice.expedientes);
  const comisiones = [...new Set(todos.flatMap((n) => datos.indice.expedientes[n].comisiones || []))]
    .sort((a, b) => normalizar(a).localeCompare(normalizar(b)));
  const opt = (v, t, sel) => `<option value="${V.esc(v)}"${sel === v ? " selected" : ""}>${V.esc(t)}</option>`;
  const selectores = `<div class="selectores">
    <label class="selector">Legislador o legisladora<select name="legislador">${opt("", "Todo el bloque", vista.legislador)}${datos.indice.legisladores.map((l) => opt(l.slug, l.nombre, vista.legislador)).join("")}</select></label>
    <label class="selector">Comisión<select name="comision">${opt("", "Todas las comisiones", vista.comision)}${comisiones.map((c) => opt(c, c, vista.comision)).join("")}</select></label>
  </div>`;
  pantallaLista({
    titularHTML: `<div class="titular"><h1>Todo el bloque</h1><p class="titular-sub">${todos.length} proyectos firmados por al menos un integrante del bloque UCR en este mandato.</p></div>`,
    numeros: todos, selectores, mostrarAutores: true,
  });
}

function pantallaElegir() {
  app.onclick = app.oninput = app.onchange = null;
  app.innerHTML = V.elegir(datos.indice.legisladores);
}

async function pantallaExpediente(id) {
  app.onclick = app.oninput = app.onchange = null;
  app.innerHTML = '<p class="cargando">Cargando el proyecto…</p>';
  try {
    const d = await cargarJSON(`data/expedientes/${encodeURIComponent(id)}.json`);
    const legs = datos.indice.legisladores;
    const nombres = new Set(legs.map((l) => normalizar(l.nombre)));
    const propios = (a) => {
      const [ap, nom] = a.split(",").map((x) => normalizar(x));
      return nombres.has(`${nom} ${ap}`);
    };
    app.innerHTML = V.ficha(d, { hoy: hoyAR(), aj: datos.indice.ajustes, glosario: datos.glosario, propios, volver: ultimaLista });
    document.title = `${d.numero} · Proyectos del bloque UCR`;
  } catch {
    app.innerHTML = `<p class="vacio">No encontramos ese proyecto. <a href="${V.esc(ultimaLista)}">Volver a la lista</a></p>`;
  }
}

// --- ruteo -------------------------------------------------------------------
async function rutear() {
  const params = new URLSearchParams(location.search);
  if (params.get("leg") && !location.hash) { location.replace(`#/leg/${params.get("leg")}`); return; }
  const hash = location.hash || "#/";
  const [, seccion, arg] = hash.split("/");
  marcarMenu(hash);
  document.title = "Proyectos del bloque UCR";
  if (seccion !== "exp") { reiniciarVista(); }
  if (seccion === "leg" && arg) { ultimaLista = hash; pantallaLegislador(decodeURIComponent(arg)); }
  else if (seccion === "bloque") { ultimaLista = hash; pantallaBloque(); }
  else if (seccion === "exp" && arg) await pantallaExpediente(decodeURIComponent(arg));
  else if (seccion === "como-funciona") { app.onclick = app.oninput = app.onchange = null; app.innerHTML = V.comoFunciona(datos.glosario); }
  else if (seccion === "elegir") pantallaElegir();
  else {
    const guardado = localStorage.getItem("leg");
    if (guardado && datos.indice.legisladores.some((l) => l.slug === guardado)) { location.replace(`#/leg/${guardado}`); return; }
    pantallaElegir();
  }
  if (seccion !== "exp") window.scrollTo(0, 0);
  app.focus({ preventScroll: true });
}

async function iniciar() {
  try {
    [datos.indice, datos.novedades, datos.estado, datos.glosario] = await Promise.all([
      cargarJSON("data/indice.json"), cargarJSON("data/novedades.json", []),
      cargarJSON("data/estado.json", null), cargarJSON("data/glosario.json", {}),
    ]);
  } catch {
    app.innerHTML = '<p class="vacio">Todavía no hay datos publicados. La primera actualización puede tardar unas horas.</p>';
    return;
  }
  pie();
  window.addEventListener("hashchange", rutear);
  rutear();
}

iniciar();
