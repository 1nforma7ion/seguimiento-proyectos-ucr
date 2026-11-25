// Ruteo por hash, carga de datos y eventos.
import {
  buscarEnTodo, conNovedad, estaDesactualizado, filtrar, novedadesRecientes, ordenarPor, porLegislador, proximosACaducar, resumen,
} from "./logica.js";
import * as V from "./vistas.js";

const app = document.getElementById("app");
const datos = { indice: null, novedades: [], estado: null, glosario: {} };
const vista = { pestania: "fondo", tarjeta: null, texto: "", orden: "recientes", comision: "", legislador: "", limite: 30 };
let ultimaLista = "#/elegir";
let ultimaListaNombre = "Legisladores";
let textoElegir = "";

const hoyAR = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Argentina/Cordoba" }).format(new Date());
const guardar = (slug) => { try { localStorage.setItem("leg", slug); } catch { /* almacenamiento bloqueado */ } };
// "Para atender" arranca cerrado; si alguien lo abre, queda abierto en sus próximas visitas.
const atenderAbierto = () => { try { return localStorage.getItem("atender") === "1"; } catch { return false; } };
const guardarAtender = (v) => { try { localStorage.setItem("atender", v ? "1" : "0"); } catch { /* almacenamiento bloqueado */ } };
const guardado = () => { try { return localStorage.getItem("leg"); } catch { return null; } };

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

const legsPorSlug = () => Object.fromEntries(datos.indice.legisladores.map((l) => [l.slug, l]));
const expedientes = (numeros) => numeros.map((n) => ({ numero: n, ...datos.indice.expedientes[n] })).filter((e) => e.estado);

function pie() {
  const est = datos.estado;
  const fecha = est?.ultima_actualizacion_ok
    ? new Intl.DateTimeFormat("es-AR", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "America/Argentina/Cordoba" })
      .format(new Date(est.ultima_actualizacion_ok))
    : null;
  document.getElementById("pie-datos").textContent = fecha ? `Datos actualizados el ${fecha}.` : "Todavía no hay una actualización completa.";
  const viejo = estaDesactualizado(est, hoyAR(), datos.indice.ajustes.dias_desactualizado);
  const cargando = (est?.advertencias || []).some((a) => a.startsWith("Carga inicial en curso"));
  document.getElementById("aviso").hidden = !viejo;
  document.getElementById("aviso-texto").textContent = cargando
    ? "Carga inicial en curso: todavía faltan proyectos de algunos legisladores. Se completa sola en las próximas actualizaciones."
    : fecha ? `Los datos están desactualizados desde el ${fecha}. Pueden faltar movimientos recientes.`
      : "Los datos todavía no terminaron de cargarse por primera vez.";
}

