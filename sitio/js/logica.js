// Funciones puras del sitio: sin DOM, testeadas con `node --test tests_js/`.
// Las fechas son strings ISO "YYYY-MM-DD".

const DIA = 86400000;
const MUERTOS = new Set(["caduco", "archivado"]);
const PESTANIAS = {
  fondo: new Set(["ley", "resolucion"]),
  declaraciones: new Set(["declaracion"]),
  otros: new Set(["otros"]),
};

const aFecha = (iso) => new Date(`${iso.slice(0, 10)}T12:00:00Z`);

export function normalizar(s) {
  return (s ?? "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/\s+/g, " ").trim();
}

export function diasHasta(fecha, hoy) {
  return Math.round((aFecha(fecha) - aFecha(hoy)) / DIA);
}

export function fechaRelativa(fecha, hoy) {
  if (!fecha) return "sin fecha";
  const d = -diasHasta(fecha, hoy);
  if (d <= 0) return "hoy";
  if (d === 1) return "ayer";
  if (d < 60) return `hace ${d} días`;
  const meses = Math.floor(d / 30.44);
  if (meses < 12) return `hace ${meses} meses`;
  const anios = Math.floor(meses / 12);
  return anios === 1 ? "hace 1 año" : `hace ${anios} años`;
}

export function conNovedad(novedades, hoy, dias = 7) {
  return new Set(novedades.filter((n) => -diasHasta(n.fecha, hoy) <= dias).map((n) => n.numero));
}

const enComision = (e) => !e.estado.resultado && (e.estado.etapa === 2 || e.estado.etapa === 3);
const porCaducar = (e, hoy, aj) =>
  !e.estado.resultado && e.estado.caduca_el != null &&
  diasHasta(e.estado.caduca_el, hoy) >= 0 && diasHasta(e.estado.caduca_el, hoy) <= aj.dias_por_caducar;
// Cuenta por la fecha de aprobación (no por la de promulgación u otro movimiento posterior).
const aprobadoEsteAnio = (e, hoy) =>
  e.estado.resultado === "aprobado" &&
  (e.estado.fecha_resultado ?? e.estado.ultimo_movimiento?.fecha)?.slice(0, 4) === hoy.slice(0, 4);

export function resumen(exps, novedades, hoy, aj) {
  const nov = conNovedad(novedades, hoy);
  return {
    novedades: exps.filter((e) => nov.has(e.numero)).length,
    porCaducar: exps.filter((e) => porCaducar(e, hoy, aj)).length,
    enComision: exps.filter(enComision).length,
    aprobadosAnio: exps.filter((e) => aprobadoEsteAnio(e, hoy)).length,
  };
}

const TARJETAS = {
  novedades: (e, ctx) => ctx.nov.has(e.numero),
  porCaducar: (e, ctx) => porCaducar(e, ctx.hoy, ctx.aj),
  enComision: (e) => enComision(e),
  aprobados: (e, ctx) => aprobadoEsteAnio(e, ctx.hoy),
  caducados: (e) => MUERTOS.has(e.estado.resultado),
};

export function filtrar(exps, { pestania = "fondo", tarjeta = null, texto = "", comision = "", legislador = "" } = {},
  novedades = [], hoy, aj) {
  const ctx = { nov: conNovedad(novedades, hoy), hoy, aj };
  const q = normalizar(texto).split(" ").filter(Boolean);
  return exps.filter((e) => {
    if (tarjeta) {
      if (!TARJETAS[tarjeta](e, ctx)) return false;
    } else if (!PESTANIAS[pestania].has(e.tipo) || MUERTOS.has(e.estado.resultado)) {
      return false;
    }
    if (comision && !(e.comisiones || []).includes(comision)) return false;
    if (legislador && !(e.autores_bloque || []).includes(legislador)) return false;
    const pajar = normalizar(`${e.numero} ${e.titulo}`);
    return q.every((p) => pajar.includes(p));
  });
}

export function ordenar(exps, novedades, hoy) {
  const nov = conNovedad(novedades, hoy);
  const fecha = (e) => e.estado.ultimo_movimiento?.fecha ?? "";
  return [...exps].sort((a, b) =>
    (nov.has(b.numero) - nov.has(a.numero)) || fecha(b).localeCompare(fecha(a)) || a.numero.localeCompare(b.numero));
}

export function estaDesactualizado(estado, hoy, diasHabiles) {
  const ok = estado?.ultima_actualizacion_ok;
  if (!ok) return true;
  let habiles = 0;
  for (let d = aFecha(ok); d < aFecha(hoy);) {
    d = new Date(d.getTime() + DIA);
    const dia = d.getUTCDay();
    if (dia !== 0 && dia !== 6) habiles += 1;
  }
  return habiles > diasHabiles;
}

// --- Rediseño -----------------------------------------------------------------

export function esAutorDelBloque(nombre, legs) {
  const n = normalizar(nombre);
  const l = legs.find((x) => [x.nombre_portal, ...(x.alias || [])].some((a) => normalizar(a) === n));
  return l ? l.slug : null;
}

export function proximosACaducar(exps, hoy, aj) {
  return exps.filter((e) => porCaducar(e, hoy, aj))
    .sort((a, b) => a.estado.caduca_el.localeCompare(b.estado.caduca_el));
}

export function novedadesRecientes(novedades, hoy, dias = 7) {
  const ultima = new Map();
  for (const n of novedades) {
    if (-diasHasta(n.fecha, hoy) > dias) continue;
    const prev = ultima.get(n.numero);
    if (!prev || n.fecha >= prev.fecha) ultima.set(n.numero, n);
  }
  return [...ultima.values()].sort((a, b) => b.fecha.localeCompare(a.fecha) || a.numero.localeCompare(b.numero));
}

export function conteos(exps) {
  const c = { fondo: 0, declaraciones: 0, otros: 0, caducados: 0 };
  for (const e of exps) {
    if (MUERTOS.has(e.estado.resultado)) c.caducados += 1;
    else for (const [p, tipos] of Object.entries(PESTANIAS)) if (tipos.has(e.tipo)) c[p] += 1;
  }
  return c;
}

export function ordenarPor(exps, criterio, novedades, hoy) {
  if (criterio !== "vencen") return ordenar(exps, novedades, hoy);
  const v = (e) => e.estado.caduca_el ?? "9999";
  return [...exps].sort((a, b) => v(a).localeCompare(v(b)) || a.numero.localeCompare(b.numero));
}

export function resumenCoautores(slugsBloque, propio, nAutores) {
  const otrosBloque = slugsBloque.filter((s) => s !== propio);
  const caras = otrosBloque.slice(0, 4);
  return { caras, masBloque: otrosBloque.length - caras.length, otros: Math.max(0, nAutores - slugsBloque.length) };
}

export function porLegislador(indice, hoy, aj) {
  return indice.legisladores.map((l) => {
    const exps = l.expedientes.map((n) => indice.expedientes[n]).filter(Boolean);
    return {
      slug: l.slug, nombre: l.nombre, foto: l.foto ?? null, total: exps.length,
      enComision: exps.filter(enComision).length,
      porCaducar: exps.filter((e) => porCaducar(e, hoy, aj)).length,
      aprobadosAnio: exps.filter((e) => aprobadoEsteAnio(e, hoy)).length,
      caducados: exps.filter((e) => MUERTOS.has(e.estado.resultado)).length,
    };
  }).sort((a, b) => b.total - a.total || a.nombre.localeCompare(b.nombre, "es"));
}

export function agruparPorAnio(lineaTiempo) {
  const grupos = [];
  for (const paso of lineaTiempo) {
    const anio = paso.fecha ? paso.fecha.slice(0, 4) : "Sin fecha";
    if (grupos.at(-1)?.anio === anio) grupos.at(-1).pasos.push(paso);
    else grupos.push({ anio, pasos: [paso] });
  }
  return grupos;
}
