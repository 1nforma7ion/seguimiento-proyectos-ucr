"""Una corrida completa: descubre expedientes del bloque, actualiza su recorrido y publica los JSON."""
import math
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from . import almacen
from .bloque import URL_LEGISLADORES, verificar_bloque
from .config import cargar_config
from .parse import parse_autores, parse_comisiones, parse_resultados, parse_ruta, parse_total
from .portal import TARGET_AUTORES, TARGET_COMISIONES, TARGET_RUTA, PortalError

POR_PAGINA = 10
MAX_PASADAS = 8


# --- descubrimiento ---------------------------------------------------------

def listar_autor(portal, id_portal: int, desde: date, hasta: date) -> tuple[dict[str, str], list[str]]:
    """Todos los expedientes del autor con estado parlamentario en [desde, hasta).

    El portal ordena al azar, así que se parte el rango hasta que cada consulta
    entre en una sola página. Un día con más de 10 se recorre varias veces.
    Devuelve {numero: extracto} y advertencias.
    """
    html = portal.consultar_autor(id_portal, desde, hasta)
    total = parse_total(html)
    encontrados = {r.numero: r.extracto for r in parse_resultados(html)}
    if total <= POR_PAGINA:
        return encontrados, []
    if (hasta - desde).days > 1:
        medio = desde + (hasta - desde) // 2
        a, adv_a = listar_autor(portal, id_portal, desde, medio)
        b, adv_b = listar_autor(portal, id_portal, medio, hasta)
        return {**a, **b}, adv_a + adv_b
    paginas = math.ceil(total / POR_PAGINA)
    for _ in range(MAX_PASADAS):
        for n in range(1, paginas + 1):
            encontrados.update({r.numero: r.extracto for r in parse_resultados(portal.ir_a_pagina(n))})
        if len(encontrados) >= total:
            return encontrados, []
    return encontrados, [f"Autor {id_portal}, día {desde:%d/%m/%Y}: se leyeron {len(encontrados)} de {total} "
                         "expedientes; el resto se intenta en la próxima corrida"]


def detalle(portal, numero: str, con_autores: bool = True, con_comisiones: bool = True):
    """Busca un expediente por número y trae extracto, autores, recorrido y comisiones."""
    resultados = parse_resultados(portal.buscar(numero))
    r = next((x for x in resultados if x.numero == numero), None)
    if r is None:
        raise PortalError(f"No se encontró el expediente {numero} en el portal")
    autores = parse_autores(portal.postback(TARGET_AUTORES.format(r.posicion))) if con_autores else None
    ruta = parse_ruta(portal.postback(TARGET_RUTA.format(r.posicion)))
    comisiones = parse_comisiones(portal.postback(TARGET_COMISIONES.format(r.posicion))) if con_comisiones else None
    return r.extracto, autores, ruta, comisiones


def verificar_bloque_en_linea(portal, legisladores) -> list[str]:
    return verificar_bloque(portal.get(URL_LEGISLADORES), legisladores)


# --- corrida ----------------------------------------------------------------

def _resumen_github(texto: str) -> None:
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write(texto + "\n")


def _guardar(dir_datos, cfg, hoy, numero, extracto, autores, ruta, comisiones, ahora) -> list[str]:
    exp = almacen.Expediente(numero, extracto, autores, comisiones, ruta, ahora)
    textos = almacen.guardar_expediente(dir_datos, exp, cfg.etapas)
    if textos:
        almacen.agregar_novedades(dir_datos, numero, textos, hoy, cfg.ajustes["dias_novedades"])
    return almacen.cargar_expediente(dir_datos, numero).get("desconocidos", [])


