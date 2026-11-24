import test from "node:test";
import assert from "node:assert/strict";
import {
  fechaRelativa, diasHasta, resumen, filtrar, ordenar, estaDesactualizado, normalizar, conNovedad,
} from "../sitio/js/logica.js";

const AJ = { dias_por_caducar: 60, dias_desactualizado: 2 };
const HOY = "2026-11-24";

const exp = (numero, tipo, estado, extra = {}) => ({
  numero, tipo, titulo: `Proyecto ${numero}`, comisiones: [], autores_bloque: ["ferrero"],
  estado: { etapa: 2, resultado: null, caduca_el: null, ultimo_movimiento: null, ...estado }, ...extra,
});

const EXPS = [
  exp("1/L/26", "ley", { etapa: 2, caduca_el: "2027-01-10", ultimo_movimiento: { fecha: "2026-01-10", texto: "Pasó a estudio en comisión" } }),
  exp("2/R/26", "resolucion", { etapa: 3, caduca_el: "2027-06-01", ultimo_movimiento: { fecha: "2026-06-01", texto: "x" } }),
  exp("3/D/26", "declaracion", { etapa: 4, resultado: "aprobado", ultimo_movimiento: { fecha: "2026-10-29", texto: "Fue aprobado" } }),
  exp("4/L/24", "ley", { etapa: 4, resultado: "caduco", ultimo_movimiento: { fecha: "2025-02-17", texto: "Caducó" } }),
  exp("5/N/25", "otros", { etapa: 1, ultimo_movimiento: null }),
  exp("6/L/25", "ley", { etapa: 4, resultado: "aprobado", ultimo_movimiento: { fecha: "2025-12-01", texto: "Fue aprobado" } }),
];
const NOVEDADES = [
  { numero: "3/D/26", fecha: "2026-11-20", texto: "Fue aprobado" },
  { numero: "3/D/26", fecha: "2026-11-21", texto: "Otra" },
  { numero: "2/R/26", fecha: "2026-11-01", texto: "vieja" },
];

test("normalizar quita tildes y mayúsculas", () => {
  assert.equal(normalizar("  Comisión  de EDUCACIÓN "), "comision de educacion");
});

test("fechaRelativa", () => {
  assert.equal(fechaRelativa("2026-11-24", HOY), "hoy");
  assert.equal(fechaRelativa("2026-11-23", HOY), "ayer");
  assert.equal(fechaRelativa("2026-11-18", HOY), "hace 6 días");
  assert.equal(fechaRelativa("2026-06-24", HOY), "hace 5 meses");
  assert.equal(fechaRelativa("2025-10-24", HOY), "hace 1 año");
  assert.equal(fechaRelativa(null, HOY), "sin fecha");
});

test("diasHasta", () => {
  assert.equal(diasHasta("2026-12-24", HOY), 30);
  assert.equal(diasHasta("2026-11-20", HOY), -4);
});

test("conNovedad mira solo los últimos 7 días", () => {
  const s = conNovedad(NOVEDADES, HOY);
  assert.deepEqual([...s], ["3/D/26"]);
});

test("resumen: por caducar usa 60 días y excluye resueltos; aprobados del año", () => {
  assert.deepEqual(resumen(EXPS, NOVEDADES, HOY, AJ), { novedades: 1, porCaducar: 1, enComision: 2, aprobadosAnio: 1 });
});

test("filtrar por pestaña", () => {
  const f = (p) => filtrar(EXPS, { pestania: p }, NOVEDADES, HOY, AJ).map((e) => e.numero);
  assert.deepEqual(f("fondo"), ["1/L/26", "2/R/26", "6/L/25"]);
  assert.deepEqual(f("declaraciones"), ["3/D/26"]);
  assert.deepEqual(f("otros"), ["5/N/25"]);
});

test("las pestañas no muestran caducados; el filtro de caducados sí", () => {
  const cad = filtrar(EXPS, { tarjeta: "caducados" }, NOVEDADES, HOY, AJ).map((e) => e.numero);
  assert.deepEqual(cad, ["4/L/24"]);
});

test("tarjeta ignora pestaña", () => {
  const r = filtrar(EXPS, { pestania: "declaraciones", tarjeta: "porCaducar" }, NOVEDADES, HOY, AJ);
  assert.deepEqual(r.map((e) => e.numero), ["1/L/26"]);
  const a = filtrar(EXPS, { pestania: "otros", tarjeta: "aprobados" }, NOVEDADES, HOY, AJ);
  assert.deepEqual(a.map((e) => e.numero), ["3/D/26"]);
});

test("filtrar por texto ignora tildes y busca en número y título", () => {
  const xs = [exp("9/L/26", "ley", {}, { titulo: "Creando la Comisión de Ética" })];
  assert.equal(filtrar(xs, { pestania: "fondo", texto: "comision etica" }, [], HOY, AJ).length, 1);
  assert.equal(filtrar(xs, { pestania: "fondo", texto: "9/L" }, [], HOY, AJ).length, 1);
  assert.equal(filtrar(xs, { pestania: "fondo", texto: "salud" }, [], HOY, AJ).length, 0);
});

test("filtrar por comisión y legislador (vista del bloque)", () => {
  const xs = [exp("9/L/26", "ley", {}, { comisiones: ["Educación"], autores_bloque: ["bria"] }), exp("8/L/26", "ley", {})];
  assert.deepEqual(filtrar(xs, { pestania: "fondo", comision: "Educación" }, [], HOY, AJ).map((e) => e.numero), ["9/L/26"]);
  assert.deepEqual(filtrar(xs, { pestania: "fondo", legislador: "bria" }, [], HOY, AJ).map((e) => e.numero), ["9/L/26"]);
});

test("ordenar: novedades primero, después por último movimiento, null al final", () => {
  const r = ordenar(EXPS, NOVEDADES, HOY).map((e) => e.numero);
  assert.deepEqual(r, ["3/D/26", "2/R/26", "1/L/26", "6/L/25", "4/L/24", "5/N/25"]);
});

test("desactualizado cuenta días hábiles", () => {
  const est = (f) => ({ ultima_actualizacion_ok: `${f}T07:10:00-03:00` });
  assert.equal(estaDesactualizado(est("2026-11-20"), "2026-11-23", 2), false); // viernes → lunes: 1 hábil
  assert.equal(estaDesactualizado(est("2026-11-18"), "2026-11-23", 2), true);  // miércoles → lunes: 3 hábiles
  assert.equal(estaDesactualizado(est("2026-11-24"), "2026-11-24", 2), false);
  assert.equal(estaDesactualizado({ ultima_actualizacion_ok: null }, HOY, 2), true);
});

test("aprobados del año usan la fecha de aprobación, no la de promulgación", () => {
  const ley = exp("7/L/25", "ley", { etapa: 4, resultado: "aprobado", fecha_resultado: "2025-12-10",
    ultimo_movimiento: { fecha: "2026-01-15", texto: "La ley se promulgó" } });
  assert.equal(resumen([ley], [], HOY, AJ).aprobadosAnio, 0);
  const nueva = exp("8/L/26", "ley", { etapa: 4, resultado: "aprobado", fecha_resultado: "2026-03-02",
    ultimo_movimiento: { fecha: "2026-04-01", texto: "La ley se promulgó" } });
  assert.equal(resumen([nueva], [], HOY, AJ).aprobadosAnio, 1);
});
