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

def listar_autor(portal, id_portal: int, desde: date, hasta: date) -> tuple[dict[str, str], list[date]]:
    """Todos los expedientes del autor con estado parlamentario en [desde, hasta).

    El portal ordena al azar, así que se parte el rango hasta que cada consulta
    entre en una sola página. Un día con más de 10 se recorre varias veces.
    Devuelve {numero: extracto} y los días que no se pudieron completar.
    """
    html = portal.consultar_autor(id_portal, desde, hasta)
    total = parse_total(html)
    encontrados = _resultados(html, total)
    if total <= POR_PAGINA:
        return encontrados, []
    if (hasta - desde).days > 1:
        medio = desde + (hasta - desde) // 2
        a, pend_a = listar_autor(portal, id_portal, desde, medio)
        b, pend_b = listar_autor(portal, id_portal, medio, hasta)
        return {**a, **b}, pend_a + pend_b
    paginas = math.ceil(total / POR_PAGINA)
    for _ in range(MAX_PASADAS):
        for n in range(1, paginas + 1):
            encontrados.update(_resultados(portal.ir_a_pagina(n), total))
        if len(encontrados) >= total:
            return encontrados, []
    return encontrados, [desde]


def _resultados(html: str, total: int) -> dict[str, str]:
    res = {r.numero: r.extracto for r in parse_resultados(html)}
    if total > 0 and not res:
        raise PortalError("El portal informa resultados pero no se pudieron leer: puede que haya cambiado")
    return res


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
    almacen.guardar_expediente(dir_datos, exp, cfg.etapas)
    guardado = almacen.cargar_expediente(dir_datos, numero)
    return guardado.get("desconocidos", [])


MAX_FALLAS_SEGUIDAS = 3


