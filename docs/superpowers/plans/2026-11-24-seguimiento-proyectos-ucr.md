# Seguimiento de proyectos del bloque UCR — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sitio web estático, actualizado solo todos los días, donde cada legislador del bloque UCR ve el estado de los proyectos que firmó, en lenguaje simple.

**Architecture:** Un recolector en Python lee el portal GLD (ASP.NET WebForms, mediante postbacks) y escribe JSON en `sitio/data/`. El sitio, hecho con HTML, CSS y JS sin build, lee esos JSON. Un workflow de GitHub Actions corre el recolector en días hábiles, hace commit de los datos y publica `sitio/` en GitHub Pages.

**Tech Stack:** Python 3.12+ (`requests`, `beautifulsoup4`, `pytest`), JavaScript ES modules en el navegador (`node --test` para la lógica pura), GitHub Actions y GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-11-24-seguimiento-proyectos-ucr-design.md`

**Raíz del repo:** `D:\CLAUDE\BLOQUE UCR CBA\Seguimiento_Proyectos_UCR`. **Nunca** inicializar git ni publicar la carpeta padre `BLOQUE UCR CBA`, porque contiene archivos personales.

## Global Constraints

- Fuente de datos: `https://gld.legislaturacba.gob.ar/Publics/Buscar.aspx?q=<texto>`, con postbacks `ctl00$Body$R_Results$ctlNN$LB_Autores`, `$LB_Ruta` y `$LB_Comisiones`.
- Cortesía con el portal:
  - Como máximo 1 consulta por segundo (`pausa_segundos: 1.0`).
  - User-Agent genérico: `SeguimientoLegislativo/1.0 (+https://github.com)`, sin datos personales.
  - 3 reintentos con espera de 5, 15 y 45 s.
- El portal responde en cp1252/latin-1. Se decodifica con `utf-8` y, si falla, con `cp1252`. Los acentos y la ñ tienen que verse bien.
- Alcance: expedientes con año ≥ 24 (`desde_anio: 24`, período 146 en adelante).
- Autoría: un expediente pertenece a un legislador si su nombre normalizado (sin tildes, en minúsculas y con espacios colapsados) es igual a `nombre_portal` o a algún `alias`.
- Etapas visibles: 1 Presentado · 2 En estudio en comisión · 3 Con dictamen de comisión · 4 Resultado (aprobado / caducó / archivado).
- Estados finales para la actualización diaria: Aprobado y Archivado.
  - Caducado **no** es final: se re-consulta solo los lunes o con `--completo`.
  - Rehabilitado vuelve el proyecto a la etapa 2.
- "Por caducar": a menos de `dias_por_caducar: 60` días de `caduca_el`. `caduca_el` = fecha base + 12 meses y se muestra como fecha aproximada.
- Novedades: los cambios detectados en los últimos `dias_novedades: 30` días. La tarjeta de la portada cuenta los últimos 7 días.
- Aviso "datos desactualizados desde <fecha>" cuando la última actualización exitosa tiene más de `dias_desactualizado: 2` días hábiles.
- Si una corrida falla, **no** se marca como exitosa ni se borran datos previos. El proceso termina con código ≠ 0.
- La interfaz está toda en castellano rioplatense y sin jerga. Cada término técnico tiene su "¿Qué significa?".
- Identidad visual: sobria, con acento rojo y blanco. **No** usa el logo ni la marca de la Legislatura.
- Accesibilidad: el estado nunca se indica solo con color, se puede usar en modo claro y oscuro, y la experiencia se piensa primero para el celular.

## Review Focus

1. **Eventos sin fecha o sin sesión.** Por ejemplo, "Ingresado" sin sesión, visto en 38560/L/24. Se parsean con `None`, la línea de tiempo los muestra sin fecha y no hay error. Lo prueba el Task 3, `test_ruta_evento_sin_sesion`.
2. **Estado o situación desconocidos.** Se muestran tal cual y se agregan a `advertencias` en `estado.json`, sin error. Lo prueba el Task 4, `test_estado_desconocido`.
3. **El portal cae o cambia su HTML a mitad de la corrida.** Si la búsqueda de un legislador que ya tenía expedientes devuelve 0 resultados, se trata como error y no como "no tiene proyectos". `estado.json` conserva `ultima_actualizacion_ok` y no se borra ningún JSON. Lo prueba el Task 6, `test_cero_resultados_es_error`.
4. **Tildes.** "Bría", "Gudiño" y "Nicolás" en la configuración tienen que coincidir con "Bria, Jose Alberto" en el portal, y los extractos con ñ se guardan en UTF-8 correcto. Lo prueban el Task 1, `test_normalizar`, y el Task 3, `test_decodificacion_cp1252`.
5. **Caducidad que no cae exacta a los 12 meses** (14/02/2024 → 17/02/2025) **y proyectos rehabilitados.**
   - Si existe el evento Caducado, manda ese evento.
   - Un proyecto rehabilitado cuenta como "en comisión", con una nueva base de caducidad.
   - Lo prueba el Task 4, `test_rehabilitado_vuelve_a_comision`.

---

## Estructura de archivos

