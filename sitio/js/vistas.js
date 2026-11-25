// Arma el HTML de cada pantalla. Todo texto que viene de los datos pasa por esc().
import {
  agruparNovedades, agruparPorAnio, conteos, diasHasta, esAutorDelBloque, fechaRelativa, resumenCoautores,
} from "./logica.js";

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const idArchivo = (numero) => numero.replaceAll("/", "-");

const TIPO = { ley: "LEY", resolucion: "RESOLUCIÓN", declaracion: "DECLARACIÓN", otros: "NOTA" };
const TIPO_TEXTO = { ley: "Ley", resolucion: "Resolución", declaracion: "Declaración", otros: "Nota" };
// Qué es cada tipo, en una línea, para quien no conoce el reglamento.
export const TIPO_BREVE = {
  ley: "Crea o cambia una norma obligatoria para toda la provincia.",
  resolucion: "Una decisión de la Legislatura. Muchas veces es un pedido de informes al Poder Ejecutivo.",
  declaracion: "Expresa la opinión de la Legislatura: beneplácito, adhesión, repudio o preocupación. No obliga a nadie.",
  otros: "Un pedido formal de un legislador o legisladora, por ejemplo para rehabilitar un proyecto caducado o pedir licencia.",
};
const TIPO_LARGO = { ley: "Proyecto de ley", resolucion: "Proyecto de resolución", declaracion: "Proyecto de declaración", otros: "Nota" };
const etiquetaTipo = (tipo) => `<span class="tipo ${esc(tipo)}" title="${esc(TIPO_BREVE[tipo] ?? "")}">${TIPO[tipo] ?? "OTRO"}</span>`;
const RESULTADO = { aprobado: "Aprobado", caduco: "Caducó", archivado: "Archivado", rechazado: "No aprobado" };
const ESTACIONES = ["Presentado", "En comisión", "Con dictamen"];
const MUERTOS = new Set(["caduco", "archivado", "rechazado"]);

const fecha = (iso, opciones = { day: "numeric", month: "long", year: "numeric" }) =>
  new Intl.DateTimeFormat("es-AR", { ...opciones, timeZone: "UTC" }).format(new Date(`${iso.slice(0, 10)}T12:00:00Z`));
const fechaCorta = (iso) => fecha(iso, { day: "numeric", month: "short", year: "numeric" });
const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;

// --- piezas ------------------------------------------------------------------

export function avatar(leg, tam = "m") {
  if (!leg) return "";
  if (leg.foto) return `<img class="avatar ${tam}" src="${esc(leg.foto)}" alt="" loading="lazy">`;
  const ini = leg.nombre.split(" ").filter(Boolean);
  const letras = (ini[0][0] + (ini.at(-1)[0] || "")).toUpperCase();
  return `<span class="avatar ${tam}" aria-hidden="true">${esc(letras)}</span>`;
}

export function que(glosario, clave) {
  const g = glosario[clave];
  return g ? `<details class="que"><summary>¿Qué significa?</summary><p>${esc(g.texto)}</p></details>` : "";
}

function claseResultado(r) {
  return r === "aprobado" ? "aprobado" : MUERTOS.has(r) ? "muerto" : "";
}

function nombresEstaciones(e) {
  return [...ESTACIONES, RESULTADO[e.estado.resultado] ?? "Votación"];
}

function ruta(e, { grande = false } = {}) {
  const etapa = e.estado.etapa;
  const nombres = nombresEstaciones(e);
  const items = nombres.map((n, i) => {
    const paso = i + 1;
    const clase = paso < etapa ? "hecho" : paso === etapa ? "actual" : "";
    let extra = "";
    if (grande && paso === 1 && e.estado.ingreso) extra = `<small>${esc(fechaCorta(e.estado.ingreso))}</small>`;
    if (grande && paso === etapa && paso === 4 && e.estado.fecha_resultado) extra = `<small>${esc(fechaCorta(e.estado.fecha_resultado))}</small>`;
    return `<li class="${clase}"${paso === etapa ? ' aria-current="step"' : ""}>${esc(n)}${extra}</li>`;
  }).join("");
  const etiqueta = `Etapa ${etapa} de 4: ${nombres[etapa - 1]}`;
  return `<ol class="ruta ${grande ? "grande" : "compacta"} ${claseResultado(e.estado.resultado)}" aria-label="${esc(etiqueta)}">${items}</ol>`;
}

