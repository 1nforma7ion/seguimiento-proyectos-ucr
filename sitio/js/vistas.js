// Arma el HTML de cada pantalla. Todo texto que viene de los datos pasa por esc().
import { conNovedad, diasHasta, fechaRelativa } from "./logica.js";

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const TIPO = { ley: "Ley", resolucion: "Resolución", declaracion: "Declaración", otros: "Otro" };
const RESULTADO = { aprobado: "Aprobado", caduco: "Caducó", archivado: "Archivado", rechazado: "No aprobado" };
const ESTACIONES = ["Presentado", "En comisión", "Con dictamen"];
const fechaLarga = (iso) => new Intl.DateTimeFormat("es-AR", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" })
  .format(new Date(`${iso.slice(0, 10)}T12:00:00Z`));
export const idArchivo = (numero) => numero.replaceAll("/", "-");

export function que(glosario, clave) {
  const g = glosario[clave];
  if (!g) return "";
  return `<details class="que"><summary>¿Qué significa?</summary><p>${esc(g.texto)}</p></details>`;
}

function claseRuta(e, hoy, aj) {
  const r = e.estado.resultado;
  if (r === "aprobado") return "aprobado";
  if (r) return "muerto";
  const c = e.estado.caduca_el;
  if (c && diasHasta(c, hoy) <= aj.dias_por_caducar) return "urgente";
  return "";
}

export function ruta(e, hoy, aj) {
  const etapa = e.estado.etapa;
  const final = RESULTADO[e.estado.resultado] ?? "Votación";
  const nombres = [...ESTACIONES, final];
  const items = nombres.map((n, i) => {
    const paso = i + 1;
    const clase = paso < etapa ? "hecho" : paso === etapa ? "actual" : "";
    const actual = paso === etapa ? ' aria-current="step"' : "";
    return `<li class="${clase}"${actual}>${esc(n)}</li>`;
  }).join("");
  const resumen = `Etapa ${etapa} de 4: ${etapa === 4 ? final : ESTACIONES[etapa - 1]}`;
  return `<ol class="ruta ${claseRuta(e, hoy, aj)}" aria-label="${esc(resumen)}">${items}</ol>`;
}

function lineaCaducidad(e, hoy, aj) {
  const c = e.estado.caduca_el;
  if (!c || e.estado.resultado) return "";
  const d = diasHasta(c, hoy);
  if (d < 0) return `<p class="movimiento">Debería haber caducado el ${esc(fechaLarga(c))}; el portal todavía no lo registra.</p>`;
  if (d <= aj.dias_por_caducar) return `<p class="caduca">Caduca en ${d} ${d === 1 ? "día" : "días"} (aprox. ${esc(fechaLarga(c))})</p>`;
  return `<p class="movimiento">Caduca aprox. el ${esc(fechaLarga(c))}</p>`;
}

export function filaProyecto(e, ctx) {
  const { hoy, aj, novedades, nombres, mostrarAutores } = ctx;
  const nov = conNovedad(novedades, hoy).has(e.numero);
  const um = e.estado.ultimo_movimiento;
  const autores = mostrarAutores ? `<span>${esc(e.autores_bloque.map((s) => nombres[s] ?? s).join(", "))}</span>` : "";
  return `<li class="proyecto"><a href="#/exp/${esc(idArchivo(e.numero))}">
    <span class="cabeza"><span class="tipo">${TIPO[e.tipo]}</span><span>${esc(e.numero)}</span>${autores}${nov ? '<span class="nuevo">Con novedades</span>' : ""}</span>
    <span class="titulo">${esc(e.titulo)}</span>
    ${ruta(e, hoy, aj)}
    ${um ? `<p class="movimiento">Último movimiento ${esc(fechaRelativa(um.fecha, hoy))}: ${esc(um.texto)}</p>` : ""}
    ${lineaCaducidad(e, hoy, aj)}
  </a></li>`;
}

export function botonesResumen(r, activa) {
  const b = (clave, n, texto, urgente = false) =>
    `<button type="button" data-tarjeta="${clave}" aria-pressed="${activa === clave}" class="${urgente && n ? "urgente" : ""}">
      <span class="n">${n}</span><span class="t">${texto}</span></button>`;
  return `<div class="resumen" role="group" aria-label="Filtrar por situación">
    ${b("novedades", r.novedades, "con novedades esta semana")}
    ${b("porCaducar", r.porCaducar, "por caducar en 60 días", true)}
    ${b("enComision", r.enComision, "en estudio en comisión")}
    ${b("aprobados", r.aprobadosAnio, "aprobados este año")}
  </div>`;
}

const NOMBRE_TARJETA = {
  novedades: "con novedades en los últimos 7 días",
  porCaducar: "que caducan en los próximos 60 días",
  enComision: "en estudio en comisión",
  aprobados: "aprobados este año",
  caducados: "caducados o archivados",
};

export function controles(estado, cuenta) {
  const tab = (clave, texto) =>
    `<button type="button" role="tab" data-pestania="${clave}" aria-selected="${!estado.tarjeta && estado.pestania === clave}">${texto}</button>`;
  const filtro = estado.tarjeta
    ? `<div class="filtro-activo"><span>Mostrando ${cuenta} ${cuenta === 1 ? "proyecto" : "proyectos"} ${NOMBRE_TARJETA[estado.tarjeta]}.</span><button type="button" data-quitar>Ver todos</button></div>`
    : "";
  return `<div class="controles">
    <div class="pestanias" role="tablist" aria-label="Tipo de proyecto">
      ${tab("fondo", "Leyes y resoluciones")}${tab("declaraciones", "Declaraciones")}${tab("otros", "Otros")}
    </div>
    <label class="buscar"><span class="saltar">Buscar</span>
      <input type="search" placeholder="Buscar por tema o número" value="${esc(estado.texto)}" data-buscar></label>
  </div>${filtro}`;
}

export function explicaCaducados(glosario) {
  return `<p class="explica">${esc(glosario.caducidad.texto)} ${esc(glosario.rehabilitacion.texto)}</p>`;
}

export function lista(exps, ctx, limite) {
  if (!exps.length) return '<p class="vacio">No hay proyectos que coincidan. Probá con otra pestaña o borrá la búsqueda.</p>';
  const filas = exps.slice(0, limite).map((e) => filaProyecto(e, ctx)).join("");
  const resto = exps.length - limite;
  return `<ul class="lista">${filas}</ul>${resto > 0
    ? `<p class="mas"><button type="button" data-mas>Mostrar ${Math.min(resto, 30)} más (quedan ${resto})</button></p>` : ""}`;
}

export function elegir(legisladores) {
  const items = [...legisladores].sort((a, b) => a.nombre.split(" ").at(-1).localeCompare(b.nombre.split(" ").at(-1), "es"))
    .map((l) => `<li><a href="#/leg/${esc(l.slug)}"><span class="nomina-nombre">${esc(l.nombre)}${l.departamental ? '<span class="depto">Legislador/a departamental</span>' : ""}</span>
      <span class="nomina-cant">${l.expedientes.length} proyectos</span></a></li>`).join("");
  return `<h1>¿De quién querés ver los proyectos?</h1>
    <p class="intro">Elegí un legislador o legisladora del bloque. La próxima vez que entres desde este dispositivo vas a ir directo a sus proyectos.</p>
    <ul class="nomina">${items}</ul>`;
}

export function titular(leg, cantidad) {
  return `<div class="titular"><a class="volver" href="#/elegir">Cambiar de legislador</a>
    <h1>${esc(leg.nombre)}</h1>
    <p class="titular-sub">Firmó ${cantidad} ${cantidad === 1 ? "proyecto" : "proyectos"} en este mandato, como autor o coautor.</p></div>`;
}

export function ficha(d, ctx) {
  const { hoy, aj, glosario, propios } = ctx;
  const e = { ...d, estado: d.estado };
  const r = d.estado.resultado;
  const etiqueta = r ? `<span class="resultado ${r === "aprobado" ? "aprobado" : "muerto"}">${RESULTADO[r]}</span>` : "";
  // "Sigue el trámite normal" no le dice nada nuevo a quien lee: se omite del recorrido.
  const pasos = d.linea_tiempo.filter((t) => t.texto !== "Sigue el trámite normal");
  const cuando = (t) => [t.fecha && fechaLarga(t.fecha), t.detalle].filter(Boolean).join(", ");
  const tiempo = pasos.map((t) => `<li>${cuando(t) ? `<span class="cuando">${esc(cuando(t))}</span><br>` : ""}${esc(t.texto)}</li>`).join("");
  const autores = d.autores.map((a) => `<li class="${propios(a) ? "propio" : ""}">${esc(a)}</li>`).join("");
  const comisiones = d.comisiones.length
    ? `<ul class="personas">${d.comisiones.map((c, i) => `<li${i === 0 ? ' class="propio"' : ""}>${esc(c)}${i === 0 && d.comisiones.length > 1 ? " (principal)" : ""}</li>`).join("")}</ul>`
    : "<p>Todavía no se giró a ninguna comisión.</p>";
  const docs = d.documentos.length
    ? `<ul>${d.documentos.map((x) => `<li>${esc(x.seccion)}: ${x.url ? `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.nombre)}</a>` : `${esc(x.nombre)} (se ve en el portal oficial)`}</li>`).join("")}</ul>`
    : "<p>Todavía no hay despachos, actas ni texto aprobado.</p>";
  const tipoGlosario = { ley: "ley", resolucion: "resolucion", declaracion: "declaracion" }[d.tipo];
  return `<article class="ficha">
    <div class="titular"><a class="volver" href="${esc(ctx.volver)}" data-volver>Volver a la lista</a>
      <p class="cabeza"><span class="tipo">${TIPO[d.tipo]}</span><span>${esc(d.numero)}</span>${tipoGlosario ? que(glosario, tipoGlosario) : ""}</p>
      <p class="extracto">${esc(d.extracto)}</p>
      <div>${etiqueta}</div>
      ${ruta(e, hoy, aj)}
      ${lineaCaducidad(e, hoy, aj)}
      ${d.estado.sobre_tablas ? `<p class="movimiento">Se trató sobre tablas. ${que(glosario, "sobre-tablas")}</p>` : ""}
    </div>
    <section class="seccion"><h2>Recorrido</h2><ol class="tiempo">${tiempo || "<li>El portal todavía no muestra movimientos.</li>"}</ol></section>
    <section class="seccion"><h2>Comisiones ${que(glosario, "comision")}</h2>${comisiones}</section>
    <section class="seccion"><h2>Autores</h2><ul class="personas">${autores}</ul></section>
    <section class="seccion"><h2>Documentos ${que(glosario, "despacho")}</h2>${docs}
      <p><a href="${esc(d.url_portal)}" target="_blank" rel="noopener">Ver este expediente en el portal oficial</a></p></section>
  </article>`;
}

export function comoFunciona(glosario) {
  const def = Object.values(glosario).map((g) => `<div><dt>${esc(g.termino)}</dt><dd>${esc(g.texto)}</dd></div>`).join("");
  return `<h1>¿Cómo avanza un proyecto?</h1>
    <p class="intro">Todo proyecto recorre hasta cuatro etapas. Este sitio las muestra como una línea con cuatro paradas.</p>
    <ol class="etapas">
      <li><strong>Presentado</strong><p>Se ingresa y se informa en una sesión: toma estado parlamentario.</p></li>
      <li><strong>En comisión</strong><p>Se gira a una o varias comisiones para que lo estudien. Desde ese momento corre un plazo de 12 meses: si no se trata, caduca.</p></li>
      <li><strong>Con dictamen</strong><p>La comisión emite su despacho y el proyecto queda listo para votarse en el recinto.</p></li>
      <li><strong>Resultado</strong><p>Se aprueba o no en una sesión. Si pasó el plazo sin tratarse, caduca, y puede rehabilitarse o archivarse.</p></li>
    </ol>
    <section class="seccion" style="margin-top:2.5rem"><h2>Palabras que aparecen en el sitio</h2><dl class="glosario">${def}</dl></section>`;
}