```
Seguimiento_Proyectos_UCR/
  config/legisladores.json   18 integrantes: slug, nombre_portal, nombre_mostrar, busqueda[], departamental, alias[]
  config/etapas.json         mapeo estado/situación → etapa, resultado y texto simple
  config/ajustes.json        pausa_segundos, desde_anio, dias_por_caducar, dias_novedades, dias_desactualizado
  recolector/
    __init__.py
    util.py                  normalizar(), slug(), decodificar()
    config.py                cargar_config(raiz) -> Config
    parse.py                 dataclasses Evento/Documento/Ruta/Resultado + parsers HTML
    portal.py                Portal: sesión HTTP, viewstate, pausas, reintentos
    etapas.py                calcular_estado(), linea_tiempo(), tipo_de()
    almacen.py               Expediente, guardar/cargar JSON, índice, novedades, estado, descartados
    bloque.py                verificar_bloque(): compara con legislaturacba.gob.ar/legisladores/
    corrida.py               descubrir(), actualizar(), correr()
    __main__.py              CLI
  herramientas/capturar_fixtures.py   baja HTML real a tests/fixtures (uso manual)
  tests/fixtures/*.html      HTML real del portal, guardado en bytes crudos
  tests/test_*.py
  sitio/
    index.html  estilos.css
    js/logica.js             funciones puras (testeadas con node --test)
    js/vistas.js             render de pantallas
    js/app.js                ruteo por hash y carga de datos
    data/                    salida del recolector y glosario.json (estático)
  tests_js/logica.test.mjs
  .github/workflows/sondeo.yml       prueba única de alcance desde Actions
  .github/workflows/actualizar.yml   corrida diaria y publicación en Pages
  requirements.txt  requirements-dev.txt  .gitignore  README.md  MANTENIMIENTO.md
```

---

### Task 1: Repositorio, configuración y utilidades

**Files:**
- Create: `.gitignore`, `requirements.txt` (`requests`, `beautifulsoup4`), `requirements-dev.txt` (`-r requirements.txt`, `pytest`)
- Create: `config/legisladores.json`, `config/etapas.json`, `config/ajustes.json`
- Create: `recolector/__init__.py`, `recolector/util.py`, `recolector/config.py`
- Test: `tests/test_config.py`, `tests/test_util.py`

**Interfaces:**
- Produces:
  - `normalizar(s: str) -> str`: sin tildes (NFKD), en minúsculas, con espacios colapsados y sin espacios en los extremos.
  - `slug(s: str) -> str`: normalizado; lo que no es `[a-z0-9]` pasa a `-`.
  - `decodificar(b: bytes) -> str`.
  - `cargar_config(raiz: Path) -> Config`, donde `Config(legisladores: list[Legislador], etapas: dict, ajustes: dict)`.
  - `Legislador(slug, nombre_portal, nombre_mostrar, busqueda: list[str], departamental: bool, alias: list[str])`, más el método `es_autor(nombre: str) -> bool`.

- [ ] **Step 1:** Ejecutar `git init` en la raíz del repo, armar el venv (`python -m venv .venv` y luego `.venv/Scripts/pip install -r requirements-dev.txt`) y crear un `.gitignore` con `.venv/`, `__pycache__/`, `.pytest_cache/` y `*.pyc`.

- [ ] **Step 2:** Escribir `config/legisladores.json` con las 18 personas del spec §7.1.
  - `nombre_portal` va en formato `"Apellido, Nombres"`, sin tildes, como lo escribe el portal (por ejemplo `"Bria, Jose Alberto"`).
  - `nombre_mostrar` va con tildes (por ejemplo `"José Alberto Bría"`).
  - `busqueda` es `[apellido sin tilde]`; para Gudiño es `["Gudiño", "Gudino"]`.
  - `departamental` es `true` para Valiente, Nigro, Jaimes, Luna, Saliba, Grich, Briner, Molina y Carignano.

- [ ] **Step 3:** Escribir `config/etapas.json`.

```json
{
  "estados": {
    "Ingresado":            {"etapa": 1, "texto": "Se presentó el proyecto"},
    "Estado Parlamentario": {"etapa": 1, "texto": "Se informó en la sesión (tomó estado parlamentario)"},
    "En Comisión":          {"etapa": 2, "texto": "Pasó a estudio en comisión"},
    "Aprobado":             {"etapa": 4, "resultado": "aprobado",  "texto": "Fue aprobado"},
    "Caducado":             {"etapa": 4, "resultado": "caduco",    "texto": "Caducó: pasaron 12 meses sin tratarse"},
    "Rehabilitado":         {"etapa": 2, "resultado": null,        "texto": "Se rehabilitó: vuelve a estar en comisión"},
    "Archivado":            {"etapa": 4, "resultado": "archivado", "texto": "Se archivó"}
  },
  "situaciones": {
    "Art 110 (tramite normal)": {"texto": "Sigue el trámite normal"},
    "Sobre Tablas":             {"texto": "Se trató sobre tablas: se votó el mismo día, sin pasar por comisión", "sobre_tablas": true}
  },
  "nombres_etapa": {"1": "Presentado", "2": "En estudio en comisión", "3": "Con dictamen de comisión", "4": "Resultado"}
}
```

- [ ] **Step 4:** Escribir `config/ajustes.json`: `{"pausa_segundos": 1.0, "desde_anio": 24, "dias_por_caducar": 60, "dias_novedades": 30, "dias_desactualizado": 2}`.

- [ ] **Step 5:** Escribir los tests que deben fallar.