function estadoFila(e) {
  const etapa = e.estado.etapa;
  return `<div class="estado-fila ${claseResultado(e.estado.resultado)}">${esc(nombresEstaciones(e)[etapa - 1])}<span>paso ${etapa} de 4</span></div>`;
}

function lineaVence(e, hoy, aj) {
  const c = e.estado.caduca_el;
  if (!c || e.estado.resultado) return "";
  const d = diasHasta(c, hoy);
  if (d < 0) return `<div class="vence tranqui">El plazo venció el ${esc(fechaCorta(c))}; el portal todavía no lo registra</div>`;
  if (d <= aj.dias_por_caducar) return `<div class="vence">Caduca en ${plural(d, "día", "días")}</div>`;
  return `<div class="vence tranqui">Caduca aprox. el ${esc(fecha(c))}</div>`;
}

function coautores(e, ctx) {
  const r = resumenCoautores(e.autores_bloque, ctx.propio, e.n_autores ?? e.autores_bloque.length);
  if (!r.caras.length && !r.otros) return "";
  const caras = r.caras.map((s) => avatar(ctx.legs[s], "s")).join("");
  const conBloque = r.caras.length + r.masBloque;
  const partes = [];
  if (conBloque) partes.push(`${conBloque} del bloque`);
  if (r.otros) partes.push(`${r.otros} ${r.otros === 1 ? "autor" : "autores"} ${conBloque ? "más" : "de otros bloques"}`);
  const texto = `${ctx.propio ? "Con " : ""}${partes.join(" y ")}`;
  return `<div class="avatares">${caras}<span>${esc(texto.charAt(0).toUpperCase() + texto.slice(1))}</span></div>`;
}

// Etiqueta que dice qué pasó y cuándo: "● Aprobado el 18/11".
function etiquetaNovedad(n) {
  const dia = n.fecha ? ` el ${fecha(n.fecha, { day: "numeric", month: "numeric" })}` : "";
  return `<span class="nuevo ${esc(n.clase ?? "tramite")}">● ${esc(n.corto ?? "Novedad")}${dia}</span>`;
}

export function filaProyecto(e, ctx) {
  const nov = ctx.nov.get(e.numero);
  const um = e.estado.ultimo_movimiento;
  const comision = e.comisiones?.[0];
  return `<li class="proyecto"><a href="#/exp/${esc(idArchivo(e.numero))}">
    <div>
      <div class="meta">${etiquetaTipo(e.tipo)}<span>${esc(e.numero)}</span>${comision ? `<span>${esc(comision)}</span>` : ""}${nov ? etiquetaNovedad(nov) : ""}</div>
      <div class="titulo">${esc(e.titulo)}</div>
      ${um ? `<div class="ultimo">${esc(um.texto)}, ${esc(fechaRelativa(um.fecha, ctx.hoy))}</div>` : ""}
    </div>
    <div class="lado">${estadoFila(e)}${ruta(e)}${lineaVence(e, ctx.hoy, ctx.aj)}${coautores(e, ctx)}</div>
  </a></li>`;
}

export function lista(exps, ctx, limite) {
  if (!exps.length) return '<p class="vacio">No hay proyectos que coincidan. Probá con otra pestaña o borrá la búsqueda.</p>';
  const resto = exps.length - limite;
  return `<ul class="lista">${exps.slice(0, limite).map((e) => filaProyecto(e, ctx)).join("")}</ul>${resto > 0
    ? `<p class="mas"><button type="button" class="boton sec" data-mas>Mostrar ${Math.min(resto, 30)} más (quedan ${resto})</button></p>` : ""}`;
}

// --- indicadores, pestañas y filtros -------------------------------------------

