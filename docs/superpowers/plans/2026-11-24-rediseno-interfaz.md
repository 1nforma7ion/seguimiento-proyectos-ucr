# Rediseño de la interfaz — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (elegido por el usuario: ejecución en la sesión). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Llevar el sitio al diseño aprobado en las maquetas: la marca del bloque, fotos, "Para atender", filas más claras, la ficha en dos columnas, la tabla del bloque y la explicación del plazo.

**Architecture:** El recolector suma al índice los datos que necesita la interfaz (foto, cargo, nombre en el portal y alias). La lógica nueva va en `sitio/js/logica.js`, con funciones puras y testeadas. `vistas.js`, `app.js`, `index.html` y `estilos.css` se reescriben siguiendo la maqueta. Las fotos y la tipografía se sirven desde el propio sitio.

**Tech Stack:** Python 3.12 y pytest; HTML, CSS y ES modules sin build; `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-24-rediseno-interfaz-design.md`. La maqueta aprobada es `C:/Users/facun/AppData/Local/Temp/claude/cc6c0a1a3adae163/09f2d05e-ce5b-4e2d-9eaf-5b25f8e1d25a/scratchpad/maquetas/index.html`; sus estilos y su estructura son la referencia visual.

## Global Constraints

- Tokens de color:
  - rojo `#C8102E` y rojo oscuro `#A00D25`;
  - tinta `#1F2328`, fondo `#FFFFFF`, fondo alternativo `#F4F5F7`, borde `#E3E5E8`, pie `#1E1E1E`;
  - verde `#1E7A4C`, azul `#1F4E8C`;
  - radio de 4 px.
- Tipografía Public Sans 400 y 700, en woff, en `sitio/fuentes/` (copiada de `Web_UCR_Legisladores/src/assets/fuentes`, con licencia OFL incluida). Logo en `sitio/logo-ucr.svg`.
- Sin dependencias externas en tiempo de carga.
- Todo texto que venga de los datos se escapa con `esc()`.
- Modo oscuro y celular de 375 px sin scroll horizontal.
- Textos en castellano rioplatense.

## Review Focus

1. **Legislador sin foto en `sitio/fotos/`:** se muestran sus iniciales en un círculo y no aparece una imagen rota. Lo prueba el Task 1, `test_indice_foto_solo_si_existe`, y lo verifica en el navegador el Task 3.
2. **Legislador sin proyectos todavía,** porque la carga inicial está en curso: el panel muestra "Todavía no hay proyectos cargados" y "Para atender" queda vacío sin errores. Lo verifica en el navegador el Task 3.
3. **Autor con tilde o alias:** "Bría, José Alberto" escrito con tilde se reconoce como del bloque. Lo prueba el Task 2, `esAutorDelBloque`.
4. **Más de 3 coautores del bloque:** se muestran hasta 4 caras y "+N". Lo prueba el Task 2, `resumenCoautores`.
5. **Proyecto con `caduca_el` ya vencido** pero que el portal todavía no marcó: no se muestra una cuenta negativa y queda fuera de "Caducan pronto". Lo prueba el Task 2, `proximosACaducar`.

---

### Task 1: Datos para la interfaz (fotos, cargo, índice)

**Files:**
- Create: `herramientas/bajar_fotos.py`, `sitio/fotos/*.webp`, `sitio/fuentes/*`, `sitio/logo-ucr.svg`
- Modify: `config/legisladores.json` (agregar `"cargo": "Presidenta del bloque"` a Ferrero), `recolector/config.py` (`cargo: str | None = None`), `recolector/almacen.py` (`construir_indice`)
- Test: `tests/test_almacen.py`

**Interfaces:**
- Produces: cada entrada de `indice.json → legisladores` suma:
  - `foto`: `"fotos/<slug>.webp"`, o `null` si el archivo no existe;
  - `cargo`: `str | null`;
  - `nombre_portal`: `str`;
  - `alias`: `list[str]`.

  Cada entrada de `expedientes` suma `n_autores: int`.