```python
def test_config_tiene_18_legisladores_con_slug_unico(): cfg = cargar_config(RAIZ); assert len(cfg.legisladores) == 18; assert len({l.slug for l in cfg.legisladores}) == 18
def test_departamentales(): assert {l.slug for l in cfg.legisladores if l.departamental} == {"valiente","nigro","jaimes","luna","saliba","grich","briner","molina","carignano"}
def test_normalizar(): assert normalizar("  Bría,  José Alberto ") == "bria, jose alberto"; assert normalizar("Gudiño") == "gudino"
def test_es_autor_ignora_tildes(): assert bria.es_autor("Bria, Jose Alberto") and bria.es_autor("BRÍA, José Alberto") and not bria.es_autor("Bria, Otro")
def test_decodificar_cp1252(): assert decodificar("Comisión".encode("cp1252")) == "Comisión"
```

- [ ] **Step 6:** Correr `.venv/Scripts/python -m pytest tests -q`. Resultado esperado: FAIL por import.

- [ ] **Step 7:** Implementar `util.py` y `config.py`.

- [ ] **Step 8:** Correr `pytest`. Resultado esperado: PASS.

- [ ] **Step 9:** Commit con el mensaje "Configuración del bloque y utilidades". El commit incluye `docs/`.

---

### Task 2: Cliente del portal, fixtures reales y sondeo desde GitHub

**Files:**
- Create: `recolector/portal.py`, `herramientas/capturar_fixtures.py`, `tests/fixtures/`, `.github/workflows/sondeo.yml`
- Test: `tests/test_portal.py`

**Interfaces:**
- Consumes: `decodificar` (Task 1).
- Produces:
  - `class PortalError(Exception)`.
  - `class Portal(pausa: float = 1.0, sesion: requests.Session | None = None)`.
    - `buscar(q: str) -> str`: hace GET y guarda el HTML y los campos ocultos.
    - `postback(target: str) -> str`: hace POST con `__EVENTTARGET` y los campos ocultos. Si la respuesta trae campos ocultos nuevos, reemplaza el estado.
    - `pagina_siguiente() -> str | None`: devuelve el HTML de la página siguiente o `None` si no hay más.
    - `get(url: str) -> str`.
  - Constante `TARGET_AUTORES = "ctl00$Body$R_Results$ctl{:02d}$LB_Autores"`, y lo mismo para `TARGET_RUTA` y `TARGET_COMISIONES`.

- [ ] **Step 1:** Escribir `herramientas/capturar_fixtures.py`. Se usa por única vez y guarda `.content` en bytes crudos.
  - `buscar_ferrero_p1.html` y `buscar_ferrero_p2.html`: la página 2 se obtiene siguiendo el paginador.
  - `buscar_numero_38560.html`: `q=38560/L/24`.
  - `autores_42894.html`.
  - `ruta_28243_aprobado_sobre_tablas.html`.
  - `ruta_38560_caducado_rehabilitado.html`.
  - `ruta_46709_en_comision.html`.
  - `comisiones_46709.html`.
  - Una ruta que tenga **Despachos no vacío**: hay que buscarla entre las leyes aprobadas del bloque, por ejemplo con `q="Proyecto de Ley" Ferrero`, recorriendo hasta encontrar Aprobado con despacho. El archivo se llama `ruta_con_despacho.html`.
  - `legisladores_oficial.html`, de `https://legislaturacba.gob.ar/legisladores/`.
  - Del HTML de la página 1 se identifica el `__doPostBack` del paginador ("siguiente" o el número de página) y se anota como constante en `portal.py`.

- [ ] **Step 2:** Correr el script y verificar que existan los 10 archivos y que `buscar_ferrero_p2.html` traiga números distintos de la página 1.

- [ ] **Step 3:** Escribir los tests con un `requests.Session` falso, un stub que devuelve los fixtures.

```python
def test_postback_envia_viewstate_de_la_ultima_respuesta(): # el POST lleva __VIEWSTATE de buscar_ferrero_p1 y __EVENTTARGET pedido
def test_pausa_entre_consultas(): # con pausa=1.0 y un reloj falso, entre dos llamadas pasa ≥1.0 s
def test_reintenta_y_luego_falla(): # 4 respuestas 503 → PortalError; esperas 5, 15, 45 s (sleep falso)
def test_pagina_siguiente_none_en_ultima(): # HTML sin el enlace de siguiente → None
```

- [ ] **Step 4:** Correr `pytest tests/test_portal.py`. Resultado esperado: FAIL.

- [ ] **Step 5:** Implementar `portal.py`. `time.sleep` y `time.monotonic` se inyectan por parámetro para poder testear.

- [ ] **Step 6:** Correr `pytest`. Resultado esperado: PASS.

- [ ] **Step 7:** Escribir `.github/workflows/sondeo.yml`.
  - Se dispara con `workflow_dispatch`.
  - Usa `actions/setup-python` con Python 3.12 e instala `requirements.txt`.
  - Corre `python -c` con `Portal().buscar("Ferrero")` y una ruta.
  - Imprime la cantidad de expedientes encontrados.