export function indicadores(r, activa) {
  const b = (clave, n, texto, rojo = false) =>
    `<button type="button" class="ind ${rojo && n ? "rojo" : ""}" data-tarjeta="${clave}" aria-pressed="${activa === clave}">
      <span class="n">${n}</span><span class="t">${texto}</span></button>`;
  return `<div class="indicadores" role="group" aria-label="Filtrar por situación">
    ${b("novedades", r.novedades, "con novedades esta semana")}
    ${b("porCaducar", r.porCaducar, `caducan en los próximos ${r.dias} días`, true)}
    ${b("enComision", r.enComision, "en estudio en comisión")}
    ${b("aprobados", r.aprobadosAnio, "aprobados este año")}
  </div>`;
}

const NOMBRE_TARJETA = {
  novedades: "con novedades esta semana",
  porCaducar: "que caducan pronto, los que vencen antes primero",
  enComision: "en estudio en comisión",
  aprobados: "aprobados este año",
};

export function herramientas(vista, exps, cuenta, glosario) {
  const c = conteos(exps);
  const tab = (clave, texto) => `<button type="button" role="tab" data-pestania="${clave}" aria-selected="${!vista.tarjeta && vista.pestania === clave}">${texto}<span class="c">${c[clave]}</span></button>`;
  const filtro = vista.tarjeta
    ? `<div class="filtro-activo"><span>${plural(cuenta, "proyecto", "proyectos")} ${NOMBRE_TARJETA[vista.tarjeta]}.</span><button type="button" class="enlace" data-quitar>Ver todos</button></div>`
    : "";
  const explicaciones = {
    fondo: `<b>Leyes:</b> ${esc(TIPO_BREVE.ley)} <b>Resoluciones:</b> ${esc(TIPO_BREVE.resolucion)}`,
    declaraciones: esc(TIPO_BREVE.declaracion),
    otros: `<b>Notas:</b> ${esc(TIPO_BREVE.otros)}`,
    caducados: `${esc(glosario.caducidad?.texto)} ${esc(glosario.rehabilitacion?.texto)}`,
  };
  const explica = vista.tarjeta ? "" : `<p class="explica${vista.pestania === "caducados" ? "" : " suave"}">${explicaciones[vista.pestania]}</p>`;
  return `<div class="herr">
    <div class="tabs" role="tablist" aria-label="Tipo de proyecto">
      ${tab("fondo", "Leyes y resoluciones")}${tab("declaraciones", "Declaraciones")}${tab("otros", "Notas")}${tab("caducados", "Caducados y archivados")}
    </div>
    <div class="buscar">
      <label class="oculto" for="buscar">Buscar</label>
      <input id="buscar" class="campo" type="search" placeholder="Buscar por tema o número" value="${esc(vista.texto)}" data-buscar>
      <label class="oculto" for="orden">Orden</label>
      <select id="orden" class="campo" data-orden>
        <option value="recientes"${vista.orden === "recientes" ? " selected" : ""}>Más recientes</option>
        <option value="vencen"${vista.orden === "vencen" ? " selected" : ""}>Vencen antes</option>
      </select>
    </div>
  </div>${filtro}${explica}`;
}

// --- pantallas ------------------------------------------------------------------

export function elegir(legisladores, statsPorSlug, texto) {
  const q = texto.trim().toLowerCase();
  const tarjetas = legisladores
    .filter((l) => !q || l.nombre.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase()
      .includes(q.normalize("NFKD").replace(/[̀-ͯ]/g, "")))
    .map((l) => {
      const s = statsPorSlug[l.slug];
      return `<li><a class="tarjeta-leg" href="#/leg/${esc(l.slug)}">${avatar(l, "l")}<b>${esc(l.nombre)}</b>
        <small>${l.departamental ? "Legislador/a departamental" : "Distrito único"}</small>
        <small>${plural(s.total, "proyecto", "proyectos")}</small>
        ${s.porCaducar ? `<span class="alertita">${plural(s.porCaducar, "caduca pronto", "caducan pronto")}</span>` : ""}</a></li>`;
    }).join("");
  return tarjetas ? `<ul class="grilla">${tarjetas}</ul>` : '<p class="vacio">No hay ningún legislador del bloque con ese nombre.</p>';
}

