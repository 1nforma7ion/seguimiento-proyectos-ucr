import json
import random
import shutil
from datetime import date, datetime, timedelta, timezone

import pytest

from conftest import RAIZ
from recolector import corrida
from recolector.parse import Evento, Ruta
from recolector.portal import PortalError

AR = timezone(timedelta(hours=-3))


def html_resultados(nums: list[str], total: int) -> str:
    items = "".join(
        f'<div class="col-12"><a class="result-number"><span>{n}</span></a>'
        f'<p><small><span class="text-muted">Extracto {n}</span></small></p></div>' for n in nums)
    return f'<span id="Body_L_Results">{total} resultados (0.1 segundos)</span>{items}'


class PortalListado:
    """Simula la búsqueda avanzada: filtra por fecha y devuelve cada página en orden aleatorio."""

    def __init__(self, por_autor: dict[int, dict[str, date]], semilla=1):
        self.por_autor = por_autor
        self.rnd = random.Random(semilla)
        self.consultas = 0
        self._actual = []

    def consultar_autor(self, id_portal, desde, hasta):
        self.consultas += 1
        self._actual = [n for n, f in self.por_autor.get(id_portal, {}).items() if desde <= f < hasta]
        return self.ir_a_pagina(1)

    def ir_a_pagina(self, n):
        orden = self._actual[:]
        self.rnd.shuffle(orden)  # el portal no garantiza el orden entre pedidos
        return html_resultados(orden[(n - 1) * 10:n * 10], len(self._actual))


def test_listar_ventana_chica_una_pagina():
    p = PortalListado({1: {f"{i}/L/26": date(2026, 10, 1 + i) for i in range(5)}})
    nums, adv = corrida.listar_autor(p, 1, date(2026, 10, 1), date(2026, 11, 1))
    assert set(nums) == {f"{i}/L/26" for i in range(5)} and adv == [] and p.consultas == 1


def test_listar_bisecta_hasta_que_entra_en_una_pagina():
    datos = {f"{i}/L/26": date(2026, 10, 1) + timedelta(days=i % 30) for i in range(40)}
    nums, adv = corrida.listar_autor(PortalListado({1: datos}), 1, date(2026, 10, 1), date(2026, 11, 1))
    assert set(nums) == set(datos) and adv == []
    assert nums["3/L/26"] == "Extracto 3/L/26"


def test_listar_dia_con_mas_de_10_pagina_hasta_completar():
    datos = {f"{i}/D/26": date(2026, 10, 29) for i in range(27)}
    nums, adv = corrida.listar_autor(PortalListado({1: datos}), 1, date(2026, 10, 1), date(2026, 11, 1))
    assert set(nums) == set(datos) and adv == []


def test_listar_dia_que_no_converge_avisa():
    class Tacanio(PortalListado):
        def ir_a_pagina(self, n):  # siempre devuelve los mismos 10
            return html_resultados(self._actual[:10], len(self._actual))

    datos = {f"{i}/D/26": date(2026, 10, 29) for i in range(27)}
    nums, adv = corrida.listar_autor(Tacanio({1: datos}), 1, date(2026, 10, 29), date(2026, 10, 30))
    assert len(nums) == 10
    assert adv and "10 de 27" in adv[0]


# --- correr -----------------------------------------------------------------

@pytest.fixture
def raiz(tmp_path):
    shutil.copytree(RAIZ / "config", tmp_path / "config")
    return tmp_path


def ruta_en_comision(f=date(2026, 10, 29)):
    return Ruta([Evento("Estado", "Ingresado", "S", 148, f), Evento("Estado", "En Comisión", "S", 148, f)])


class Registro:
    def __init__(self):
        self.detalles = []


@pytest.fixture
def falso(monkeypatch):
    """Reemplaza listar_autor y detalle por versiones en memoria."""
    reg = Registro()
    reg.listados = {}      # id_portal -> {numero: extracto}
    reg.rutas = {}         # numero -> Ruta
    reg.autores = {}       # numero -> [autores]
    reg.error_en = None

    def listar(portal, id_portal, desde, hasta):
        if reg.error_en == id_portal:
            raise PortalError("se cayó")
        return dict(reg.listados.get(id_portal, {})), []

    def detalle(portal, numero, con_autores=True, con_comisiones=True):
        reg.detalles.append((numero, con_autores))
        return (f"Extracto {numero}", reg.autores.get(numero, ["Ferrero, Alejandra"]) if con_autores else None,
                reg.rutas.get(numero, ruta_en_comision()), ["Legislación General"] if con_comisiones else None)

    monkeypatch.setattr(corrida, "listar_autor", listar)
    monkeypatch.setattr(corrida, "detalle", detalle)
    monkeypatch.setattr(corrida, "verificar_bloque_en_linea", lambda portal, legs: [])
    return reg


