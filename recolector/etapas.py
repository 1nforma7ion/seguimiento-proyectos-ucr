"""Traduce el recorrido de un expediente a 4 etapas en lenguaje simple."""
import calendar
import re
from dataclasses import dataclass, field
from datetime import date

from .parse import Evento, Ruta

TIPOS = {"L": "ley", "R": "resolucion", "D": "declaracion"}


RE_AUTORES = re.compile(r"(iniciado por|de los legisladores|de la legisladora|del legislador)\b", re.I)
RE_TEMA = re.compile(r",\s+(?=(?:[a-záéíóúñ]+(?:ando|endo|iendo)|que|para|por el cual|por la cual|mediante|sobre)\b)")


def tema_de(extracto: str) -> str:
    """El tema del proyecto, sin el encabezado "Proyecto de X, iniciado por …, ".

    Los extractos del portal empiezan con el tipo y la lista de autores; el tema arranca
    en el primer verbo ("disponiendo", "solicitando", "que modifica"…). Si no se reconoce
    el formato, se devuelve el extracto tal cual.
    """
    autores = RE_AUTORES.search(extracto)
    if not autores:
        return extracto
    tema = RE_TEMA.search(extracto, autores.end())
    if not tema:
        return extracto
    resto = extracto[tema.end():].strip()
    return resto[:1].upper() + resto[1:] if resto else extracto


def tipo_de(numero: str) -> str:
    partes = numero.split("/")
    return TIPOS.get(partes[1] if len(partes) == 3 else "", "otros")


@dataclass
class EstadoExp:
    etapa: int
    etapa_nombre: str
    resultado: str | None
    sobre_tablas: bool
    ingreso: date | None
    ultimo_movimiento: dict | None
    caduca_el: date | None
    desconocidos: list[str] = field(default_factory=list)
    fecha_resultado: date | None = None  # cuándo se llegó al resultado (p. ej. la aprobación)


def _mas_12_meses(d: date) -> date:
    anio = d.year + 1
    return date(anio, d.month, min(d.day, calendar.monthrange(anio, d.month)[1]))


def _regla(ev: Evento, mapeo: dict) -> dict | None:
    tabla = mapeo["estados"] if ev.tipo == "Estado" else mapeo["situaciones"]
    return tabla.get(ev.valor)


def texto_evento(ev: Evento, mapeo: dict) -> str:
    regla = _regla(ev, mapeo)
    return regla["texto"] if regla else ev.valor


def calcular_estado(ruta: Ruta, mapeo: dict) -> EstadoExp:
    etapa, resultado, sobre_tablas = 1, None, False
    ingreso, base_rehab, desconocidos, fecha_resultado = None, None, [], None
    for ev in ruta.eventos:
        regla = _regla(ev, mapeo)
        if regla is None:
            desconocidos.append(ev.valor)
            continue
        if ev.tipo == "Estado":
            if regla["etapa"] is not None:  # null = el estado no mueve la etapa
                etapa = regla["etapa"]
                nuevo = regla.get("resultado")
                if nuevo != resultado:  # la promulgación no cambia la fecha de la aprobación
                    fecha_resultado = ev.fecha if nuevo else None
                resultado = nuevo
            if ev.valor in ("Ingresado", "Estado Parlamentario") and ingreso is None and ev.fecha:
                ingreso = ev.fecha
            if ev.valor == "Rehabilitado":
                base_rehab = ev.fecha
        elif regla.get("sobre_tablas"):
            sobre_tablas = True
    if resultado is None and ruta.tiene_despacho:
        etapa = max(etapa, 3)

    caduca_el = None
    if resultado is None and etapa in (2, 3):
        base = base_rehab or ingreso
        caduca_el = _mas_12_meses(base) if base else None

    ultimo = None
    if ruta.eventos:
        con_fecha = [e for e in ruta.eventos if e.fecha]
        ev = con_fecha[-1] if con_fecha else ruta.eventos[-1]
        ultimo = {"fecha": ev.fecha.isoformat() if ev.fecha else None, "texto": texto_evento(ev, mapeo)}

    return EstadoExp(etapa, mapeo["nombres_etapa"][str(etapa)], resultado, sobre_tablas,
                     ingreso, ultimo, caduca_el, desconocidos, fecha_resultado)


def linea_tiempo(ruta: Ruta, mapeo: dict) -> list[dict]:
    return [{"fecha": e.fecha.isoformat() if e.fecha else None,
             "texto": texto_evento(e, mapeo),
             "detalle": e.sesion}
            for e in ruta.eventos]