export function bandaElegir(texto) {
  return `<div class="banda"><div class="cont">
    <h1>¿De quién querés ver los proyectos?</h1>
    <p class="bajada">Elegí un legislador o legisladora del bloque. Desde este dispositivo vas a entrar directo a su panel la próxima vez.</p>
    <div style="margin-top:20px"><label class="oculto" for="buscar-leg">Buscar por nombre</label>
      <input id="buscar-leg" class="campo" type="search" placeholder="Buscar por nombre" value="${esc(texto)}" data-buscar-leg></div>
  </div></div>`;
}

export function bandaLegislador(leg, total) {
  return `<div class="perfil">${avatar(leg, "xl")}<div>
    ${leg.cargo ? `<span class="etiqueta">${esc(leg.cargo)}</span>` : ""}
    <h1>${esc(leg.nombre)}</h1>
    <p class="bajada">${total
      ? `Firmó <b>${plural(total, "proyecto", "proyectos")}</b> en este mandato, como autor/a o coautor/a.`
      : "Todavía no hay proyectos cargados. Si la carga inicial está en curso, van a aparecer en las próximas actualizaciones."}</p>
  </div></div>`;
}

export function paraAtender(caducan, novedades, expPorNumero, hoy, abierto = false) {
  if (!caducan.length && !novedades.length) return "";
  const alerta = (e) => `<a class="alerta" href="#/exp/${esc(idArchivo(e.numero))}">
      <div class="cuenta"><b>${diasHasta(e.estado.caduca_el, hoy)}</b><small>días</small></div>
      <div><div class="tt">${esc(e.titulo)}</div><div class="mm">${TIPO_TEXTO[e.tipo]} · ${esc(e.numero)}${e.comisiones?.[0] ? ` · ${esc(e.comisiones[0])}` : ""}</div></div></a>`;
  const nov = (n) => {
    const e = expPorNumero[n.numero];
    const cuando = fecha(n.fecha, { weekday: "long", day: "numeric", month: "long" });
    return `<a class="nov ${esc(n.clase ?? "tramite")}" href="#/exp/${esc(idArchivo(n.numero))}"><span class="qq">${esc(n.corto ?? n.texto)} · ${esc(cuando)}</span>
      <span class="tt">${esc(e?.titulo ?? n.numero)}</span></a>`;
  };
  const g = agruparNovedades(novedades);
  const grupo = (lista, titulo, clase) => lista.length
    ? `<div class="grupo-nov ${clase}"><div class="grupo-tit">${titulo} <span>${lista.length}</span></div>${lista.slice(0, 5).map(nov).join("")}
        ${lista.length > 5 ? `<p class="grupo-mas">y ${lista.length - 5} más</p>` : ""}</div>` : "";
  const rutina = g.tramite.length
    ? `<details class="rutina"><summary>${g.buenas.length || g.malas.length ? "Además, " : ""}${plural(g.tramite.length, "proyecto tuvo", "proyectos tuvieron")} trámite de rutina (se presentaron, pasaron a comisión…)</summary>
        ${g.tramite.slice(0, 8).map(nov).join("")}${g.tramite.length > 8 ? `<p class="grupo-mas">y ${g.tramite.length - 8} más</p>` : ""}</details>` : "";
  const chip = (n, texto, color) => `<span class="chip-at"><span class="punto" style="background:var(--${color})"></span><b>${n}</b> ${texto}</span>`;
  return `<details class="desp-atender seccion" data-atender${abierto ? " open" : ""}>
    <summary>
      <span class="desp-tit">Para atender</span>
      <span class="desp-chips">${chip(caducan.length, caducan.length === 1 ? "caduca pronto" : "caducan pronto", "rojo")}${chip(novedades.length, novedades.length === 1 ? "novedad de la semana" : "novedades de la semana", "azul")}</span>
      <span class="desp-accion" aria-hidden="true"><span class="ver">Ver detalle</span><span class="ocultar">Ocultar</span></span>
    </summary>
    <div class="atender">
      <div class="caja"><div class="caja-cab"><span class="punto" style="background:var(--rojo)"></span>Caducan pronto si no se tratan</div>
        ${caducan.length ? caducan.slice(0, 5).map(alerta).join("") : '<p class="nada">Ningún proyecto caduca en los próximos 60 días.</p>'}
        ${caducan.length > 5 ? `<div class="caja-pie"><button type="button" class="enlace" data-tarjeta="porCaducar">Ver los ${caducan.length}</button></div>` : ""}
      </div>
      <div class="caja"><div class="caja-cab"><span class="punto" style="background:var(--azul)"></span>Novedades de la semana</div>
        ${novedades.length ? grupo(g.buenas, "Aprobados y avances", "buena") + grupo(g.malas, "Caducaron, se archivaron o no se aprobaron", "mala") + rutina
          : '<p class="nada">Esta semana no hubo novedades.</p>'}
        ${novedades.length > 1 ? `<div class="caja-pie"><button type="button" class="enlace" data-tarjeta="novedades">Ver las ${novedades.length} en la lista</button></div>` : ""}
      </div>
    </div></details>`;
}