- [ ] **Step 8:** **Acción del usuario, guiada paso a paso:**
  - Crear el repositorio **público** `seguimiento-proyectos-ucr` en su cuenta de GitHub.
  - Correr `git remote add origin …` y `git push`.
  - En la pestaña Actions, ejecutar "sondeo".
  - Resultado esperado: el log muestra 10 expedientes y una ruta con "Estado:".
  - **Si el portal bloquea o no responde desde GitHub, se frena el plan y se consulta al usuario** (spec §8).

- [ ] **Step 9:** Commit con el mensaje "Cliente del portal y fixtures reales".

---

### Task 3: Parsers del HTML

**Files:**
- Create: `recolector/parse.py`
- Test: `tests/test_parse.py`

**Interfaces:**
- Consumes: `tests/fixtures/*` (Task 2).
- Produces:
  - `Evento(tipo: Literal["Estado","Situación"], valor: str, sesion: str | None, periodo: int | None, fecha: date | None)`.
  - `Documento(seccion: Literal["Anexos","Actas","Despachos","Texto aprobado"], nombre: str, url: str)`.
  - `Ruta(eventos: list[Evento], documentos: list[Documento])`, con la propiedad `tiene_despacho: bool`.
  - `Resultado(numero: str, extracto: str, posicion: int)`.
  - `parse_resultados(html) -> list[Resultado]`, `parse_autores(html) -> list[str]`, `parse_comisiones(html) -> list[str]` y `parse_ruta(html) -> Ruta`.
  - Todas las funciones lanzan `PortalError` (de `portal.py`) cuando no está el contenedor esperado: es la señal de que el portal cambió.

- [ ] **Step 1:** Escribir los tests que deben fallar, con valores tomados de lo ya observado.

```python
def test_resultados_ferrero_p1(): r = parse_resultados(fx("buscar_ferrero_p1.html")); assert len(r) == 10; assert r[0].numero.count("/") == 2; assert [x.posicion for x in r] == list(range(10))
def test_autores_42894(): a = parse_autores(fx("autores_42894.html")); assert len(a) == 16; assert a[0] == "Ferrero, Alejandra"; assert "Bria, Jose Alberto" in a
def test_ruta_sobre_tablas(): ev = parse_ruta(fx("ruta_28243_aprobado_sobre_tablas.html")).eventos; assert [e.valor for e in ev if e.tipo=="Estado"] == ["Ingresado","Estado Parlamentario","En Comisión","Aprobado"]; assert ev[-1].valor == "Sobre Tablas"; assert ev[0].fecha == date(2019,6,5) and ev[0].periodo == 141
def test_ruta_evento_sin_sesion(): ev = parse_ruta(fx("ruta_38560_caducado_rehabilitado.html")).eventos; assert ev[0].valor == "Ingresado" and ev[0].sesion is None; cad = next(e for e in ev if e.valor=="Caducado"); assert cad.fecha == date(2025,2,17) and cad.sesion is None
def test_ruta_con_despacho(): assert parse_ruta(fx("ruta_con_despacho.html")).tiene_despacho
def test_ruta_sin_despacho(): assert not parse_ruta(fx("ruta_46709_en_comision.html")).tiene_despacho
def test_comisiones_46709(): assert len(parse_comisiones(fx("comisiones_46709.html"))) >= 1
def test_decodificacion_cp1252(): assert "Comisión" in [e.valor for e in parse_ruta(fx("ruta_46709_en_comision.html")).eventos]
def test_html_inesperado_lanza(): with pytest.raises(PortalError): parse_ruta("<html><body>mantenimiento</body></html>")
```

- [ ] **Step 2:** Correr `pytest tests/test_parse.py`. Resultado esperado: FAIL.

- [ ] **Step 3:** Implementar con BeautifulSoup.
  - La sesión se extrae con la regex `Sesión (\w+) (\d+) del Período (\d+) \((\d\d/\d\d/\d{4})\)`, más el caso con solo fecha `\((\d\d/\d\d/\d{4})\)`.
  - Los links de documentos se vuelven absolutos con base `https://gld.legislaturacba.gob.ar/`.

- [ ] **Step 4:** Correr `pytest`. Resultado esperado: PASS.

- [ ] **Step 5:** Commit con el mensaje "Parsers del portal".

---

### Task 4: Etapas, caducidad y línea de tiempo

**Files:**
- Create: `recolector/etapas.py`
- Test: `tests/test_etapas.py`

**Interfaces:**
- Consumes: `Ruta` y `Evento` (Task 3), y `Config.etapas` (Task 1).
- Produces:
  - `tipo_de(numero: str) -> Literal["ley","resolucion","declaracion","otros"]`: L, R y D según la letra; el resto es `otros`.
  - `EstadoExp(etapa: int, etapa_nombre: str, resultado: str | None, sobre_tablas: bool, ingreso: date | None, ultimo_movimiento: dict | None, caduca_el: date | None, desconocidos: list[str])`. `ultimo_movimiento` tiene la forma `{"fecha": iso|None, "texto": str}`.
  - `calcular_estado(ruta: Ruta, mapeo: dict) -> EstadoExp`.
  - `linea_tiempo(ruta: Ruta, mapeo: dict) -> list[dict]`. Cada elemento es `{"fecha": iso|None, "texto": str, "detalle": str|None}`, donde `detalle` es la sesión original.

