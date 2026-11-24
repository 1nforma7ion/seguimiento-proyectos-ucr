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
    nums, pend = corrida.listar_autor(p, 1, date(2026, 10, 1), date(2026, 11, 1))
    assert set(nums) == {f"{i}/L/26" for i in range(5)} and pend == [] and p.consultas == 1


def test_listar_bisecta_hasta_que_entra_en_una_pagina():
    datos = {f"{i}/L/26": date(2026, 10, 1) + timedelta(days=i % 30) for i in range(40)}
    nums, pend = corrida.listar_autor(PortalListado({1: datos}), 1, date(2026, 10, 1), date(2026, 11, 1))
    assert set(nums) == set(datos) and pend == []
    assert nums["3/L/26"] == "Extracto 3/L/26"


def test_listar_dia_con_mas_de_10_pagina_hasta_completar():
    datos = {f"{i}/D/26": date(2026, 10, 29) for i in range(27)}
    nums, pend = corrida.listar_autor(PortalListado({1: datos}), 1, date(2026, 10, 1), date(2026, 11, 1))
    assert set(nums) == set(datos) and pend == []


def test_listar_dia_que_no_converge_avisa():
    class Tacanio(PortalListado):
        def ir_a_pagina(self, n):  # siempre devuelve los mismos 10
            return html_resultados(self._actual[:10], len(self._actual))

    datos = {f"{i}/D/26": date(2026, 10, 29) for i in range(27)}
    nums, pend = corrida.listar_autor(Tacanio({1: datos}), 1, date(2026, 10, 29), date(2026, 10, 30))
    assert len(nums) == 10
    assert pend == [date(2026, 10, 29)]


def test_listar_total_sin_resultados_es_error():
    class Roto(PortalListado):
        def ir_a_pagina(self, n):  # el contador dice 5 pero no hay resultados legibles
            return html_resultados([], len(self._actual))

    datos = {f"{i}/D/26": date(2026, 10, 29) for i in range(5)}
    with pytest.raises(PortalError):
        corrida.listar_autor(Roto({1: datos}), 1, date(2026, 10, 1), date(2026, 11, 1))


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
    reg.corte_en = None     # id_portal en el que se agota el tiempo
    reg.pendientes = {}     # id_portal -> [fechas sin completar]
    reg.llamadas = []       # (id_portal, desde, hasta)
    reg.fallan = set()      # números cuyo detalle falla ("*" = todos)
    reg.excepcion = PortalError

    def listar(portal, id_portal, desde, hasta):
        reg.llamadas.append((id_portal, desde, hasta))
        if reg.error_en == id_portal:
            raise PortalError("se cayó")
        if reg.corte_en == id_portal:
            raise TimeoutError
        return dict(reg.listados.get(id_portal, {})), list(reg.pendientes.pop(id_portal, []))

    def detalle(portal, numero, con_autores=True, con_comisiones=True):
        reg.detalles.append((numero, con_autores))
        if numero in reg.fallan or "*" in reg.fallan:
            raise reg.excepcion(f"no se encontró {numero}")
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
    antes = leer(raiz, "estado.json")["ultima_actualizacion_ok"]
    falso.listados[2950] = {}
    assert correr(raiz, solo="ferrero", completo=True) == 1
    estado = leer(raiz, "estado.json")
    assert estado["ok"] is False and estado["ultima_actualizacion_ok"] == antes
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


def progreso(raiz):
    return leer(raiz, "progreso.json")


def test_carga_inicial_cortada_continua_al_dia_siguiente(raiz, falso):
    falso.listados[2949] = {"1/L/26": "x"}           # austin (primera en la lista)
    falso.listados[2950] = {"2/L/26": "y"}           # ferrero
    falso.corte_en = 2950
    assert correr(raiz) == 1
    assert "austin" in progreso(raiz)["listado_completo"]
    assert "ferrero" not in progreso(raiz)["listado_completo"]
    assert leer(raiz, "estado.json")["ultima_actualizacion_ok"] is None
    falso.corte_en = None
    falso.llamadas.clear()
    assert correr(raiz, hoy=MARTES + timedelta(days=1)) == 0
    desde = {i: d for i, d, _ in falso.llamadas}
    assert desde[2950] == date(2023, 12, 10)                                # sigue la carga completa
    assert desde[2949] == MARTES + timedelta(days=1) - timedelta(days=45)   # ya cargada: ventana diaria
    assert "2/L/26" in leer(raiz, "indice.json")["expedientes"]
    assert leer(raiz, "estado.json")["ultima_actualizacion_ok"] is not None


def test_carga_pendiente_mantiene_el_aviso(raiz, falso):
    falso.listados[2950] = {"2/L/26": "y"}
    assert correr(raiz, solo="ferrero") == 0
    est = leer(raiz, "estado.json")
    assert est["ok"] is True and est["ultima_actualizacion_ok"] is None   # faltan 17 legisladores
    assert any("Carga inicial en curso" in a for a in est["advertencias"])


def test_max_nuevos_no_marca_completo(raiz, falso):
    falso.listados[2950] = {f"{i}/L/26": "x" for i in range(5)}
    correr(raiz, solo="ferrero", max_nuevos=2)
    assert "ferrero" not in progreso(raiz)["listado_completo"]


def test_dia_que_no_converge_se_reintenta(raiz, falso):
    falso.listados[2950] = {"2/L/26": "y"}
    falso.pendientes[2950] = [date(2025, 3, 5)]
    correr(raiz, solo="ferrero")
    assert progreso(raiz)["dias_pendientes"] == {"ferrero": ["2025-03-05"]}
    assert any("05/03/2025" in a for a in leer(raiz, "estado.json")["advertencias"])
    falso.llamadas.clear()
    correr(raiz, solo="ferrero", hoy=MARTES + timedelta(days=1))
    assert (2950, date(2025, 3, 5), date(2025, 3, 6)) in falso.llamadas
    assert progreso(raiz)["dias_pendientes"] == {}


def test_expediente_inencontrable_no_corta_la_corrida(raiz, falso):
    falso.listados[2950] = {"1/L/26": "x", "2/L/26": "y"}
    falso.fallan = {"1/L/26"}
    assert correr(raiz, solo="ferrero") == 0
    assert list(leer(raiz, "indice.json")["expedientes"]) == ["2/L/26"]
    assert any("1/L/26" in a for a in leer(raiz, "estado.json")["advertencias"])


def test_tres_fallas_seguidas_cortan(raiz, falso):
    falso.listados[2950] = {f"{i}/L/26": "x" for i in range(6)}
    falso.fallan = {"*"}
    assert correr(raiz, solo="ferrero") == 1
    assert len(falso.detalles) == 3


def test_error_inesperado_igual_escribe_estado(raiz, falso):
    falso.listados[2950] = {f"{i}/L/26": "x" for i in range(2)}
    falso.fallan = {"*"}
    falso.excepcion = ValueError
    assert correr(raiz, solo="ferrero") == 1
    est = leer(raiz, "estado.json")
    assert est["ok"] is False and any("ValueError" in a for a in est["advertencias"])
    assert (raiz / "sitio" / "data" / "indice.json").exists()


def test_carga_inicial_no_llena_novedades(raiz, falso):
    falso.listados[2950] = {"1/L/24": "viejo", "2/L/26": "nuevo"}
    falso.rutas["1/L/24"] = ruta_en_comision(date(2024, 5, 1))
    falso.rutas["2/L/26"] = ruta_en_comision(MARTES - timedelta(days=3))
    correr(raiz, solo="ferrero")
    assert [n["numero"] for n in leer(raiz, "novedades.json")] == ["2/L/26"]
