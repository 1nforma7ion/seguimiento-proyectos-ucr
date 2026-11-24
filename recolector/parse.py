"""Convierte el HTML del portal GLD en datos."""
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .portal import BASE, PortalError

RE_SESION = re.compile(r"^(?P<sesion>.+? del Período (?P<periodo>\d+))\s*\((?P<fecha>\d{1,2}/\d{1,2}/\d{4})\)")
RE_FECHA = re.compile(r"\((\d{1,2}/\d{1,2}/\d{4})\)")
SECCIONES = {"Body_GV_Anexos": "Anexos", "Body_GV_Actas": "Actas",
             "Body_GV_Despachos": "Despachos", "Body_GV_TA": "Texto aprobado"}


@dataclass
class Evento:
    tipo: Literal["Estado", "Situación"]
    valor: str
    sesion: str | None = None
    periodo: int | None = None
    fecha: date | None = None


@dataclass
class Documento:
    seccion: str
    nombre: str
    url: str | None = None


@dataclass
class Ruta:
    eventos: list[Evento] = field(default_factory=list)
    documentos: list[Documento] = field(default_factory=list)

    @property
    def tiene_despacho(self) -> bool:
        return any(d.seccion == "Despachos" for d in self.documentos)


@dataclass
class Resultado:
    numero: str
    extracto: str
    posicion: int


def _sopa(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _texto(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip() if el else ""


def _exigir(sopa, selector: str, que: str):
    el = sopa.select_one(selector)
    if el is None:
        raise PortalError(f"El portal cambió: no se encontró {que} ({selector})")
    return el


def _fecha(s: str) -> date:
    return datetime.strptime(s, "%d/%m/%Y").date()


def parse_total(html: str) -> int:
    t = _texto(_exigir(_sopa(html), "#Body_L_Results", "la cantidad de resultados"))
    m = re.match(r"([\d\.]+) resultados", t)
    if not m:
        raise PortalError(f"El portal cambió: cantidad de resultados ilegible: {t!r}")
    return int(m.group(1).replace(".", ""))


def parse_resultados(html: str) -> list[Resultado]:
    out = []
    for i, a in enumerate(_sopa(html).select("a.result-number")):
        bloque = a.find_parent("div", class_="col-12")
        extracto = _texto(bloque.select_one("p span.text-muted")) if bloque else ""
        out.append(Resultado(numero=_texto(a), extracto=extracto, posicion=i))
    return out


def _celdas_tabla(tabla, columna: int) -> list[str]:
    out = []
    for fila in tabla.select("tr"):
        tds = fila.find_all("td", recursive=False)
        if len(tds) > columna and not tds[0].get("colspan"):
            out.append(_texto(tds[columna]))
    return out


def parse_autores(html: str) -> list[str]:
    cont = _exigir(_sopa(html), "#Body_UP_mdlAutores", "la ventana de autores")
    tabla = cont.select_one("#Body_GV_Autores")
    return [x for x in _celdas_tabla(tabla, 2) if x] if tabla else []


def parse_comisiones(html: str) -> list[str]:
    cont = _exigir(_sopa(html), "#Body_UP_mdlComisiones", "la ventana de comisiones")
    tabla = cont.select_one("#Body_GV_Comisiones")
    if not tabla:
        return []
    # Se respeta el orden del portal: la comisión principal va primero.
    return [x for x in _celdas_tabla(tabla, 3) if x]


def _evento(item) -> Evento:
    tipo = "Situación" if _texto(item.select_one(".tracking-content small")).startswith("Situ") else "Estado"
    valor = _texto(item.select_one(".tracking-content b"))
    detalle = _texto(item.select_one(".tracking-content small.ml-1"))
    m = RE_SESION.match(detalle)
    if m:
        return Evento(tipo, valor, m["sesion"], int(m["periodo"]), _fecha(m["fecha"]))
    f = RE_FECHA.search(detalle)
    return Evento(tipo, valor, None, None, _fecha(f.group(1)) if f else None)


def _documentos(sopa) -> list[Documento]:
    out = []
    for id_tabla, seccion in SECCIONES.items():
        tabla = sopa.select_one("#" + id_tabla)
        if not tabla:
            continue
        for fila in tabla.select("tr"):
            tds = fila.find_all("td", recursive=False)
            if len(tds) < 2 or tds[0].get("colspan"):
                continue
            visibles = [_texto(td) for td in tds if "d-none" not in (td.get("class") or [])]
            enlace = fila.select_one("a[href]")
            href = enlace["href"] if enlace else ""
            url = urljoin(BASE + "Publics/", href) if href and not href.startswith("javascript") else None
            if seccion == "Despachos" and len(visibles) >= 3:
                nombre = f"{visibles[0]} ({visibles[2].split(' ')[0]})"
            elif seccion == "Texto aprobado":
                nombre = f"Texto aprobado N° {visibles[0]}"
            else:
                nombre = " · ".join(v for v in visibles if v)
            out.append(Documento(seccion, nombre, url))
    return out


def parse_ruta(html: str) -> Ruta:
    sopa = _sopa(html)
    cont = _exigir(sopa, "#Body_P_RutaRuta", "el recorrido del expediente")
    eventos = [_evento(it) for it in cont.select(".tracking-item")]
    return Ruta(eventos=eventos, documentos=_documentos(sopa))