Reglas, en este orden:
1. Se recorren los eventos en orden. Cada Estado conocido fija `etapa` y `resultado`; Rehabilitado lo pone en `None`.
2. Si `resultado` es None y `ruta.tiene_despacho`, la etapa es `max(etapa, 3)`.
3. `sobre_tablas` vale si aparece alguna situación con `sobre_tablas: true`.
4. `ingreso` es la primera fecha no nula entre Ingresado y Estado Parlamentario.
5. `caduca_el` solo se calcula si `resultado is None` y la etapa es 2 o 3: es la fecha del último Rehabilitado, o si no hay, `ingreso`, más 12 meses. Si cae en un día que no existe, se usa el último día del mes. Si no hay fecha base, queda `None`.
6. Un valor que no está en el mapeo se agrega a `desconocidos`. En la línea de tiempo aparece con su texto crudo y no cambia la etapa.

- [ ] **Step 1:** Escribir los tests que deben fallar. Usan los fixtures parseados y `Ruta` armadas a mano.

```python
def test_sobre_tablas_aprobado(): e = calcular_estado(ruta_28243, M); assert (e.etapa, e.resultado, e.sobre_tablas) == (4, "aprobado", True); assert e.caduca_el is None
def test_en_comision_caduca_en_12_meses(): e = calcular_estado(ruta_46709, M); assert e.etapa == 2 and e.caduca_el == date(2027,6,25)
def test_con_despacho_etapa_3(): # ruta armada: En Comisión + documento Despachos, sin Aprobado → etapa 3
def test_rehabilitado_vuelve_a_comision(): # Ingresado(2024-02-14)…Caducado(2025-02-17), Rehabilitado(2025-03-05) → etapa 2, resultado None, caduca_el 2026-03-05
def test_caducado_sin_rehabilitar(): # → etapa 4, resultado "caduco", caduca_el None
def test_estado_desconocido(): # Estado "Reservado en Secretaría" → desconocidos == ["Reservado en Secretaría"], etapa sin cambio, aparece en linea_tiempo con texto crudo
def test_tipo_de(): assert [tipo_de(n) for n in ["1/L/26","1/R/26","1/D/26","1/N/26"]] == ["ley","resolucion","declaracion","otros"]
def test_linea_tiempo_textos_simples(): assert linea_tiempo(ruta_46709, M)[-1]["texto"] == "Pasó a estudio en comisión"
```

- [ ] **Step 2:** Correr `pytest tests/test_etapas.py`. Resultado esperado: FAIL.

- [ ] **Step 3:** Implementar `etapas.py` según las reglas.

- [ ] **Step 4:** Correr `pytest`. Resultado esperado: PASS.

- [ ] **Step 5:** Commit con el mensaje "Etapas y caducidad en lenguaje simple".

---

### Task 5: Almacén de datos (JSON, índice, novedades y estado)

**Files:**
- Create: `recolector/almacen.py`
- Test: `tests/test_almacen.py`

**Interfaces:**
- Consumes: `Ruta` (Task 3), `calcular_estado`, `linea_tiempo` y `tipo_de` (Task 4), `Legislador` (Task 1).
- Produces:
  - `Expediente(numero: str, extracto: str, autores: list[str], comisiones: list[str], ruta: Ruta, recolectado: datetime)`.
  - `id_archivo(numero) -> str`: `"48498/L/26"` → `"48498-L-26"`.
  - `guardar_expediente(dir_datos: Path, exp: Expediente, mapeo: dict, hoy: date) -> list[str]`.
    - Escribe `expedientes/<id>.json`.
    - Devuelve los textos de los eventos nuevos respecto del archivo anterior (comparando `(tipo, valor, fecha)`). Si el expediente es nuevo, devuelve `["Nuevo proyecto en seguimiento"]`.
  - `cargar_expediente(dir_datos, numero) -> dict | None`.
  - `agregar_novedades(dir_datos, numero, textos, hoy, dias: int) -> None`: agrega a `novedades.json` y poda lo anterior a `hoy - dias`.
  - `construir_indice(dir_datos, legisladores, mapeo, ajustes, hoy, ahora) -> dict`: escribe `indice.json`.
  - `escribir_estado(dir_datos, ok: bool, advertencias: list[str], ahora: datetime) -> None`. Si `ok` es False, conserva el `ultima_actualizacion_ok` anterior.
  - `cargar_descartados(dir_datos) -> set[str]` y `guardar_descartados(dir_datos, s: set[str])`.

**Formato de los archivos** (es el contrato con el sitio, Tasks 7 y 8):

```jsonc
// expedientes/48498-L-26.json
{"numero":"48498/L/26","tipo":"ley","extracto":"…","autores":["Ferrero, Alejandra", "…"],"comisiones":["…"],
 "estado":{"etapa":2,"etapa_nombre":"En estudio en comisión","resultado":null,"sobre_tablas":false,"ingreso":"2026-10-29",
           "ultimo_movimiento":{"fecha":"2026-10-29","texto":"Pasó a estudio en comisión"},"caduca_el":"2027-10-29"},
 "linea_tiempo":[{"fecha":"2026-10-29","texto":"Se presentó el proyecto","detalle":"Sesión Ordinaria 18 del Período 148"}],
 "eventos_crudos":[{"tipo":"Estado","valor":"Ingresado","sesion":"…","periodo":148,"fecha":"2026-10-29"}],
 "documentos":[{"seccion":"Despachos","nombre":"…","url":"https://…"}],
 "url_portal":"https://gld.legislaturacba.gob.ar/Publics/Buscar.aspx?q=48498%2FL%2F26",
 "recolectado":"2026-11-24T07:10:00-03:00"}
// indice.json
{"generado":"…","ajustes":{…ajustes.json…},
 "legisladores":[{"slug":"ferrero","nombre":"Alejandra Ferrero","departamental":false,"expedientes":["48498/L/26"]}],
 "expedientes":{"48498/L/26":{"tipo":"ley","titulo":"<extracto recortado a 140 car. sin cortar palabras + …>",
   "autores_bloque":["ferrero"],"estado":{…igual que arriba…}}}}
// novedades.json
[{"numero":"48498/L/26","fecha":"2026-11-24","texto":"Pasó a estudio en comisión"}]
// estado.json
{"ultima_corrida":"…","ultima_actualizacion_ok":"…","ok":true,"advertencias":["Estado desconocido: …"]}
```