def leer(raiz, nombre):
    return json.loads((raiz / "sitio" / "data" / nombre).read_text(encoding="utf-8"))


MARTES = date(2026, 11, 24)
LUNES = date(2026, 11, 23)


def correr(raiz, hoy=MARTES, **kw):
    ahora = datetime(hoy.year, hoy.month, hoy.day, 7, 0, tzinfo=AR)
    return corrida.correr(raiz, portal=None, hoy=hoy, ahora=ahora, **kw)


def test_correr_guarda_nuevo_y_novedad(raiz, falso):
    falso.listados[2950] = {"48498/L/26": "Extracto"}
    assert correr(raiz, solo="ferrero") == 0
    idx = leer(raiz, "indice.json")
    assert idx["expedientes"]["48498/L/26"]["autores_bloque"] == ["ferrero"]
    assert leer(raiz, "novedades.json")[0]["texto"] == "Nuevo proyecto en seguimiento"
    assert leer(raiz, "estado.json")["ok"] is True


def test_correr_no_reconsulta_finales(raiz, falso):
    falso.listados[2950] = {"1/D/26": "x", "2/L/26": "y"}
    falso.rutas["1/D/26"] = Ruta([Evento("Estado", "Aprobado", "S", 148, date(2026, 10, 29))])
    correr(raiz, solo="ferrero")
    falso.detalles.clear()
    correr(raiz, solo="ferrero")
    assert [n for n, _ in falso.detalles] == ["2/L/26"]
    assert falso.detalles[0][1] is False  # al actualizar no se vuelven a pedir los autores


def test_caducados_solo_lunes(raiz, falso):
    falso.listados[2950] = {"3/L/24": "x"}
    falso.rutas["3/L/24"] = Ruta([Evento("Estado", "Ingresado", "S", 146, date(2024, 2, 14)),
                                  Evento("Estado", "Caducado", None, None, date(2025, 2, 17))])
    correr(raiz, solo="ferrero")
    falso.detalles.clear()
    correr(raiz, hoy=MARTES + timedelta(days=1), solo="ferrero")
    assert falso.detalles == []
    correr(raiz, hoy=LUNES + timedelta(days=7), solo="ferrero")
    assert [n for n, _ in falso.detalles] == ["3/L/24"]


def test_cero_resultados_es_error(raiz, falso):
    falso.listados[2950] = {"48498/L/26": "x"}
    correr(raiz, solo="ferrero")
    falso.listados[2950] = {}
    assert correr(raiz, solo="ferrero", completo=True) == 1
    estado = leer(raiz, "estado.json")
    assert estado["ok"] is False and estado["ultima_actualizacion_ok"].startswith("2026-11-24")
    assert any("0 resultados" in a for a in estado["advertencias"])
    assert (raiz / "sitio" / "data" / "expedientes" / "48498-L-26.json").exists()


def test_error_del_portal_no_borra_y_devuelve_1(raiz, falso):
    falso.listados[2950] = {"48498/L/26": "x"}
    correr(raiz, solo="ferrero")
    falso.error_en = 2950
    assert correr(raiz, hoy=MARTES + timedelta(days=1), solo="ferrero") == 1
    assert leer(raiz, "estado.json")["ok"] is False
    assert "48498/L/26" in leer(raiz, "indice.json")["expedientes"]


def test_estado_desconocido_va_a_advertencias(raiz, falso):
    falso.listados[2950] = {"5/L/26": "x"}
    falso.rutas["5/L/26"] = Ruta([Evento("Estado", "Estado Inventado", "S", 148, date(2026, 10, 29))])
    assert correr(raiz, solo="ferrero") == 0
    assert any("Estado Inventado" in a for a in leer(raiz, "estado.json")["advertencias"])


def test_max_nuevos_limita_la_prueba(raiz, falso):
    falso.listados[2950] = {f"{i}/L/26": "x" for i in range(5)}
    assert correr(raiz, solo="ferrero", max_nuevos=2) == 0
    assert len(leer(raiz, "indice.json")["expedientes"]) == 2


def test_ventana_diaria_vs_completa(raiz, falso, monkeypatch):
    llamadas = []

    def listar(p, i, d, h):
        llamadas.append((d, h))
        return ({"1/L/26": "x"} if len(llamadas) == 1 else {}), []

    monkeypatch.setattr(corrida, "listar_autor", listar)
    correr(raiz, solo="ferrero")                # primera vez: todo el mandato
    correr(raiz, solo="ferrero")                # después: ventana de 45 días
    assert llamadas[0] == (date(2023, 12, 10), MARTES + timedelta(days=1))
    assert llamadas[1] == (MARTES - timedelta(days=45), MARTES + timedelta(days=1))