export function tablaBloque(filas) {
  const celda = (n, rojo = false) => `<td class="n ${n ? (rojo ? "rojo" : "") : "nulo"}">${n || "—"}</td>`;
  const cuerpo = filas.map((f) => {
    const vivos = f.enComision, aprob = f.aprobadosAnio, muertos = f.caducados;
    const tot = Math.max(1, f.total);
    return `<tr data-leg="${esc(f.slug)}"><td><a class="quien2" href="#/leg/${esc(f.slug)}">${avatar(f, "m")}${esc(f.nombre)}</a></td>
      <td class="n">${f.total}</td>${celda(vivos)}${celda(f.porCaducar, true)}${celda(aprob)}
      <td><span class="mini" aria-hidden="true"><i style="width:${vivos / tot * 100}%;background:var(--rojo)"></i><i style="width:${aprob / tot * 100}%;background:var(--verde)"></i><i style="width:${muertos / tot * 100}%;background:var(--gris-claro)"></i></span></td></tr>`;
  }).join("");
  return `<div class="tabla-cont"><table class="tabla"><thead><tr><th>Legislador</th><th class="n">Proyectos</th><th class="n">En comisión</th><th class="n">Por caducar</th><th class="n">Aprobados este año</th><th>Cómo están</th></tr></thead>
    <tbody>${cuerpo}</tbody></table></div>
    <div class="leyenda"><span style="--c:var(--rojo)">En comisión</span><span style="--c:var(--verde)">Aprobados este año</span><span style="--c:var(--gris-claro)">Caducados o archivados</span></div>`;
}