def correr(raiz: Path, portal, hoy: date, ahora: datetime, solo: str | None = None,
           completo: bool = False, limite: datetime | None = None, max_nuevos: int | None = None) -> int:
    raiz = Path(raiz)
    cfg = cargar_config(raiz)
    dir_datos = raiz / "sitio" / "data"
    finales = set(cfg.etapas.get("resultados_finales", []))
    legisladores = [l for l in cfg.legisladores if solo in (None, l.slug)]
    conocidos = {}
    for archivo in (dir_datos / "expedientes").glob("*.json") if (dir_datos / "expedientes").exists() else []:
        d = almacen._leer(archivo)
        conocidos[d["numero"]] = d

    primera_vez = not conocidos
    desde = (date.fromisoformat(cfg.ajustes["desde_fecha"]) if completo or primera_vez
             else hoy - timedelta(days=cfg.ajustes["dias_ventana_diaria"]))
    hasta = hoy + timedelta(days=1)
    advertencias, desconocidos, ok = [], set(), True
    nuevos = set()

    def a_tiempo():
        return limite is None or datetime.now(ahora.tzinfo) < limite

    try:
        for leg in legisladores:
            if not a_tiempo():
                raise TimeoutError
            encontrados, adv = listar_autor(portal, leg.id_portal, desde, hasta)
            advertencias += adv
            tenia = any(any(leg.es_autor(a) for a in d.get("autores", [])) for d in conocidos.values())
            if not encontrados and tenia and desde == date.fromisoformat(cfg.ajustes["desde_fecha"]):
                raise PortalError(f"{leg.nombre_mostrar}: el portal devolvió 0 resultados pero tenía "
                                  "expedientes; puede que el portal haya cambiado")
            for numero in sorted(set(encontrados) - set(conocidos) - nuevos):
                if max_nuevos is not None and len(nuevos) >= max_nuevos:
                    break
                if not a_tiempo():
                    raise TimeoutError
                extracto, autores, ruta, comisiones = detalle(portal, numero)
                desconocidos.update(_guardar(dir_datos, cfg, hoy, numero, extracto or encontrados[numero],
                                             autores, ruta, comisiones, ahora))
                nuevos.add(numero)

        es_lunes = hoy.weekday() == 0
        for numero, d in sorted(conocidos.items()):
            if numero in nuevos:
                continue
            if solo and not any(l.es_autor(a) for l in legisladores for a in d.get("autores", [])):
                continue
            resultado = d["estado"]["resultado"]
            if resultado in finales or (resultado == "caduco" and not (es_lunes or completo)):
                continue
            if not a_tiempo():
                raise TimeoutError
            extracto, _, ruta, _ = detalle(portal, numero, con_autores=False, con_comisiones=False)
            antes = [(e["tipo"], e["valor"], e["fecha"]) for e in d.get("eventos_crudos", [])]
            ahora_ev = [(e.tipo, e.valor, e.fecha.isoformat() if e.fecha else None) for e in ruta.eventos]
            comisiones = d["comisiones"]
            if antes != ahora_ev:  # hubo movimiento: puede haber cambiado el giro a comisiones
                comisiones = detalle(portal, numero, con_autores=False)[3]
            desconocidos.update(_guardar(dir_datos, cfg, hoy, numero, extracto or d["extracto"],
                                         d["autores"], ruta, comisiones, ahora))

        if (es_lunes or completo) and not solo:
            advertencias += verificar_bloque_en_linea(portal, cfg.legisladores)
    except PortalError as e:
        ok = False
        advertencias.append(f"La corrida falló: {e}")
    except TimeoutError:
        ok = False
        advertencias.append("La corrida se cortó por tiempo; la próxima continúa desde donde quedó")

    advertencias += [f"Estado desconocido en el portal: {v}" for v in sorted(desconocidos)]
    almacen.construir_indice(dir_datos, cfg.legisladores, cfg.ajustes, ahora)
    almacen.escribir_estado(dir_datos, ok, advertencias, ahora)
    _resumen_github(("✅ Actualización completa" if ok else "❌ La actualización no terminó")
                    + "".join(f"\n- {a}" for a in advertencias))
    return 0 if ok else 1