- [ ] **Step 1:** Escribir los tests que deben fallar, usando `tmp_path`.

```python
def test_guardar_nuevo_devuelve_nuevo(): assert guardar_expediente(tmp, exp, M, HOY) == ["Nuevo proyecto en seguimiento"]
def test_guardar_detecta_evento_nuevo(): # 2ª versión con Caducado extra → ["Caducó: pasaron 12 meses sin tratarse"]
def test_guardar_sin_cambios_devuelve_vacio(): ...
def test_novedades_poda_30_dias(): ...
def test_indice_expediente_en_dos_legisladores(): # autores Ferrero y Bria → aparece en ambos y una sola vez en "expedientes"; autores_bloque == ["bria","ferrero"] ordenado
def test_titulo_recortado_140(): ...
def test_estado_fallido_conserva_ultima_ok(): escribir_estado(tmp, True, [], T1); escribir_estado(tmp, False, ["x"], T2); d = json(tmp/"estado.json"); assert d["ultima_actualizacion_ok"] == T1.isoformat() and d["ok"] is False
def test_json_utf8_sin_escapar(): # el archivo contiene "Comisión" literal (ensure_ascii=False)
```

- [ ] **Step 2:** Correr `pytest tests/test_almacen.py`. Resultado esperado: FAIL.

- [ ] **Step 3:** Implementar. Escritura atómica: se escribe en `.tmp` y después se hace `os.replace`.

- [ ] **Step 4:** Correr `pytest`. Resultado esperado: PASS.

- [ ] **Step 5:** Commit con el mensaje "Almacén de datos en JSON".

---

### Task 6: Corrida completa, verificación del bloque y CLI

