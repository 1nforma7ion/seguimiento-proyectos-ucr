"""Guarda los expedientes como JSON y arma el índice, las novedades y el estado que lee el sitio."""
import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import Legislador
from .etapas import calcular_estado, linea_tiempo, tema_de, texto_evento, tipo_de
from .parse import Documento, Evento, Ruta
from .portal import url_busqueda
from .titulos import titulo_de

NUEVO = "Nuevo proyecto en seguimiento"


@dataclass
class Expediente:
    numero: str
    extracto: str
    autores: list[str]
    comisiones: list[str]
    ruta: Ruta
    recolectado: datetime


def id_archivo(numero: str) -> str:
    return numero.replace("/", "-")


def _escribir(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, ruta)


def _leer(ruta: Path, defecto=None):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else defecto


def _iso(v):
    return v.isoformat() if isinstance(v, (date, datetime)) else v


def recortar(texto: str, largo: int) -> str:
    if len(texto) <= largo:
        return texto
    corte = texto[:largo].rsplit(" ", 1)[0].rstrip(" ,;.")
    return corte + "…"


def _ruta_archivo(dir_datos: Path, numero: str) -> Path:
    return Path(dir_datos) / "expedientes" / f"{id_archivo(numero)}.json"


def cargar_expediente(dir_datos: Path, numero: str) -> dict | None:
    return _leer(_ruta_archivo(dir_datos, numero))


def _armar(numero, extracto, autores, comisiones, ruta: Ruta, recolectado: str, mapeo: dict) -> dict:
    estado = calcular_estado(ruta, mapeo)
    return {
        "numero": numero,
        "tipo": tipo_de(numero),
        "extracto": extracto,
        "tema": tema_de(extracto),
        "titulo": titulo_de(tema_de(extracto), extracto),
        "autores": autores,
        "comisiones": comisiones,
        "estado": {k: _iso(v) for k, v in asdict(estado).items() if k != "desconocidos"},
        "desconocidos": estado.desconocidos,
        "linea_tiempo": linea_tiempo(ruta, mapeo),
        "eventos_crudos": [{k: _iso(v) for k, v in asdict(e).items()} for e in ruta.eventos],
        "documentos": [asdict(d) for d in ruta.documentos],
        "url_portal": url_busqueda(numero),
        "recolectado": recolectado,
    }


def _ruta_guardada(d: dict) -> Ruta:
    eventos = [Evento(e["tipo"], e["valor"], e["sesion"], e["periodo"],
                      date.fromisoformat(e["fecha"]) if e["fecha"] else None) for e in d["eventos_crudos"]]
    return Ruta(eventos, [Documento(**x) for x in d["documentos"]])


def rederivar(dir_datos: Path, mapeo: dict) -> int:
    """Recalcula estado y recorrido de lo ya guardado, sin consultar el portal.

    Sirve cuando cambia config/etapas.json o el cálculo de etapas. Devuelve cuántos cambiaron.
    """
    cambiados = 0
    for archivo in sorted((Path(dir_datos) / "expedientes").glob("*.json")):
        d = _leer(archivo)
        nuevo = _armar(d["numero"], d["extracto"], d["autores"], d["comisiones"], _ruta_guardada(d),
                       d["recolectado"], mapeo)
        if nuevo != d:
            _escribir(archivo, nuevo)
            cambiados += 1
    return cambiados


def guardar_expediente(dir_datos: Path, exp: Expediente, mapeo: dict) -> list[str]:
    """Escribe el JSON del expediente y devuelve los textos de los eventos nuevos."""
    anterior = cargar_expediente(dir_datos, exp.numero)
    datos = _armar(exp.numero, exp.extracto, exp.autores, exp.comisiones, exp.ruta,
                   exp.recolectado.isoformat(), mapeo)
    crudos = datos["eventos_crudos"]
    # Si solo cambió la hora de recolección, no se reescribe: evita commits diarios sin cambios reales.
    if anterior is not None and {**anterior, "recolectado": None} == {**datos, "recolectado": None}:
        return []
    _escribir(_ruta_archivo(dir_datos, exp.numero), datos)
    if anterior is None:
        return [NUEVO]
    vistos = {(e["tipo"], e["valor"], e["fecha"]) for e in anterior.get("eventos_crudos", [])}
    return [texto_evento(e, mapeo) for e, c in zip(exp.ruta.eventos, crudos)
            if (c["tipo"], c["valor"], c["fecha"]) not in vistos]


