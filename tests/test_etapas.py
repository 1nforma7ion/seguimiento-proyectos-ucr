from datetime import date

import pytest

from conftest import RAIZ, fx
from recolector.config import cargar_config
from recolector.etapas import calcular_estado, linea_tiempo, tipo_de
from recolector.parse import Documento, Evento, Ruta, parse_ruta

M = cargar_config(RAIZ).etapas


def E(valor, fecha=None, tipo="Estado", sesion=None):
    return Evento(tipo, valor, sesion, None, fecha)


def test_sobre_tablas_aprobado():
    e = calcular_estado(parse_ruta(fx("ruta_28243_aprobado_sobre_tablas.html")), M)
    assert (e.etapa, e.resultado, e.sobre_tablas) == (4, "aprobado", True)
    assert e.etapa_nombre == "Resultado"
    assert e.caduca_el is None
    assert e.ingreso == date(2019, 6, 5)


def test_en_comision_caduca_en_12_meses():
    e = calcular_estado(parse_ruta(fx("ruta_46709_en_comision.html")), M)
    assert e.etapa == 2 and e.resultado is None
    assert e.caduca_el == date(2027, 6, 25)
    assert e.ultimo_movimiento == {"fecha": "2026-06-25", "texto": "Pasó a estudio en comisión"}


def test_con_despacho_etapa_3():
    ruta = Ruta([E("Ingresado", date(2026, 3, 1)), E("En Comisión", date(2026, 3, 1))],
                [Documento("Despachos", "Despacho (1/4/2026)")])
    e = calcular_estado(ruta, M)
    assert e.etapa == 3 and e.etapa_nombre == "Con dictamen de comisión"
    assert e.caduca_el == date(2027, 3, 1)


def test_rehabilitado_vuelve_a_comision():
    ruta = Ruta([E("Ingresado"), E("Estado Parlamentario", date(2024, 2, 14)), E("En Comisión", date(2024, 2, 14)),
                 E("Caducado", date(2025, 2, 17)), E("Rehabilitado", date(2025, 3, 5))])
    e = calcular_estado(ruta, M)
    assert (e.etapa, e.resultado) == (2, None)
    assert e.caduca_el == date(2026, 3, 5)


def test_rehabilitado_real_del_portal():
    # 38560/L/24: caducó, se rehabilitó, volvió a caducar y se archivó por Art. 111.
    e = calcular_estado(parse_ruta(fx("ruta_38560_caducado_rehabilitado.html")), M)
    assert (e.etapa, e.resultado, e.desconocidos) == (4, "archivado", [])
    assert e.ultimo_movimiento["fecha"] == "2026-04-09"


def test_caducado_sin_rehabilitar():
    ruta = Ruta([E("Ingresado", date(2024, 2, 14)), E("En Comisión", date(2024, 2, 14)),
                 E("Caducado", date(2025, 2, 17))])
    e = calcular_estado(ruta, M)
    assert (e.etapa, e.resultado, e.caduca_el) == (4, "caduco", None)


def test_caducidad_29_de_febrero():
    ruta = Ruta([E("Ingresado", date(2024, 2, 29)), E("En Comisión", date(2024, 2, 29))])
    assert calcular_estado(ruta, M).caduca_el == date(2025, 2, 28)


def test_estado_desconocido():
    ruta = Ruta([E("Ingresado", date(2026, 3, 1)), E("En Comisión", date(2026, 3, 1)),
                 E("Reservado en Secretaría", date(2026, 4, 1))])
    e = calcular_estado(ruta, M)
    assert e.desconocidos == ["Reservado en Secretaría"]
    assert e.etapa == 2
    assert linea_tiempo(ruta, M)[-1]["texto"] == "Reservado en Secretaría"


def test_estado_que_no_mueve_la_etapa():
    ruta = Ruta([E("Ingresado", date(2026, 3, 1)), E("En Comisión", date(2026, 3, 1)),
                 E("Reservado en Secretaría Legislativa", date(2026, 4, 1))])
    e = calcular_estado(ruta, M)
    assert (e.etapa, e.desconocidos) == (2, [])


def test_rechazado():
    ruta = Ruta([E("Ingresado", date(2026, 3, 1)), E("Rechazado", date(2026, 5, 1))])
    assert calcular_estado(ruta, M).resultado == "rechazado"


def test_sin_eventos():
    e = calcular_estado(Ruta(), M)
    assert e.etapa == 1 and e.ultimo_movimiento is None and e.caduca_el is None


@pytest.mark.parametrize("numero,tipo", [("1/L/26", "ley"), ("1/R/26", "resolucion"),
                                         ("1/D/26", "declaracion"), ("1/N/26", "otros"), ("1/C/24", "otros")])
def test_tipo_de(numero, tipo):
    assert tipo_de(numero) == tipo


def test_linea_tiempo_textos_simples():
    lt = linea_tiempo(parse_ruta(fx("ruta_46709_en_comision.html")), M)
    assert lt[-1]["texto"] == "Pasó a estudio en comisión"
    assert lt[-1]["fecha"] == "2026-06-25"
    assert lt[-1]["detalle"] == "Sesión Ordinaria 10 del Período 148"


def test_linea_tiempo_situacion_traducida():
    lt = linea_tiempo(parse_ruta(fx("ruta_28243_aprobado_sobre_tablas.html")), M)
    assert lt[-1]["texto"].startswith("Se trató sobre tablas")