**Files:**
- Create: `recolector/corrida.py`, `recolector/bloque.py`, `recolector/__main__.py`
- Test: `tests/test_corrida.py`, `tests/test_bloque.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces:
  - `verificar_bloque(html: str, legisladores) -> list[str]`.
    - Lee los `span.premium-gallery-img-name` cuyo item tenga la clase `unión-cívica-radical`.
    - Normaliza "NN- Apellido Nombres" y lo compara con `nombre_portal` (sin la coma).
    - Devuelve advertencias del tipo "Nuevo en el bloque según la web oficial: …" o "Ya no figura en el bloque: …".
  - `descubrir(portal, leg, conocidos: set[str], descartados: set[str], desde_anio: int, max_paginas: int | None) -> list[tuple[str, str, list[str]]]`.
    - Devuelve `(numero, extracto, autores)` para cada expediente nuevo del legislador.
    - Consulta los autores solo de los números con año ≥ `desde_anio` que no estén en `conocidos` ni en `descartados`.
    - Si los autores no incluyen a nadie del bloque, el número va a `descartados`.
    - Si los incluyen, se devuelve, aunque el autor sea otro legislador del bloque.
    - Si hay 0 resultados y el legislador ya tenía expedientes en `conocidos`, lanza `PortalError`.
  - `actualizar(portal, numero) -> tuple[str, Ruta, list[str]]`: busca `q=numero`, toma el resultado cuyo número coincide y hace los postbacks de Ruta y Comisiones. Devuelve `(extracto, ruta, comisiones)`.
  - `correr(raiz: Path, portal, hoy: date, ahora: datetime, solo: str | None, max_paginas: int | None, completo: bool) -> int`. Devuelve el código de salida.
    - Primero hace el descubrimiento por legislador y guarda el progreso después de cada uno.
    - Después actualiza las rutas: todos los no finales; los caducados, solo los lunes o con `completo`.
    - Al final construye el índice y escribe el estado.
    - Los lunes o con `completo` corre también `verificar_bloque`.
    - Cualquier `PortalError` deja `escribir_estado(ok=False)` y devuelve 1, sin borrar datos.
    - Si hay valores desconocidos o cambios en el bloque, los agrega a `advertencias` y a `$GITHUB_STEP_SUMMARY` si existe.
  - CLI: `python -m recolector [--solo SLUG] [--max-paginas N] [--completo] [--pausa S]`.

- [ ] **Step 1:** Escribir los tests que deben fallar. Usan un `PortalFalso` que sirve fixtures por target.

```python
def test_bloque_sin_cambios(): assert verificar_bloque(fx("legisladores_oficial.html"), cfg.legisladores) == []
def test_bloque_detecta_faltante(): # quitar Bottasso de la config → ["Nuevo en el bloque según la web oficial: Bottasso Gustavo Armando"]
def test_descubrir_filtra_anio_y_descartados(): # resultados con /19 no consultan autores; número en descartados no consulta autores
def test_descubrir_incluye_coautor_del_bloque(): # 42894/N/25 buscado por "Ferrero" → incluido
def test_cero_resultados_es_error(): # conocidos contiene expedientes de ferrero y la búsqueda devuelve 0 → PortalError; correr() devuelve 1 y estado.json ok False
def test_correr_no_reconsulta_finales(): # expediente Aprobado no llama actualizar()
def test_caducados_solo_lunes(): # hoy martes → no actualiza caducado; lunes → sí
```

- [ ] **Step 2:** Correr `pytest`. Resultado esperado: FAIL.

- [ ] **Step 3:** Implementar `bloque.py`, `corrida.py` y `__main__.py`.

- [ ] **Step 4:** Correr `pytest`. Resultado esperado: PASS.

- [ ] **Step 5:** Hacer una prueba real acotada con `python -m recolector --solo ferrero --max-paginas 3`. Resultado esperado:
  - `sitio/data/indice.json` con al menos 1 expediente para ferrero.
  - `estado.json` con `ok: true`.
  - Revisar a mano un expediente contra el portal.

- [ ] **Step 6:** Commit con el mensaje "Corrida completa del recolector". Se incluyen los datos de prueba de `sitio/data`.

---

### Task 7: Lógica del sitio (funciones puras)

**Files:**
- Create: `sitio/js/logica.js`
- Test: `tests_js/logica.test.mjs`

**Interfaces:**
- Consumes: el formato de `indice.json`, `novedades.json` y `estado.json` (Task 5).
- Produces (exports de ES module; las fechas son strings ISO `YYYY-MM-DD`):
  - `fechaRelativa(fecha, hoy) -> string`: "hoy", "ayer", "hace N días" (menos de 60) o "hace N meses".
  - `diasHasta(fecha, hoy) -> number`.
  - `resumen(exps: object[], novedades: object[], hoy, ajustes)`. Devuelve `{novedades, porCaducar, enComision, aprobadosAnio}`, donde:
    - `novedades` cuenta expedientes distintos con novedad en los últimos 7 días.
    - `enComision` cuenta las etapas 2 y 3 sin resultado.
    - `aprobadosAnio` cuenta los que tienen `resultado == "aprobado"` y el último movimiento en el año de `hoy`.
  - `filtrar(exps, {pestania, tarjeta, texto}, novedades, hoy, ajustes) -> object[]`.
    - `pestania` puede ser `"fondo"` (ley y resolución), `"declaraciones"` u `"otros"`.
    - `tarjeta` puede ser `null`, `"novedades"`, `"porCaducar"`, `"enComision"`, `"aprobados"` o `"caducados"`. Si hay tarjeta, se ignora la pestaña.
    - `texto` busca en número y título, normalizado sin tildes.
  - `ordenar(exps, novedades, hoy) -> object[]`: primero los que tienen novedad en 7 días, después por `ultimo_movimiento.fecha` descendente; los `null` van al final.
  - `estaDesactualizado(estado, hoy, diasHabiles) -> boolean`: cuenta días hábiles (lunes a viernes) entre `ultima_actualizacion_ok` y `hoy`.

- [ ] **Step 1:** Escribir los tests que deben fallar.

```js
test("fechaRelativa", () => { eq(fechaRelativa("2026-11-24","2026-11-24"),"hoy"); eq(fechaRelativa("2026-11-18","2026-11-24"),"hace 6 días"); eq(fechaRelativa("2026-06-24","2026-11-24"),"hace 5 meses"); });
test("porCaducar usa 60 días y excluye resueltos", ...);
test("filtrar por texto ignora tildes", () => { /* "comision" encuentra "Comisión" */ });
test("tarjeta ignora pestaña", ...);
test("ordenar: novedades primero, null al final", ...);
test("desactualizado: viernes→lunes son 1 día hábil (no desactualizado); miércoles→lunes sí", ...);
```

- [ ] **Step 2:** Correr `node --test tests_js/`. Resultado esperado: FAIL.

- [ ] **Step 3:** Implementar `logica.js`, sin dependencias.

- [ ] **Step 4:** Correr `node --test tests_js/`. Resultado esperado: PASS.

- [ ] **Step 5:** Commit con el mensaje "Lógica del sitio".

---

### Task 8: Interfaz del sitio

**Files:**
- Create: `sitio/index.html`, `sitio/estilos.css`, `sitio/js/vistas.js`, `sitio/js/app.js`, `sitio/data/glosario.json`, `.claude/launch.json`
- Test: verificación en el navegador de vista previa con los datos reales del Task 6.

**Interfaces:**
- Consumes: `logica.js` (Task 7) y los JSON (Task 5).
- Produces: las rutas por hash `#/` (elegir legislador), `#/leg/<slug>`, `#/exp/<id-archivo>`, `#/bloque` y `#/como-funciona`. El legislador elegido se guarda en `localStorage["leg"]`. `?leg=<slug>` en la URL redirige a `#/leg/<slug>`.

