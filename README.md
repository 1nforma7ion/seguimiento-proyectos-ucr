# Seguimiento de proyectos del bloque UCR

Este sitio muestra a cada legislador del bloque UCR de la Legislatura de Córdoba el estado de los proyectos que firmó, en lenguaje simple. Los datos salen del portal público de Gestión Legislativa Digital y se actualizan solos todos los días hábiles.

Para mantenerlo, ver [MANTENIMIENTO.md](MANTENIMIENTO.md).

## Cómo está armado

- `recolector/`: programa en Python que lee el portal y escribe los JSON en `sitio/data/`.
- `sitio/`: página estática (HTML, CSS y JS, sin compilación) que lee esos JSON.
- `config/`: legisladores del bloque, traducción de estados a etapas y ajustes.
- `.github/workflows/actualizar.yml`: la corrida diaria y la publicación en GitHub Pages.
- `docs/superpowers/`: el diseño y el plan de construcción.

## Correrlo en la computadora

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt     # en Linux o Mac: .venv/bin/pip
.venv/Scripts/python -m recolector --solo ferrero --max-nuevos 20   # prueba chica
.venv/Scripts/python -m http.server 8000 -d sitio                  # y abrir http://localhost:8000
```

Pruebas:

```bash
.venv/Scripts/python -m pytest -q
node --test "tests_js/*.test.mjs"
```
