import test from "node:test";
import assert from "node:assert/strict";
import { buscarEnTodo } from "../sitio/js/logica.js";

const e = (numero, titulo, extra = {}) => ({
  numero, titulo, tipo: "ley", autores_bloque: ["ferrero"],
  estado: { etapa: 2, resultado: null, ingreso: "2025-01-01", ultimo_movimiento: null }, ...extra,
});
const LEGS = { ferrero: { nombre: "Alejandra Ferrero" }, bria: { nombre: "José Alberto Bría" } };

test("buscarEnTodo encuentra por palabras sin importar tildes ni tipo ni estado", () => {
  const xs = [
    e("1/L/25", "Crea el programa de salud mental"),
    e("2/D/25", "Beneplácito por la SALUD rural", { tipo: "declaracion", estado: { etapa: 4, resultado: "caduco", ingreso: "2024-01-01" } }),
    e("3/L/25", "Modifica el código de tránsito"),
  ];
  assert.deepEqual(buscarEnTodo(xs, "salud", LEGS).map((x) => x.numero), ["1/L/25", "2/D/25"]);
  assert.deepEqual(buscarEnTodo(xs, "transito codigo", LEGS).map((x) => x.numero), ["3/L/25"]);
});

test("buscarEnTodo busca por número y pone primero la coincidencia exacta", () => {
  const xs = [e("145212/L/25", "Otro", { estado: { etapa: 1, ingreso: "2026-01-01" } }), e("45212/D/26", "Algo", { tipo: "declaracion" })];
  assert.equal(buscarEnTodo(xs, "45212", LEGS)[0].numero, "45212/D/26");
  assert.deepEqual(buscarEnTodo(xs, "45212/d/26", LEGS).map((x) => x.numero), ["45212/D/26"]);
});

test("buscarEnTodo también busca por legislador del bloque", () => {
  const xs = [e("1/L/25", "Salud", { autores_bloque: ["bria"] }), e("2/L/25", "Salud")];
  assert.deepEqual(buscarEnTodo(xs, "bria salud", LEGS).map((x) => x.numero), ["1/L/25"]);
});

test("buscarEnTodo ordena de más nuevo a más viejo e ignora textos muy cortos", () => {
  const xs = [e("1/L/24", "Agua", { estado: { etapa: 2, ingreso: "2024-03-01" } }), e("2/L/25", "Agua", { estado: { etapa: 2, ingreso: "2025-03-01" } })];
  assert.deepEqual(buscarEnTodo(xs, "agua", LEGS).map((x) => x.numero), ["2/L/25", "1/L/24"]);
  assert.deepEqual(buscarEnTodo(xs, "a", LEGS), []);
  assert.deepEqual(buscarEnTodo(xs, "  ", LEGS), []);
});
