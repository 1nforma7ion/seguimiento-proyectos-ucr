from datetime import date

import pytest

from conftest import fx_bytes
from recolector.portal import Portal, PortalError, TARGET_RUTA, target_pagina


class Resp:
    def __init__(self, contenido: bytes, status: int = 200, url: str = "https://gld.legislaturacba.gob.ar/Publics/Buscar.aspx"):
        self.content = contenido
        self.status_code = status
        self.url = url


class SesionFalsa:
    """Devuelve respuestas en orden y registra cada llamada."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.llamadas.append(("GET", url, params))
        return self.respuestas.pop(0)

    def post(self, url, data=None, timeout=None):
        self.llamadas.append(("POST", url, data))
        return self.respuestas.pop(0)


class Reloj:
    def __init__(self):
        self.t = 0.0
        self.esperas = []

    def ahora(self):
        return self.t

    def dormir(self, s):
        self.esperas.append(s)
        self.t += s


def portal_con(respuestas, pausa=1.0):
    reloj = Reloj()
    p = Portal(pausa=pausa, sesion=SesionFalsa(respuestas), dormir=reloj.dormir, reloj=reloj.ahora)
    return p, reloj


PAGINA = fx_bytes("buscar_ferrero_p1.html")


def test_postback_envia_viewstate_de_la_ultima_respuesta():
    p, _ = portal_con([Resp(PAGINA), Resp(PAGINA)])
    p.buscar("Ferrero")
    p.postback(TARGET_RUTA.format(3))
    metodo, _, datos = p.sesion.llamadas[-1]
    assert metodo == "POST"
    assert datos["__EVENTTARGET"] == "ctl00$Body$R_Results$ctl03$LB_Ruta"
    assert datos["__VIEWSTATE"] and len(datos["__VIEWSTATE"]) > 100
    assert "__EVENTVALIDATION" in datos


def test_postback_sin_pagina_previa_falla():
    p, _ = portal_con([])
    with pytest.raises(PortalError):
        p.postback(TARGET_RUTA.format(0))


def test_pausa_entre_consultas():
    p, reloj = portal_con([Resp(PAGINA), Resp(PAGINA)])
    p.buscar("Ferrero")
    p.buscar("Ferrero")
    assert reloj.esperas and sum(reloj.esperas) >= 1.0


def test_reintenta_y_luego_falla():
    p, reloj = portal_con([Resp(b"", 503)] * 4, pausa=0)
    with pytest.raises(PortalError):
        p.buscar("Ferrero")
    assert [e for e in reloj.esperas if e >= 5] == [5, 15, 45]
    assert len(p.sesion.llamadas) == 4


def test_reintenta_y_se_recupera():
    p, _ = portal_con([Resp(b"", 503), Resp(PAGINA)], pausa=0)
    assert "Ferrero" in p.buscar("Ferrero")


def test_target_pagina():
    assert target_pagina(1) == "ctl00$Body$R_Paginas$ctl00$LB_Pagina"
    assert target_pagina(12) == "ctl00$Body$R_Paginas$ctl11$LB_Pagina"


def test_consultar_autor_completa_el_formulario_avanzado():
    p, _ = portal_con([Resp(PAGINA), Resp(PAGINA), Resp(PAGINA)])
    p.consultar_autor(2950, date(2026, 10, 1), date(2026, 11, 1))
    _, _, abrir = p.sesion.llamadas[1]
    _, _, enviar = p.sesion.llamadas[2]
    assert "ctl00$Body$B_Avanzada" in abrir
    assert enviar["ctl00$Body$HF_IdAutores"] == "2950"
    assert enviar["ctl00$Body$TB_FechaEstadoParlamentarioDesde"] == "01/10/2026"
    assert enviar["ctl00$Body$TB_FechaEstadoParlamentarioHasta"] == "01/11/2026"
    assert "ctl00$Body$B_BusquedaAvanzada" in enviar


def test_ir_a_pagina_reenvia_los_filtros_de_la_consulta():
    p, _ = portal_con([Resp(PAGINA)] * 4)
    p.consultar_autor(2950, date(2026, 10, 29), date(2026, 10, 30))
    p.ir_a_pagina(2)
    datos = p.sesion.llamadas[-1][2]
    assert datos["__EVENTTARGET"] == "ctl00$Body$R_Paginas$ctl01$LB_Pagina"
    assert datos["ctl00$Body$HF_IdAutores"] == "2950"
    assert datos["ctl00$Body$TB_FechaEstadoParlamentarioDesde"] == "29/10/2026"
    assert "ctl00$Body$B_BusquedaAvanzada" not in datos


def test_consultar_autor_abre_el_formulario_una_sola_vez():
    p, _ = portal_con([Resp(PAGINA)] * 4)
    p.consultar_autor(2950, date(2026, 10, 1), date(2026, 11, 1))
    p.consultar_autor(2951, date(2026, 10, 1), date(2026, 11, 1))
    assert len(p.sesion.llamadas) == 4
    assert p.sesion.llamadas[-1][2]["ctl00$Body$HF_IdAutores"] == "2951"


def test_fin_de_tiempo_corta_antes_de_pedir():
    reloj = Reloj()
    reloj.t = 100.0
    p = Portal(pausa=0, sesion=SesionFalsa([Resp(PAGINA)]), dormir=reloj.dormir, reloj=reloj.ahora, fin=50.0)
    with pytest.raises(TimeoutError):
        p.buscar("Ferrero")
    assert p.sesion.llamadas == []


def test_no_reintenta_si_no_alcanza_el_tiempo():
    reloj = Reloj()
    p = Portal(pausa=0, sesion=SesionFalsa([Resp(b"", 503)] * 4), dormir=reloj.dormir, reloj=reloj.ahora, fin=4.0)
    with pytest.raises(TimeoutError):
        p.buscar("Ferrero")
    assert len(p.sesion.llamadas) == 1


ERROR_PORTAL = Resp(b"<html>error</html>", 200,
                    "https://gld.legislaturacba.gob.ar/Pages/500.html?exMsg=Timeout%20expired.")


def test_pagina_de_error_del_portal_se_reintenta():
    p, _ = portal_con([ERROR_PORTAL, Resp(PAGINA)], pausa=0)
    assert "Ferrero" in p.buscar("Ferrero")
    assert len(p.sesion.llamadas) == 2


def test_portal_fuera_de_servicio_da_un_mensaje_claro():
    p, _ = portal_con([ERROR_PORTAL] * 4, pausa=0)
    with pytest.raises(PortalError, match="fuera de servicio"):
        p.buscar("Ferrero")
