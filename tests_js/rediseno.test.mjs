import test from "node:test";
import assert from "node:assert/strict";
import {
  esAutorDelBloque, proximosACaducar, novedadesRecientes, conteos, ordenarPor, resumenCoautores,
  porLegislador, agruparPorAnio,
} from "../sitio/js/logica.js";

const AJ = { dias_por_caducar: 60 };
const HOY = "2026-11-24";
const e = (numero, tipo, estado, extra = {}) => ({
  numero, tipo, titulo: numero, comisiones: [], autores_bloque: ["ferrero"],
  estado: { etapa: 2, resultado: null, caduca_el: null, ultimo_movimiento: null, ...estado }, ...extra,
});

test("esAutorDelBloque ignora tildes y usa alias", () => {
  const legs = [{ slug: "bria", nombre_portal: "Bria, Jose Alberto", alias: [] },
    { slug: "gudino", nombre_portal: "Gudiño, Daniela Soledad", alias: ["Gudino, Daniela"] }];
  assert.equal(esAutorDelBloque("Bría, José Alberto", legs), "bria");
  assert.equal(esAutorDelBloque("GUDINO, Daniela", legs), "gudino");
  assert.equal(esAutorDelBloque("Juez, Daniel Alejandro", legs), null);
});

test("proximosACaducar excluye vencidos, resueltos y lejanos, y ordena por fecha", () => {
  const xs = [
    e("1", "ley", { caduca_el: "2027-01-10" }),
    e("2", "ley", { caduca_el: "2026-12-01" }),
    e("3", "ley", { caduca_el: "2026-11-20" }),            // ya vencido: no
    e("4", "ley", { caduca_el: "2027-06-01" }),            // lejano: no
    e("5", "ley", { caduca_el: "2026-12-05", resultado: "aprobado" }),
  ];
  assert.deepEqual(proximosACaducar(xs, HOY, AJ).map((x) => x.numero), ["2", "1"]);
});

test("novedadesRecientes: una por expediente, la más nueva primero, solo 7 días", () => {
  const nov = [
    { numero: "A", fecha: "2026-11-20", texto: "Pasó a comisión" },
    { numero: "A", fecha: "2026-11-22", texto: "Fue aprobado" },
    { numero: "B", fecha: "2026-11-23", texto: "Despacho" },
    { numero: "C", fecha: "2026-11-01", texto: "vieja" },
  ];
  assert.deepEqual(novedadesRecientes(nov, HOY), [
    { numero: "B", fecha: "2026-11-23", texto: "Despacho" },
    { numero: "A", fecha: "2026-11-22", texto: "Fue aprobado" },
  ]);
});

test("conteos por pestaña separan caducados y archivados", () => {
  const xs = [e("1", "ley", {}), e("2", "resolucion", {}), e("3", "declaracion", {}), e("4", "otros", {}),
    e("5", "ley", { resultado: "caduco" }), e("6", "declaracion", { resultado: "archivado" })];
  assert.deepEqual(conteos(xs), { fondo: 2, declaraciones: 1, otros: 1, caducados: 2 });
});

test("ordenarPor vencen: los que vencen antes primero, sin vencimiento al final", () => {
  const xs = [e("1", "ley", { caduca_el: "2027-03-01" }), e("2", "ley", {}), e("3", "ley", { caduca_el: "2026-12-01" })];
  assert.deepEqual(ordenarPor(xs, "vencen", [], HOY).map((x) => x.numero), ["3", "1", "2"]);
});

test("resumenCoautores: máximo 4 caras, sin el propio, y cuenta el resto", () => {
  const r = resumenCoautores(["austin", "bria", "ferrero", "luna", "nigro", "saliba"], "ferrero", 9);
  assert.deepEqual(r, { caras: ["austin", "bria", "luna", "nigro"], masBloque: 1, otros: 3 });
  assert.deepEqual(resumenCoautores(["ferrero"], "ferrero", 1), { caras: [], masBloque: 0, otros: 0 });
});

test("porLegislador arma la tabla del bloque ordenada por total", () => {
  const indice = {
    legisladores: [
      { slug: "a", nombre: "A", foto: null, expedientes: ["1"] },
      { slug: "b", nombre: "B", foto: "fotos/b.webp", expedientes: ["1", "2", "3"] },
    ],
    expedientes: {
      1: { tipo: "ley", estado: { etapa: 2, resultado: null, caduca_el: "2026-12-10" } },
      2: { tipo: "ley", estado: { etapa: 4, resultado: "aprobado", fecha_resultado: "2026-05-01" } },
      3: { tipo: "ley", estado: { etapa: 4, resultado: "caduco" } },
    },
  };
  const t = porLegislador(indice, HOY, AJ);
  assert.deepEqual(t.map((x) => x.slug), ["b", "a"]);
  assert.deepEqual(t[0], { slug: "b", nombre: "B", foto: "fotos/b.webp", total: 3, enComision: 1, porCaducar: 1, aprobadosAnio: 1, caducados: 1 });
});

test("agruparPorAnio respeta el orden y agrupa lo que no tiene fecha", () => {
  const g = agruparPorAnio([{ fecha: null, texto: "a" }, { fecha: "2025-02-14", texto: "b" },
    { fecha: "2025-03-01", texto: "c" }, { fecha: "2026-01-02", texto: "d" }]);
  assert.deepEqual(g.map((x) => [x.anio, x.pasos.length]), [["Sin fecha", 1], ["2025", 2], ["2026", 1]]);
});