def correr(raiz: Path, portal, hoy: date, ahora: datetime, solo: str | None = None,
           completo: bool = False, limite: datetime | None = None, max_nuevos: int | None = None) -> int:
    raiz = Path(raiz)
    cfg = cargar_config(raiz)
    dir_datos = raiz / "sitio" / "data"
    finales = set(cfg.etapas.get("resultados_finales", []))
    legisladores = [l for l in cfg.legisladores if solo in (None, l.slug)]
    desde_fecha = date.fromisoformat(cfg.ajustes["desde_fecha"])
    ventana = hoy - timedelta(days=cfg.ajustes["dias_ventana_diaria"])
    hasta = hoy + timedelta(days=1)
    if (dir_datos / "expedientes").exists():
        almacen.rederivar(dir_datos, cfg.etapas)  # aplica cambios de reglas a lo ya guardado
    conocidos = {}
    for archivo in (dir_datos / "expedientes").glob("*.json") if (dir_datos / "expedientes").exists() else []:
        d = almacen._leer(archivo)
        conocidos[d["numero"]] = d
    progreso = almacen.cargar_progreso(dir_datos)
    completos, pendientes = progreso["listado_completo"], progreso["dias_pendientes"]

    advertencias, desconocidos, ok = [], set(), True
    nuevos, fallidos = set(), []
    fallas = {"seguidas": 0}

    def a_tiempo():
        if limite is not None and datetime.now(ahora.tzinfo) >= limite:
            raise TimeoutError

    def intentar(numero, funcion) -> bool:
        """Un expediente que falla no corta la corrida, salvo varios seguidos (portal caído)."""
        try:
            funcion()
            fallas["seguidas"] = 0
            return True
        except PortalError as e:
            fallas["seguidas"] += 1
            fallidos.append(f"{numero} ({e})")
            if fallas["seguidas"] >= MAX_FALLAS_SEGUIDAS:
                raise PortalError(f"fallaron {MAX_FALLAS_SEGUIDAS} expedientes seguidos; "
                                  "el portal parece caído") from e
            return False

    def guardar_nuevo(numero, extracto_listado):
        extracto, autores, ruta, comisiones = detalle(portal, numero)
        desconocidos.update(_guardar(dir_datos, cfg, hoy, numero, extracto or extracto_listado,
                                     autores, ruta, comisiones, ahora))
        nuevos.add(numero)

    def refrescar(numero, d):
        extracto, _, ruta, _ = detalle(portal, numero, con_autores=False, con_comisiones=False)
        antes = [(e["tipo"], e["valor"], e["fecha"]) for e in d.get("eventos_crudos", [])]
        despues = [(e.tipo, e.valor, e.fecha.isoformat() if e.fecha else None) for e in ruta.eventos]
        comisiones = d["comisiones"]
        if antes != despues:  # hubo movimiento: puede haber cambiado el giro a comisiones
            comisiones = detalle(portal, numero, con_autores=False)[3]
        desconocidos.update(_guardar(dir_datos, cfg, hoy, numero, extracto or d["extracto"],
                                     d["autores"], ruta, comisiones, ahora))

    try:
        for leg in legisladores:
            a_tiempo()
            carga_completa = completo or leg.slug not in completos
            desde = desde_fecha if carga_completa else ventana
            encontrados, sin_completar = listar_autor(portal, leg.id_portal, desde, hasta)
            for dia in [date.fromisoformat(x) for x in pendientes.get(leg.slug, [])]:
                if desde <= dia < hasta:
                    continue  # ya se volvió a listar dentro del rango de hoy
                extra, sigue = listar_autor(portal, leg.id_portal, dia, dia + timedelta(days=1))
                encontrados.update(extra)
                sin_completar += sigue
            pendientes.pop(leg.slug, None)
            if sin_completar:
                pendientes[leg.slug] = sorted({d.isoformat() for d in sin_completar})
            tenia = any(any(leg.es_autor(a) for a in d.get("autores", [])) for d in conocidos.values())
            if not encontrados and tenia and desde == desde_fecha:
                raise PortalError(f"{leg.nombre_mostrar}: el portal devolvió 0 resultados pero tenía "
                                  "expedientes; puede que el portal haya cambiado")
            incompleto = False
            for numero in sorted(set(encontrados) - set(conocidos) - nuevos):
                if max_nuevos is not None and len(nuevos) >= max_nuevos:
                    incompleto = True
                    break
                a_tiempo()
                if not intentar(numero, lambda: guardar_nuevo(numero, encontrados[numero])):
                    incompleto = True
            if carga_completa and not incompleto:
                completos[leg.slug] = hoy.isoformat()
            almacen.guardar_progreso(dir_datos, progreso)

        es_lunes = hoy.weekday() == 0
        for numero, d in sorted(conocidos.items()):
            if numero in nuevos:
                continue
            if solo and not any(l.es_autor(a) for l in legisladores for a in d.get("autores", [])):
                continue
            resultado = d["estado"]["resultado"]
            if resultado in finales or (resultado == "caduco" and not (es_lunes or completo)):
                continue
            a_tiempo()
            intentar(numero, lambda: refrescar(numero, d))

        if (es_lunes or completo) and not solo:
            advertencias += verificar_bloque_en_linea(portal, cfg.legisladores)
    except PortalError as e:
        ok = False
        advertencias.append(f"La corrida falló: {e}")
    except TimeoutError:
        ok = False
        advertencias.append("La corrida se cortó por tiempo; la próxima continúa desde donde quedó")
    except Exception as e:  # noqa: BLE001 - cualquier error igual deja registrado el estado
        ok = False
        advertencias.append(f"La corrida falló por un error inesperado ({type(e).__name__}: {e})")

    almacen.guardar_progreso(dir_datos, progreso)
    faltan = [l.nombre_mostrar for l in cfg.legisladores if l.slug not in completos]
    if faltan:
        advertencias.append(f"Carga inicial en curso: faltan {len(faltan)} legisladores ({', '.join(faltan)})")
    advertencias += [f"No se pudo leer el expediente {f}" for f in fallidos]
    advertencias += [f"{slug}: el {date.fromisoformat(d):%d/%m/%Y} no se pudieron leer todos los expedientes; "
                     "se reintenta en la próxima corrida" for slug, dias in sorted(pendientes.items()) for d in dias]
    advertencias += [f"Estado desconocido en el portal: {v}" for v in sorted(desconocidos)]
    almacen.construir_indice(dir_datos, cfg.legisladores, cfg.ajustes, ahora)
    almacen.construir_novedades(dir_datos, hoy, cfg.ajustes["dias_novedades"], cfg.etapas)
    # Los datos cuentan como "al día" solo si la corrida terminó bien y ya están todos los legisladores.
    almacen.escribir_estado(dir_datos, ok, advertencias, ahora, al_dia=ok and not faltan)
    _resumen_github(("✅ Actualización completa" if ok else "❌ La actualización no terminó")
                    + "".join("\n- " + a for a in advertencias))
    return 0 if ok else 1