Antes de diseñar, cargar el skill `frontend-design:frontend-design`. Las pantallas son las del spec §7.3:
- **Elegir legislador:** grilla de nombres. Los departamentales llevan una marca.
- **Mis proyectos:**
  - 4 tarjetas resumen: Novedades, Por caducar, En comisión y Aprobados este año. Funcionan como botones de filtro y se puede ver cuál está activo.
  - Pestañas: "Leyes y resoluciones", "Declaraciones" y "Otros".
  - Un buscador.
  - Una lista de tarjetas. Cada una muestra el tipo como etiqueta con texto, el título, el número, una barra de 4 pasos con el nombre del paso actual en texto, el último movimiento con fecha relativa, y "caduca aprox. en N días" si corresponde.
  - Los caducados se ven con un filtro aparte, "Ver caducados", que incluye una explicación.
- **Ficha:**
  - Extracto completo, barra de etapas y línea de tiempo vertical.
  - Autores: los del bloque, resaltados.
  - Comisiones y documentos con link.
  - "Ver en el portal oficial".
  - "¿Qué significa?" junto a cada término del glosario, con `<details>` accesible.
- **Bloque:** la misma lista sobre todos los expedientes, con selects de legislador y de comisión.
- **¿Cómo funciona un proyecto?:** diagrama de 4 etapas hecho con HTML/CSS, más el glosario completo.
- **Pie de página:** "Datos al <fecha> · Fuente: Legislatura de Córdoba (GLD)". Si `estaDesactualizado`, aparece arriba un banner visible: "Los datos están desactualizados desde <fecha>".
- **Glosario** (`glosario.json`, con textos de 1 a 2 oraciones en castellano llano): estado parlamentario, comisión, giro a comisión, despacho o dictamen, sobre tablas, trámite normal (Art. 110), caducidad, rehabilitación, archivo, ley, resolución, declaración y pedido de informes.
- **Diseño:** el contraste cumple WCAG AA, se respeta `prefers-color-scheme` y el sitio funciona sin conexión externa (sin CDNs). La ficha de un expediente se carga con fetch a demanda.

- [ ] **Step 1:** Crear `.claude/launch.json` con un servidor estático: `python -m http.server 8000 -d sitio`.

- [ ] **Step 2:** Implementar las pantallas.

- [ ] **Step 3:** Verificar en la vista previa:
  - Elegir ferrero y que las tarjetas y la lista coincidan con `indice.json`.
  - Que al tocar "Por caducar" se filtre la lista.
  - Que la ficha muestre la línea de tiempo.
  - Que con `estado.json` modificado a una fecha vieja aparezca el banner.
  - Que en mobile (375 px) no haya scroll horizontal.
  - Que el modo oscuro se lea bien.
  - Que la consola no tenga errores.

- [ ] **Step 4:** Mostrarle capturas al usuario y ajustar según lo que diga.

- [ ] **Step 5:** Commit con el mensaje "Interfaz del sitio".

---

### Task 9: Publicación automática y guía de mantenimiento

**Files:**
- Create: `.github/workflows/actualizar.yml`, `README.md`, `MANTENIMIENTO.md`
- Delete: `.github/workflows/sondeo.yml`

**Interfaces:**
- Consumes: el CLI (Task 6) y `sitio/` (Task 8).

- [ ] **Step 1:** Escribir `actualizar.yml`.
  - Disparadores: `schedule: cron "0 10 * * 1-5"` (7:00 en Argentina) y `workflow_dispatch` con el input `completo` (boolean).
  - Permisos: `contents: write`, `pages: write` e `id-token: write`.
  - `concurrency: actualizar`.
  - `timeout-minutes: 350`.
  - Pasos:
    1. checkout, setup-python 3.12 e instalar dependencias.
    2. `python -m recolector` (más `--completo` si el input lo pide).
    3. Hacer commit de `sitio/data` si hay cambios. Se ejecuta con `if: always()`, para guardar el progreso parcial.
    4. Si la corrida salió bien, `actions/upload-pages-artifact` con `path: sitio` y luego `actions/deploy-pages`.
    5. Si la corrida falló, el job termina en rojo y GitHub le manda un mail al dueño.

- [ ] **Step 2:** Escribir `MANTENIMIENTO.md` en castellano llano.
  - Cómo agregar o quitar un legislador (editar `config/legisladores.json` desde la web de GitHub).
  - Cómo forzar una actualización (Actions → actualizar → Run workflow, con "completo" para la primera carga).
  - Qué hacer si llega el mail de falla.
  - Qué significan las advertencias.
  - Cómo cambiar los ajustes (60 días, etc.).

- [ ] **Step 3:** Escribir `README.md`: qué es, el link al sitio y cómo correrlo localmente.

- [ ] **Step 4:** **Acción del usuario, guiada:**
  - Settings → Pages → Source: "GitHub Actions".
  - Hacer push.
  - Correr "actualizar" con `completo=true`, que es la primera carga.
  - Resultado esperado: el job termina en verde. Si se corta por tiempo, se vuelve a correr y continúa desde el progreso guardado.
  - El sitio responde en `https://<usuario>.github.io/seguimiento-proyectos-ucr/`.

- [ ] **Step 5:** Verificar el sitio publicado:
  - Los 18 legisladores aparecen en la portada.
  - Revisar a mano 3 expedientes contra el portal oficial.
  - `estado.json` con `ok: true`.

- [ ] **Step 6:** Commit y push con el mensaje "Publicación diaria y guía de mantenimiento".