- [ ] **Step 1:** Escribir los tests.
  - `test_indice_foto_solo_si_existe`: crea `sitio/fotos/ferrero.webp` en `tmp`; ferrero tiene `foto == "fotos/ferrero.webp"` y austin tiene `None`.
  - `test_indice_cargo_y_nombre_portal`.
  - `test_indice_n_autores`.
  - `construir_indice` recibe `dir_fotos: Path | None` como parámetro nuevo; por defecto es `dir_datos.parent / "fotos"`.
- [ ] **Step 2:** Correr pytest. Resultado esperado: FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Correr pytest. Resultado esperado: PASS.
- [ ] **Step 5:** Escribir `herramientas/bajar_fotos.py` con el mapa slug → URL de Supabase tomado de la web del bloque y correrlo una vez. Resultado esperado: 18 archivos `.webp` de menos de 60 KB cada uno.
- [ ] **Step 6:** Copiar las fuentes, la licencia y el logo. Commit.

### Task 2: Lógica nueva (funciones puras)

**Files:** Modify `sitio/js/logica.js`; Test `tests_js/logica.test.mjs`

**Interfaces (exports nuevos):**
- `esAutorDelBloque(nombre: string, legs: {nombre_portal, alias}[]) -> slug|null`: compara normalizando, igual que en Python.
- `proximosACaducar(exps, hoy, aj) -> exps[]`: los que tienen `0 <= diasHasta(caduca_el) <= dias_por_caducar` y no tienen resultado, ordenados por fecha ascendente.
- `novedadesRecientes(novedades, hoy, dias=7) -> {numero, fecha, texto}[]`: de la más nueva a la más vieja, una por expediente (la última).
- `conteos(exps) -> {fondo, declaraciones, otros, caducados}`: los caducados y archivados no se cuentan en las pestañas.
- `ordenarPor(exps, criterio: "recientes"|"vencen", novedades, hoy)`.
- `resumenCoautores(slugsBloque: string[], propio: string|null, nAutores: int) -> {caras: string[] (máx 4, sin el propio), masBloque: int, otros: int}`.
- `porLegislador(indice, hoy, aj) -> [{slug, nombre, foto, total, enComision, porCaducar, aprobadosAnio, caducados}]`, ordenado por total de mayor a menor.
- `agruparPorAnio(lineaTiempo) -> [{anio: string|"Sin fecha", pasos}]`.

- [ ] **Step 1:** Escribir un test por función, con los casos del Review Focus 3, 4 y 5.
- [ ] **Step 2:** Correr `node --test "tests_js/*.test.mjs"`. Resultado esperado: FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Correr los tests. Resultado esperado: PASS.
- [ ] **Step 5:** Commit.

### Task 3: Pantallas nuevas

**Files:** Rewrite `sitio/index.html`, `sitio/estilos.css`, `sitio/js/vistas.js`, `sitio/js/app.js`

- [ ] **Step 1:** Trasladar la maqueta:
  - cabecera con logo, menú y "quién" con foto y la opción "Cambiar";
  - las 5 pantallas, con los mismos componentes y textos;
  - ruta compacta en las filas y grande en la ficha.

  Se conservan el ruteo por hash, `localStorage` con try/catch, los filtros al volver de una ficha y el aviso de datos desactualizados.
- [ ] **Step 2:** Agregar la regla para celular (≤ 720 px):
  - una sola columna;
  - "Para atender" apilado;
  - fila de proyecto con la ruta debajo del texto;
  - tabla del bloque con scroll horizontal propio, sin desbordar la página;
  - indicadores en 2×2.
- [ ] **Step 3:** Verificar en el navegador con un juego de datos generado desde fixtures reales:
  - las 5 pantallas en escritorio;
  - celular de 375 px;
  - modo oscuro;
  - un legislador sin proyectos;
  - una foto faltante;
  - sin errores en la consola.
- [ ] **Step 4:** Correr las pruebas de Python y de JS. Commit y push.