export function ficha(d, ctx) {
  const { hoy, aj, glosario, legsLista, legs, volver, volverNombre } = ctx;
  const e = d;
  const r = d.estado.resultado;
  const deBloque = [], otros = [];
  for (const a of d.autores) {
    const slug = esAutorDelBloque(a, legsLista);
    if (slug) deBloque.push(slug); else otros.push(a);
  }

  const pasos = d.linea_tiempo.filter((t) => t.texto !== "Sigue el trámite normal");
  if (d.estado.caduca_el && !r) {
    pasos.push({ fecha: d.estado.caduca_el, texto: "Vence el plazo de 12 meses", detalle: "Si no se trata antes, caduca. Puede pedirse su rehabilitación.", futuro: true });
  }
  const tiempo = agruparPorAnio(pasos).map((g) => `<div class="anio">${esc(g.anio)}</div><ol class="tiempo">${g.pasos.map((p) =>
    `<li class="paso ${p.futuro ? "futuro" : "hecho"}"><span class="f">${p.fecha ? esc(fecha(p.fecha, { day: "numeric", month: "long" })) : ""}</span><span class="p"><i></i></span>
      <span class="x"><b>${esc(p.texto)}</b>${p.detalle ? `<small>${esc(p.detalle)}</small>` : ""}</span></li>`).join("")}</ol>`).join("");

  let estadoLateral = "";
  if (d.estado.caduca_el && !r) {
    const dias = diasHasta(d.estado.caduca_el, hoy);
    const usado = Math.min(100, Math.max(0, (365 - dias) / 365 * 100));
    const urgente = dias <= aj.dias_por_caducar;
    estadoLateral = `<div class="bloque-l reloj ${urgente ? "" : "tranqui"}"><h3>Tiempo para tratarlo</h3>
      <div class="grande">${dias >= 0 ? plural(dias, "día", "días") : "Vencido"}</div>
      <p>${dias >= 0 ? `Caduca aprox. el ${esc(fecha(d.estado.caduca_el))} si no se trata.` : "El plazo ya venció; el portal todavía no registró la caducidad."} ${que(glosario, "caducidad")}</p>
      <div class="barra" aria-hidden="true"><i style="width:${usado}%"></i></div></div>`;
  } else if (r) {
    estadoLateral = `<div class="bloque-l resultado-l ${claseResultado(r)}"><h3>Resultado</h3><div class="grande">${RESULTADO[r]}</div>
      ${d.estado.fecha_resultado ? `<p class="mm">El ${esc(fecha(d.estado.fecha_resultado))}</p>` : ""}</div>`;
  }

  const comisiones = d.comisiones.length
    ? d.comisiones.map((c, i) => `<div class="com"><span>${esc(c)}</span>${i === 0 && d.comisiones.length > 1 ? "<small>PRINCIPAL</small>" : ""}</div>`).join("")
    : '<p class="otros">Todavía no se giró a ninguna comisión.</p>';
  const docs = d.documentos.length
    ? `<ul class="docs">${d.documentos.map((x) => `<li>${esc(x.seccion)}: ${x.url ? `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.nombre)}</a>` : `${esc(x.nombre)} <span class="mm">(se ve en el portal oficial)</span>`}</li>`).join("")}</ul>`
    : '<p class="otros">Todavía no hay despachos, actas ni texto aprobado.</p>';

  return `<div class="banda"><div class="cont">
      <div class="miga"><a href="${esc(volver)}">${esc(volverNombre)}</a> › ${esc(d.numero)}</div>
      <div class="meta">${etiquetaTipo(d.tipo)}<span>${esc(d.numero)}</span>
        ${d.estado.ingreso ? `<span>Presentado el ${esc(fecha(d.estado.ingreso))}</span>` : ""}</div>
      <h1 class="ficha-titulo">${esc(d.titulo || d.tema || d.extracto)}</h1>
      ${(d.titulo || d.tema) !== d.extracto ? `<p class="extracto-completo">${esc(d.extracto)}</p>` : ""}
      ${TIPO_BREVE[d.tipo] ? `<p class="tipo-explica"><b>${TIPO_LARGO[d.tipo]}:</b> ${esc(TIPO_BREVE[d.tipo])}</p>` : ""}
      <div class="estado-ficha"><span class="pill ${claseResultado(r)}">● ${esc(nombresEstaciones(e)[e.estado.etapa - 1])}</span>
        ${d.estado.sobre_tablas ? `<span>Se trató sobre tablas ${que(glosario, "sobre-tablas")}</span>` : ""}</div>
      ${ruta(e, { grande: true })}
    </div></div>
    <div class="cont dos">
      <div>
        <section aria-labelledby="t-rec"><div class="titulo-sec"><h2 id="t-rec">Recorrido</h2></div>
          ${tiempo || '<p class="otros">El portal todavía no muestra movimientos.</p>'}</section>
        <section aria-labelledby="t-doc" style="margin-top:28px"><div class="titulo-sec"><h2 id="t-doc">Documentos</h2>${que(glosario, "despacho")}</div>${docs}</section>
      </div>
      <aside class="lateral" aria-label="Datos del proyecto">
        ${estadoLateral}
        <div class="bloque-l"><h3>Comisiones ${que(glosario, "comision")}</h3>${comisiones}</div>
        <div class="bloque-l"><h3>Autores del bloque (${deBloque.length})</h3>
          ${deBloque.map((s) => `<a class="persona" href="#/leg/${esc(s)}">${avatar(legs[s], "m")}${esc(legs[s].nombre)}</a>`).join("") || '<p class="otros">Ninguno.</p>'}
          ${otros.length ? `<h3 style="margin-top:14px">Otros autores (${otros.length})</h3><p class="otros">${otros.map(esc).join(" · ")}</p>` : ""}
        </div>
        <a class="boton sec" href="${esc(d.url_portal)}" target="_blank" rel="noopener">Ver en el portal oficial ↗</a>
      </aside>
    </div>`;
}