function cabecera(seccion) {
  const slug = guardado();
  const leg = datos.indice.legisladores.find((l) => l.slug === slug);
  const mios = document.querySelector('[data-menu="mios"]');
  mios.href = leg ? `#/leg/${leg.slug}` : "#/elegir";
  document.querySelectorAll("[data-menu]").forEach((a) => {
    if (a.dataset.menu === seccion) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  const quien = document.getElementById("quien");
  quien.hidden = !leg;
  if (leg) quien.innerHTML = `${V.avatar(leg, "m")}<span class="q-txt">${V.esc(leg.nombre)}<small>Cambiar de legislador</small></span>`;
}

function sinEventos() { app.onclick = app.oninput = app.onchange = app.onsubmit = null; }

// --- pantallas con lista -------------------------------------------------------
function pantallaLista({ arriba, numeros, propio = null, conSelectores = false }) {
  const hoy = hoyAR();
  const aj = datos.indice.ajustes;
  const legs = legsPorSlug();
  const todos = expedientes(numeros);
  const porNumero = Object.fromEntries(todos.map((e) => [e.numero, e]));
  const ctx = { hoy, aj, legs, propio, nov: conNovedad(datos.novedades, hoy) };

  const dibujar = () => {
    const base = todos.filter((e) => (!vista.comision || (e.comisiones || []).includes(vista.comision))
      && (!vista.legislador || e.autores_bloque.includes(vista.legislador)));
    const r = { ...resumen(base, datos.novedades, hoy, aj), dias: aj.dias_por_caducar };
    const filtro = { ...vista, tarjeta: vista.tarjeta ?? (vista.pestania === "caducados" ? "caducados" : null) };
    let visibles = filtrar(base, filtro, datos.novedades, hoy, aj);
    visibles = vista.tarjeta === "porCaducar" ? proximosACaducar(visibles, hoy, aj) : ordenarPor(visibles, vista.orden, datos.novedades, hoy);
    const numerosBase = new Set(base.map((e) => e.numero));
    const atender = V.paraAtender(proximosACaducar(base, hoy, aj),
      novedadesRecientes(datos.novedades.filter((n) => numerosBase.has(n.numero)), hoy), porNumero, hoy, atenderAbierto());
    document.getElementById("indicadores").innerHTML = V.indicadores(r, vista.tarjeta);
    document.getElementById("atender").innerHTML = atender;
    document.querySelector("[data-atender]")?.addEventListener("toggle", (ev) => guardarAtender(ev.target.open));
    document.getElementById("zona-lista").innerHTML = V.herramientas(vista, base, visibles.length, datos.glosario)
      + V.lista(visibles, ctx, vista.limite);
  };

  const legsOrden = [...datos.indice.legisladores].sort((a, b) => a.nombre.split(" ").at(-1).localeCompare(b.nombre.split(" ").at(-1), "es"));
  const comisiones = [...new Set(todos.flatMap((e) => e.comisiones || []))].sort((a, b) => a.localeCompare(b, "es"));
  const opt = (v, t, sel) => `<option value="${V.esc(v)}"${sel === v ? " selected" : ""}>${V.esc(t)}</option>`;
  const selectores = conSelectores ? `<div class="selectores">
      <label>Legislador o legisladora<select class="campo" name="legislador">${opt("", "Todo el bloque", vista.legislador)}${legsOrden.map((l) => opt(l.slug, l.nombre, vista.legislador)).join("")}</select></label>
      <label>Comisión<select class="campo" name="comision">${opt("", "Todas las comisiones", vista.comision)}${comisiones.map((c) => opt(c, c, vista.comision)).join("")}</select></label>
    </div>` : "";

  app.innerHTML = `<div class="banda"><div class="cont">${arriba}<div id="indicadores"></div></div></div>
    <div class="cont"><div id="atender"></div>${conSelectores ? '<div id="tabla-bloque" class="seccion"></div>' : ""}
      <section class="seccion" aria-labelledby="t-todos"><div class="titulo-sec"><h2 id="t-todos">${propio ? "Todos sus proyectos" : "Proyectos del bloque"}</h2></div>
        ${selectores}<div id="zona-lista"></div></section></div>`;
  if (conSelectores) {
    document.getElementById("tabla-bloque").innerHTML = `<div class="titulo-sec"><h2>Por legislador</h2><span class="aux">Tocá un nombre para ver su panel</span></div>`
      + V.tablaBloque(porLegislador(datos.indice, hoy, aj));
  }
  dibujar();

  app.onclick = (ev) => {
    const fila = ev.target.closest("tr[data-leg]");
    if (fila && !ev.target.closest("a")) { location.hash = `#/leg/${fila.dataset.leg}`; return; }
    const t = ev.target.closest("button");
    if (!t || !app.contains(t)) return;
    if (t.dataset.tarjeta) {
      vista.tarjeta = vista.tarjeta === t.dataset.tarjeta ? null : t.dataset.tarjeta;
      if (t.classList.contains("enlace")) vista.tarjeta = t.dataset.tarjeta;
    } else if (t.dataset.pestania) { vista.pestania = t.dataset.pestania; vista.tarjeta = null; }
    else if ("quitar" in t.dataset) vista.tarjeta = null;
    else if ("mas" in t.dataset) vista.limite += 30;
    else return;
    if (!("mas" in t.dataset)) vista.limite = 30;
    const foco = t.dataset.pestania ? `[data-pestania="${t.dataset.pestania}"]` : t.dataset.tarjeta ? `.ind[data-tarjeta="${t.dataset.tarjeta}"]` : null;
    dibujar();
    if (foco) app.querySelector(foco)?.focus();
    if (t.classList.contains("enlace") && t.dataset.tarjeta) document.getElementById("zona-lista").scrollIntoView({ behavior: "smooth" });
  };
  app.oninput = (ev) => {
    if (!("buscar" in ev.target.dataset)) return;
    vista.texto = ev.target.value;
    vista.limite = 30;
    const pos = ev.target.selectionStart;
    dibujar();
    const input = app.querySelector("[data-buscar]");
    input.focus();
    input.setSelectionRange(pos, pos);
  };
  app.onchange = (ev) => {
    const s = ev.target;
    if ("orden" in s.dataset) vista.orden = s.value;
    else if (s.name === "legislador" || s.name === "comision") vista[s.name] = s.value;
    else return;
    vista.limite = 30;
    dibujar();
  };
}

function pantallaLegislador(slug) {
  const leg = datos.indice.legisladores.find((l) => l.slug === slug);
  if (!leg) return pantallaElegir();
  guardar(slug);
  ultimaListaNombre = leg.nombre;
  pantallaLista({ arriba: V.bandaLegislador(leg, leg.expedientes.length), numeros: leg.expedientes, propio: slug });
  document.title = `${leg.nombre} · Seguimiento legislativo`;
}

function pantallaBloque() {
  const todos = Object.keys(datos.indice.expedientes);
  ultimaListaNombre = "Todo el bloque";
  pantallaLista({
    arriba: `<h1>Todo el bloque</h1><p class="bajada">${todos.length.toLocaleString("es-AR")} proyectos firmados por al menos un integrante del bloque UCR en este mandato.</p>`,
    numeros: todos, conSelectores: true,
  });
}

function pantallaElegir() {
  const stats = Object.fromEntries(porLegislador(datos.indice, hoyAR(), datos.indice.ajustes).map((s) => [s.slug, s]));
  const legs = [...datos.indice.legisladores].sort((a, b) => a.nombre.split(" ").at(-1).localeCompare(b.nombre.split(" ").at(-1), "es"));
  app.innerHTML = `${V.bandaElegir(textoElegir)}<div class="cont seccion" id="grilla">${V.elegir(legs, stats, textoElegir)}</div>`;
  sinEventos();
  app.oninput = (ev) => {
    if (!("buscarLeg" in ev.target.dataset)) return;
    textoElegir = ev.target.value;
    document.getElementById("grilla").innerHTML = V.elegir(legs, stats, textoElegir);
  };
}

function pantallaBuscar(texto) {
  const hoy = hoyAR();
  const legs = legsPorSlug();
  const todos = expedientes(Object.keys(datos.indice.expedientes));
  const ctx = { hoy, aj: datos.indice.ajustes, legs, propio: null, nov: conNovedad(datos.novedades, hoy) };
  let limite = 30;
  let actual = texto;
  ultimaListaNombre = "Búsqueda";
  app.innerHTML = `${V.bandaBuscar(texto)}<div class="cont seccion" id="resultados"></div>`;
  const dibujar = () => {
    document.getElementById("resultados").innerHTML = V.resultadosBusqueda(actual, buscarEnTodo(todos, actual, legs), ctx, limite);
  };
  dibujar();
  sinEventos();
  let espera;
  app.oninput = (ev) => {
    if (!("buscarTodo" in ev.target.dataset)) return;
    actual = ev.target.value;
    limite = 30;
    clearTimeout(espera);
    espera = setTimeout(() => {
      // Se guarda la búsqueda en la dirección para que "volver" desde un proyecto la recupere.
      ultimaLista = actual.trim() ? `#/buscar/${encodeURIComponent(actual.trim())}` : "#/buscar";
      history.replaceState(null, "", ultimaLista);
      dibujar();
    }, 150);
  };
  app.onsubmit = (ev) => { ev.preventDefault(); document.activeElement?.blur(); };
  app.onclick = (ev) => {
    if (!ev.target.closest("[data-mas]")) return;
    limite += 30;
    dibujar();
  };
  const input = document.getElementById("buscar-todo");
  if (!texto && matchMedia("(hover: hover)").matches) input.focus({ preventScroll: true });
}

async function pantallaExpediente(id) {
  sinEventos();
  app.innerHTML = '<div class="cont"><p class="cargando">Cargando el proyecto…</p></div>';
  try {
    const d = await cargarJSON(`data/expedientes/${encodeURIComponent(id)}.json`);
    app.innerHTML = V.ficha(d, {
      hoy: hoyAR(), aj: datos.indice.ajustes, glosario: datos.glosario, legsLista: datos.indice.legisladores,
      legs: legsPorSlug(), volver: ultimaLista, volverNombre: ultimaListaNombre,
    });
    document.title = `${d.numero} · Seguimiento legislativo`;
  } catch {
    app.innerHTML = `<div class="cont"><p class="vacio">No encontramos ese proyecto. <a href="${V.esc(ultimaLista)}">Volver a la lista</a></p></div>`;
  }
}

// --- ruteo ---------------------------------------------------------------------
function reiniciarVista() {
  Object.assign(vista, { pestania: "fondo", tarjeta: null, texto: "", orden: "recientes", comision: "", legislador: "", limite: 30 });
}

async function rutear() {
  const params = new URLSearchParams(location.search);
  if (params.get("leg") && !location.hash) { location.replace(`#/leg/${params.get("leg")}`); return; }
  const hash = location.hash || "#/";
  const [, seccion, arg] = hash.split("/");
  document.title = "Seguimiento legislativo · Bloque UCR";
  // Al volver de una ficha a la misma lista se conservan los filtros.
  if (seccion !== "exp" && hash !== ultimaLista) reiniciarVista();
  if (seccion === "leg" && arg) { ultimaLista = hash; cabecera("mios"); pantallaLegislador(decodeURIComponent(arg)); cabecera("mios"); }
  else if (seccion === "bloque") { ultimaLista = hash; cabecera("bloque"); pantallaBloque(); }
  else if (seccion === "exp" && arg) { cabecera(ultimaLista.startsWith("#/bloque") ? "bloque" : ultimaLista.startsWith("#/buscar") ? "buscar" : "mios"); await pantallaExpediente(decodeURIComponent(arg)); }
  else if (seccion === "buscar") {
    ultimaLista = hash; cabecera("buscar"); pantallaBuscar(arg ? decodeURIComponent(hash.split("/").slice(2).join("/")) : "");
    window.scrollTo(0, 0);
    return;
  }
  else if (seccion === "como-funciona") { sinEventos(); cabecera("como"); app.innerHTML = V.comoFunciona(datos.glosario, datos.indice.ajustes); }
  else if (seccion === "elegir") { ultimaLista = hash; ultimaListaNombre = "Legisladores"; cabecera("mios"); pantallaElegir(); }
  else {
    const g = guardado();
    if (g && datos.indice.legisladores.some((l) => l.slug === g)) { location.replace(`#/leg/${g}`); return; }
    location.replace("#/elegir");
    return;
  }
  window.scrollTo(0, 0);
  app.focus({ preventScroll: true });
}

async function iniciar() {
  try {
    [datos.indice, datos.novedades, datos.estado, datos.glosario] = await Promise.all([
      cargarJSON("data/indice.json"), cargarJSON("data/novedades.json", []),
      cargarJSON("data/estado.json", null), cargarJSON("data/glosario.json", {}),
    ]);
  } catch {
    app.innerHTML = '<div class="cont"><p class="vacio">Todavía no hay datos publicados. La primera actualización puede tardar unas horas.</p></div>';
    return;
  }
  pie();
  window.addEventListener("hashchange", rutear);
  rutear();
}

// --- instalar como app ----------------------------------------------------------
function instalable() {
  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
    navigator.serviceWorker.register("sw.js").catch(() => { /* sin modo sin conexión */ });
  }
  const boton = document.getElementById("instalar");
  const ayuda = document.getElementById("instalar-ayuda");
  const yaInstalada = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  if (!boton || yaInstalada) return;
  let pedido = null;
  window.addEventListener("beforeinstallprompt", (ev) => { ev.preventDefault(); pedido = ev; });
  window.addEventListener("appinstalled", () => { boton.hidden = true; ayuda.hidden = true; });
  boton.hidden = false;
  boton.onclick = async () => {
    if (pedido) {
      pedido.prompt();
      const { outcome } = await pedido.userChoice;
      if (outcome === "accepted") boton.hidden = true;
      pedido = null;
      return;
    }
    const iphone = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    ayuda.textContent = iphone
      ? "En el iPhone: abrí este sitio en Safari, tocá el botón Compartir (el cuadrado con la flecha hacia arriba) y elegí “Agregar a inicio”."
      : "Abrí el menú del navegador (los tres puntos ⋮) y elegí “Instalar aplicación” o “Agregar a la pantalla principal”.";
    ayuda.hidden = !ayuda.hidden;
    boton.setAttribute("aria-expanded", String(!ayuda.hidden));
  };
}

instalable();
iniciar();
