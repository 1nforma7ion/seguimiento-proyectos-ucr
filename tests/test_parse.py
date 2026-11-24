from datetime import date

import pytest

from conftest import fx
from recolector.parse import (parse_autores, parse_comisiones, parse_resultados, parse_ruta,
                              parse_total)
from recolector.portal import PortalError


def test_resultados_pagina_completa():
    r = parse_resultados(fx("buscar_autor_ferrero_p1.html"))
    assert len(r) == 10
    assert [x.posicion for x in r] == list(range(10))
    assert all(x.numero.count("/") == 2 for x in r)
    assert r[0].numero == "48474/D/26"
    assert r[0].extracto.startswith("Proyecto de Declaración, iniciado por los Legisladores Ferrero")
    assert "Nicolás" in r[0].extracto


def test_total():
    assert parse_total(fx("buscar_autor_ferrero_p1.html")) == 694
    assert parse_total(fx("consulta_ferrero_16a31oct2026.html")) == 27
    assert parse_total(fx("buscar_vacio.html")) == 0


def test_total_singular():
    assert parse_total('<span id="Body_L_Results">1 resultado (0.426 segundos)</span>') == 1
    assert parse_total('<span id="Body_L_Results">1.204 resultados (0.4 segundos)</span>') == 1204


def test_resultados_vacio():
    assert parse_resultados(fx("buscar_vacio.html")) == []


def test_autores_42894():
    a = parse_autores(fx("autores_42894.html"))
    assert len(a) == 16
    assert a[0] == "Ferrero, Alejandra"
    assert "Bria, Jose Alberto" in a


def test_ruta_sobre_tablas():
    ev = parse_ruta(fx("ruta_28243_aprobado_sobre_tablas.html")).eventos
    assert [e.valor for e in ev if e.tipo == "Estado"] == [
        "Ingresado", "Estado Parlamentario", "En Comisión", "Aprobado"]
    assert ev[-1].tipo == "Situación" and ev[-1].valor == "Sobre Tablas"
    assert ev[0].fecha == date(2019, 6, 5) and ev[0].periodo == 141
    assert ev[0].sesion == "Sesión Ordinaria 16 del Período 141"


def test_ruta_evento_sin_sesion():
    ev = parse_ruta(fx("ruta_38560_caducado_rehabilitado.html")).eventos
    assert ev[0].valor == "Ingresado" and ev[0].sesion is None and ev[0].fecha is None
    cad = next(e for e in ev if e.valor == "Caducado")
    assert cad.fecha == date(2025, 2, 17) and cad.sesion is None
    reh = next(e for e in ev if e.valor == "Rehabilitado")
    assert reh.fecha == date(2025, 4, 9) and reh.periodo == 147


def test_ruta_con_despacho():
    ruta = parse_ruta(fx("ruta_con_despacho.html"))
    assert ruta.tiene_despacho
    desp = [d for d in ruta.documentos if d.seccion == "Despachos"]
    assert desp[0].nombre == "Despacho de Comisión por Art. 101 (9/4/2024)"
    ta = [d for d in ruta.documentos if d.seccion == "Texto aprobado"]
    assert ta[0].url == "https://gld.legislaturacba.gob.ar/Handlers/PDF.ashx?id=07WeHO9x6lc="


def test_ruta_sin_despacho():
    ruta = parse_ruta(fx("ruta_46709_en_comision.html"))
    assert not ruta.tiene_despacho
    assert ruta.documentos == []


def test_comisiones_46709():
    assert parse_comisiones(fx("comisiones_46709.html")) == [
        "Asuntos Constitucionales, Justicia y Acuerdos", "Legislación General"]


def test_decodificacion_utf8():
    assert "En Comisión" in [e.valor for e in parse_ruta(fx("ruta_46709_en_comision.html")).eventos]


@pytest.mark.parametrize("funcion", [parse_ruta, parse_autores, parse_comisiones, parse_total])
def test_html_inesperado_lanza(funcion):
    with pytest.raises(PortalError):
        funcion("<html><body>mantenimiento</body></html>")
