"""Cliente del portal GLD (ASP.NET WebForms): mantiene el viewstate, espacia las consultas y reintenta."""
import json
import time
from datetime import date
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from .util import decodificar

BASE = "https://gld.legislaturacba.gob.ar/"
URL_BUSCAR = BASE + "Publics/Buscar.aspx"
URL_PERSONA = BASE + "Handlers/Persona.ashx"
USER_AGENT = "SeguimientoLegislativo/1.0 (+https://github.com)"

TARGET_AUTORES = "ctl00$Body$R_Results$ctl{:02d}$LB_Autores"
TARGET_RUTA = "ctl00$Body$R_Results$ctl{:02d}$LB_Ruta"
TARGET_COMISIONES = "ctl00$Body$R_Results$ctl{:02d}$LB_Comisiones"
ESPERAS_REINTENTO = (5, 15, 45)


class PortalError(Exception):
    """El portal no respondió o devolvió algo inesperado."""


def target_pagina(n: int) -> str:
    """Postback del paginador para la página n (base 1)."""
    return f"ctl00$Body$R_Paginas$ctl{n - 1:02d}$LB_Pagina"


def campos_ocultos(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    return {i["name"]: i.get("value", "") for i in soup.select("input[type=hidden]") if i.get("name")}


def url_busqueda(q: str) -> str:
    return URL_BUSCAR + "?q=" + quote(q, safe="")


class Portal:
    def __init__(self, pausa: float = 1.0, sesion=None, dormir=time.sleep, reloj=time.monotonic,
                 fin: float | None = None):
        """fin: instante (en el reloj dado) a partir del cual no se hacen más consultas."""
        self.pausa = pausa
        self.fin = fin
        self.sesion = sesion or requests.Session()
        self.sesion.headers["User-Agent"] = USER_AGENT
        self._dormir = dormir
        self._reloj = reloj
        self._ultima = None
        self._url = None
        self._campos: dict[str, str] | None = None
        self._avanzada = False
        self._filtros: dict[str, str] = {}

    # --- transporte -------------------------------------------------------
    def _esperar_turno(self):
        if self._ultima is not None:
            falta = self.pausa - (self._reloj() - self._ultima)
            if falta > 0:
                self._dormir(falta)

    def _pedir(self, metodo: str, url: str, **kw) -> bytes:
        for intento in range(len(ESPERAS_REINTENTO) + 1):
            if self.fin is not None and self._reloj() >= self.fin:
                raise TimeoutError("Se terminó el tiempo de la corrida")
            self._esperar_turno()
            try:
                r = getattr(self.sesion, metodo)(url, timeout=60, **kw)
                ok = r.status_code == 200
            except requests.RequestException:
                ok = False
            self._ultima = self._reloj()
            if ok:
                return r.content
            if intento < len(ESPERAS_REINTENTO):
                espera = ESPERAS_REINTENTO[intento]
                if self.fin is not None and self._reloj() + espera >= self.fin:
                    raise TimeoutError("Se terminó el tiempo de la corrida")
                self._dormir(espera)
        raise PortalError(f"El portal no respondió: {metodo.upper()} {url}")

    def _recordar(self, url: str, html: str) -> str:
        campos = campos_ocultos(html)
        if "__VIEWSTATE" in campos:
            self._url, self._campos = url, campos
        return html

    # --- operaciones ------------------------------------------------------
    def get(self, url: str, params: dict | None = None) -> str:
        return decodificar(self._pedir("get", url, params=params))

    def buscar(self, q: str) -> str:
        self._avanzada = False
        self._filtros = {}
        url = url_busqueda(q)
        return self._recordar(url, self.get(url))

    def postback(self, target: str, extra: dict | None = None) -> str:
        if not self._campos:
            raise PortalError("No hay una página cargada para hacer postback")
        datos = dict(self._campos)
        datos["__EVENTTARGET"] = target
        datos["__EVENTARGUMENT"] = ""
        datos.update(extra or {})
        html = decodificar(self._pedir("post", self._url, data=datos))
        return self._recordar(self._url, html)

    def ir_a_pagina(self, n: int) -> str:
        # Los cuadros de texto del filtro no son campos ocultos: hay que reenviarlos
        # o el portal repite la búsqueda sin fechas.
        return self.postback(target_pagina(n), dict(self._filtros))

    def abrir_avanzada(self) -> str:
        self._recordar(URL_BUSCAR, self.get(URL_BUSCAR))
        html = self.postback("", {"ctl00$Body$B_Avanzada": "Avanzada"})
        self._avanzada = True
        return html

    def consultar_autor(self, id_portal: int, desde: date, hasta: date) -> str:
        """Búsqueda avanzada por autor y fecha de estado parlamentario en [desde, hasta).

        El portal trata 'hasta' como exclusivo. Devuelve la página 1 de resultados.
        """
        if not self._avanzada:
            self.abrir_avanzada()
        self._filtros = {
            "ctl00$Body$HF_IdAutores": str(id_portal),
            "ctl00$Body$TB_FechaEstadoParlamentarioDesde": desde.strftime("%d/%m/%Y"),
            "ctl00$Body$TB_FechaEstadoParlamentarioHasta": hasta.strftime("%d/%m/%Y"),
        }
        return self.postback("", {**self._filtros, "ctl00$Body$B_BusquedaAvanzada": "Buscar"})

    def buscar_persona(self, termino: str) -> list[dict]:
        return json.loads(self.get(URL_PERSONA, params={"term": termino}))