export function comoFunciona(glosario, aj) {
  const def = Object.values(glosario).map((g) => `<div><dt>${esc(g.termino)}</dt><dd>${esc(g.texto)}</dd></div>`).join("");
  const ultimos = Math.max(1, Math.round(aj.dias_por_caducar / 30));
  return `<div class="banda"><div class="cont">
      <h1>Cómo avanza un proyecto</h1>
      <p class="bajada">Todo proyecto en la Legislatura de Córdoba recorre hasta cuatro etapas. En este sitio las vas a ver como una línea con cuatro paradas.</p>
    </div></div>
    <div class="cont seccion">
      <ol class="etapas4">
        <li class="et"><span class="num">1</span><h3>Presentado</h3><p>Se ingresa y se informa en una sesión: toma estado parlamentario y existe oficialmente.</p></li>
        <li class="et"><span class="num">2</span><h3>En comisión</h3><p>Se gira a una o varias comisiones que lo estudian. La primera es la principal.</p></li>
        <li class="et"><span class="num">3</span><h3>Con dictamen</h3><p>La comisión emite su despacho y el proyecto queda listo para votarse.</p></li>
        <li class="et"><span class="num">4</span><h3>Resultado</h3><p>Se aprueba o no en el recinto. Una ley aprobada después se promulga o se veta.</p></li>
      </ol>
      <div class="plazo">
        <h3>El plazo de 12 meses</h3>
        <p>Desde que toma estado parlamentario, un proyecto tiene 12 meses para tratarse. Si no, caduca. Se puede pedir su rehabilitación y vuelve a comisión con un plazo nuevo; si no, se archiva.</p>
        <div class="linea12" aria-hidden="true">${Array.from({ length: 12 }, (_, i) => `<i class="${i >= 12 - ultimos ? "u" : ""}"></i>`).join("")}</div>
        <div class="linea12-txt"><span>Mes 1: estado parlamentario</span><b>Últimos ${aj.dias_por_caducar} días: aparece en "Caducan pronto"</b><span>Mes 12: caduca</span></div>
      </div>
      <section style="margin-top:44px" aria-labelledby="t-glos"><div class="titulo-sec"><h2 id="t-glos">Palabras que vas a ver</h2></div><dl class="gloss">${def}</dl></section>
    </div>`;
}

// --- buscador global ------------------------------------------------------------

export function bandaBuscar(texto) {
  return `<div class="banda"><div class="cont">
    <h1>Buscar en todo el bloque</h1>
    <p class="bajada">Escribí un número de proyecto (por ejemplo 45212), palabras del tema o el apellido de un legislador. Busca en todos los tipos y estados, también en los caducados.</p>
    <form class="buscador" role="search" data-form-buscar>
      <label class="oculto" for="buscar-todo">Buscar proyectos</label>
      <input id="buscar-todo" class="campo grande" type="search" placeholder="Ej.: salud mental, 45212, Ferrero" value="${esc(texto)}" autocomplete="off" enterkeyhint="search" data-buscar-todo>
    </form>
  </div></div>`;
}

export function resultadosBusqueda(texto, resultados, ctx, limite) {
  const q = texto.trim();
  if (q.length < 2) {
    return `<p class="vacio">Escribí al menos dos letras o números para empezar.</p>`;
  }
  if (!resultados.length) {
    return `<p class="vacio">No encontramos proyectos del bloque con “${esc(q)}”. Probá con menos palabras o con otra forma de escribirlo.</p>`;
  }
  return `<div class="titulo-sec"><h2>${plural(resultados.length, "proyecto encontrado", "proyectos encontrados")}</h2><span class="aux">Los más nuevos primero</span></div>`
    + lista(resultados, ctx, limite);
}