def construir_novedades(dir_datos: Path, hoy: date, dias: int, mapeo: dict) -> list[dict]:
    """Arma novedades.json con los movimientos de los últimos `dias` días, con su fecha real.

    Se recalcula entera en cada corrida a partir de los expedientes guardados: así la fecha de una
    novedad es siempre la del movimiento en el portal, y no el día en que el sistema la encontró.
    Cada novedad lleva su clase (buena, mala o tramite) y una etiqueta corta, según config/etapas.json.
    Las situaciones (cómo se trató) no cuentan: acompañan a un estado que ya es la novedad.
    """
    limite, tope = (hoy - timedelta(days=dias)).isoformat(), hoy.isoformat()
    novedades = []
    for archivo in sorted((Path(dir_datos) / "expedientes").glob("*.json")):
        d = _leer(archivo)
        vistos = set()
        for orden, ev in enumerate(d.get("eventos_crudos", [])):
            regla = mapeo["estados"].get(ev["valor"]) if ev["tipo"] == "Estado" else None
            fecha = ev.get("fecha")
            if not regla or not regla.get("novedad") or not fecha or not limite <= fecha <= tope:
                continue
            if (fecha, regla["texto"]) in vistos:
                continue
            vistos.add((fecha, regla["texto"]))
            novedades.append({"numero": d["numero"], "fecha": fecha, "texto": regla["texto"],
                              "corto": regla.get("corto", regla["texto"]), "clase": regla["novedad"], "orden": orden})
    novedades.sort(key=lambda n: (n["fecha"], n["numero"]), reverse=True)
    _escribir(Path(dir_datos) / "novedades.json", novedades)
    return novedades


def construir_indice(dir_datos: Path, legisladores: list[Legislador], ajustes: dict, ahora: datetime,
                     dir_fotos: Path | None = None) -> dict:
    dir_fotos = Path(dir_fotos) if dir_fotos else Path(dir_datos).parent / "fotos"
    expedientes, por_leg = {}, {l.slug: [] for l in legisladores}
    for archivo in sorted((Path(dir_datos) / "expedientes").glob("*.json")):
        d = _leer(archivo)
        bloque = sorted(l.slug for l in legisladores if any(l.es_autor(a) for a in d["autores"]))
        # Quien inició el proyecto: el portal lista primero a esa persona (los "Bloque X" no cuentan).
        primero = next((a for a in d["autores"] if not a.lower().startswith("bloque")), None)
        principal = next((l.slug for l in legisladores if primero and l.es_autor(primero)), None)
        if not bloque:
            continue
        expedientes[d["numero"]] = {"tipo": d["tipo"], "titulo": d.get("titulo") or recortar(d.get("tema") or d["extracto"], 140),
                                    # Texto extra para el buscador: el tema completo dice más que el título corto.
                                    "desc": d.get("tema") or d["extracto"],
                                    "autores_bloque": bloque, "comisiones": d["comisiones"],
                                    "n_autores": len(d["autores"]),
                                    "principal": principal,
                                    "estado": d["estado"]}
        for slug in bloque:
            por_leg[slug].append(d["numero"])
    indice = {
        "generado": ahora.isoformat(),
        "ajustes": ajustes,
        "legisladores": [{"slug": l.slug, "nombre": l.nombre_mostrar, "departamental": l.departamental,
                          "cargo": l.cargo, "nombre_portal": l.nombre_portal, "alias": l.alias,
                          "foto": f"fotos/{l.slug}.webp" if (dir_fotos / f"{l.slug}.webp").exists() else None,
                          "expedientes": por_leg[l.slug]} for l in legisladores],
        "expedientes": expedientes,
    }
    _escribir(Path(dir_datos) / "indice.json", indice)
    return indice


def cargar_progreso(dir_datos: Path) -> dict:
    """Qué legisladores ya tienen su carga completa y qué días quedaron sin terminar."""
    d = _leer(Path(dir_datos) / "progreso.json", {})
    return {"listado_completo": d.get("listado_completo", {}), "dias_pendientes": d.get("dias_pendientes", {})}


def guardar_progreso(dir_datos: Path, progreso: dict) -> None:
    _escribir(Path(dir_datos) / "progreso.json", progreso)


def escribir_estado(dir_datos: Path, ok: bool, advertencias: list[str], ahora: datetime,
                    al_dia: bool | None = None) -> None:
    """al_dia: si los datos cuentan como actualizados (por defecto, igual que ok)."""
    ruta = Path(dir_datos) / "estado.json"
    anterior = _leer(ruta, {})
    al_dia = ok if al_dia is None else al_dia
    _escribir(ruta, {
        "ultima_corrida": ahora.isoformat(),
        "ultima_actualizacion_ok": ahora.isoformat() if al_dia else anterior.get("ultima_actualizacion_ok"),
        "ok": ok,
        "advertencias": advertencias,
    })
