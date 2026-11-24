"""Baja HTML real del portal a tests/fixtures. Uso manual: python herramientas/capturar_fixtures.py"""
import re
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from recolector.portal import (TARGET_AUTORES, TARGET_COMISIONES, TARGET_RUTA,  # noqa: E402
                               Portal)

DESTINO = RAIZ / "tests" / "fixtures"
NUM = re.compile(r"\b\d{4,5}/[A-Z]/\d{2}\b")


def guardar(nombre: str, html: str):
    (DESTINO / nombre).write_bytes(html.encode("utf-8"))
    print("guardado", nombre, len(html))


def numeros(html: str) -> list[str]:
    return [n for n in NUM.findall(html) if not n.startswith("00000")]


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    p = Portal(pausa=1.0)

    p1 = p.consultar_autor(2950, date(2023, 12, 10), date(2027, 1, 1))
    guardar("buscar_autor_ferrero_p1.html", p1)
    p2 = p.ir_a_pagina(2)
    guardar("buscar_autor_ferrero_p2.html", p2)
    tras_autores = p.postback(TARGET_AUTORES.format(0))
    print("¿el postback de autores conserva la página 2?",
          numeros(tras_autores)[:3] == numeros(p2)[:3])

    for nombre, q, target in [
        ("buscar_numero_38560.html", "38560/L/24", None),
        ("autores_42894.html", "42894/N/25", TARGET_AUTORES),
        ("ruta_28243_aprobado_sobre_tablas.html", "28243/D/19", TARGET_RUTA),
        ("ruta_38560_caducado_rehabilitado.html", "38560/L/24", TARGET_RUTA),
        ("ruta_46709_en_comision.html", "46709/L/26", TARGET_RUTA),
        ("comisiones_46709.html", "46709/L/26", TARGET_COMISIONES),
        ("buscar_vacio.html", "zzqxwv sin resultados", None),
    ]:
        html = p.buscar(q)
        if target:
            idx = numeros(html).index(q)
            html = p.postback(target.format(idx))
        guardar(nombre, html)

    # Una ruta con despacho: recorrer las primeras páginas de Ferrero.
    html = p.consultar_autor(2950, date(2023, 12, 10), date(2027, 1, 1))
    for pagina in range(1, 6):
        if pagina > 1:
            html = p.ir_a_pagina(pagina)
        for i in range(min(10, len(numeros(html)))):
            ruta = p.postback(TARGET_RUTA.format(i))
            if "Sin despachos." not in ruta and "Despachos" in ruta:
                guardar("ruta_con_despacho.html", ruta)
                break
        else:
            continue
        break

    guardar("consulta_ferrero_16a31oct2026.html", p.consultar_autor(2950, date(2026, 10, 16), date(2026, 11, 1)))
    guardar("consulta_ferrero_1a16oct2026.html", p.consultar_autor(2950, date(2026, 10, 1), date(2026, 10, 16)))
    guardar("legisladores_oficial.html", p.get("https://legislaturacba.gob.ar/legisladores/"))


if __name__ == "__main__":
    main()
