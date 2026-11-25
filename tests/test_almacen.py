import json
from datetime import date, datetime, timedelta, timezone

from conftest import RAIZ
from recolector.almacen import (Expediente, cargar_expediente, construir_indice, construir_novedades, rederivar,
                                escribir_estado, guardar_expediente, id_archivo, recortar)
from recolector.config import cargar_config
from recolector.parse import Evento, Ruta

CFG = cargar_config(RAIZ)
M = CFG.etapas
HOY = date(2026, 11, 24)
AR = timezone(timedelta(hours=-3))
AHORA = datetime(2026, 11, 24, 7, 10, tzinfo=AR)


def exp(numero="48498/L/26", eventos=None, autores=("Ferrero, Alejandra",)):
    eventos = eventos or [Evento("Estado", "Ingresado", "Sesión Ordinaria 18 del Período 148", 148, date(2026, 10, 29)),
                          Evento("Estado", "En Comisión", "Sesión Ordinaria 18 del Período 148", 148, date(2026, 10, 29))]
    return Expediente(numero, "Proyecto de Ley, iniciado por la Legisladora Ferrero, creando la Comisión…",
                      list(autores), ["Legislación General"], Ruta(eventos), AHORA)


def leer(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_id_archivo():
    assert id_archivo("48498/L/26") == "48498-L-26"


def test_guardar_nuevo_devuelve_nuevo(tmp_path):
    assert guardar_expediente(tmp_path, exp(), M) == ["Nuevo proyecto en seguimiento"]
    d = leer(tmp_path / "expedientes" / "48498-L-26.json")
    assert d["tipo"] == "ley"
    assert d["estado"]["etapa"] == 2 and d["estado"]["caduca_el"] == "2027-10-29"
    assert d["linea_tiempo"][0]["texto"] == "Se presentó el proyecto"
    assert d["url_portal"] == "https://gld.legislaturacba.gob.ar/Publics/Buscar.aspx?q=48498%2FL%2F26"
    assert d["recolectado"] == "2026-11-24T07:10:00-03:00"


def test_guardar_detecta_evento_nuevo(tmp_path):
    guardar_expediente(tmp_path, exp(), M)
    e2 = exp()
    e2.ruta.eventos.append(Evento("Estado", "Caducado", None, None, date(2027, 10, 29)))
    assert guardar_expediente(tmp_path, e2, M) == ["Caducó: pasaron 12 meses sin tratarse"]


def test_guardar_sin_cambios_devuelve_vacio(tmp_path):
    guardar_expediente(tmp_path, exp(), M)
    assert guardar_expediente(tmp_path, exp(), M) == []


def test_cargar_expediente(tmp_path):
    assert cargar_expediente(tmp_path, "48498/L/26") is None
    guardar_expediente(tmp_path, exp(), M)
    assert cargar_expediente(tmp_path, "48498/L/26")["numero"] == "48498/L/26"


def test_novedades_usan_la_fecha_real_del_movimiento(tmp_path):
    # Un proyecto que el sistema encuentra hoy, pero cuyos movimientos fueron hace semanas,
    # aparece con la fecha de cada movimiento, no con la de hoy.
    guardar_expediente(tmp_path, exp("1/L/26", [
        Evento("Estado", "Ingresado", "S", 148, date(2026, 10, 1)),
        Evento("Estado", "En Comisión", "S", 148, date(2026, 11, 18)),
    ]), M)
    guardar_expediente(tmp_path, exp("2/L/24", [Evento("Estado", "Ingresado", "S", 146, date(2024, 5, 1))]), M)
    construir_novedades(tmp_path, HOY, 30, M)
    assert leer(tmp_path / "novedades.json") == [
        {"numero": "1/L/26", "fecha": "2026-11-18", "texto": "Pasó a estudio en comisión",
         "corto": "Pasó a comisión", "clase": "tramite", "orden": 1},
    ]


def test_novedades_clasifican_y_omiten_situaciones(tmp_path):
    guardar_expediente(tmp_path, exp("1/D/26", [
        Evento("Estado", "Ingresado", "S", 148, date(2026, 11, 18)),
        Evento("Situación", "Sobre Tablas", "S", 148, date(2026, 11, 18)),
        Evento("Estado", "Aprobado", "S", 148, date(2026, 11, 18)),
    ]), M)
    guardar_expediente(tmp_path, exp("2/L/25", [
        Evento("Estado", "Caducado", "S", 148, date(2026, 11, 19)),
    ]), M)
    construir_novedades(tmp_path, HOY, 30, M)
    nov = {(n["numero"], n["corto"]): n["clase"] for n in leer(tmp_path / "novedades.json")}
    assert nov == {("1/D/26", "Se presentó"): "tramite", ("1/D/26", "Aprobado"): "buena", ("2/L/25", "Caducó"): "mala"}


def test_indice_expediente_en_dos_legisladores(tmp_path):
    guardar_expediente(tmp_path, exp(autores=("Ferrero, Alejandra", "Bria, Jose Alberto", "Otro, Ajeno")), M)
    idx = construir_indice(tmp_path, CFG.legisladores, CFG.ajustes, AHORA)
    por_slug = {l["slug"]: l for l in idx["legisladores"]}
    assert por_slug["ferrero"]["expedientes"] == ["48498/L/26"]
    assert por_slug["bria"]["expedientes"] == ["48498/L/26"]
    assert por_slug["austin"]["expedientes"] == []
    assert list(idx["expedientes"]) == ["48498/L/26"]
    assert idx["expedientes"]["48498/L/26"]["autores_bloque"] == ["bria", "ferrero"]
    assert idx["ajustes"]["dias_por_caducar"] == 60
    assert por_slug["bria"]["nombre"] == "José Alberto Bría" and por_slug["valiente"]["departamental"] is True
    assert leer(tmp_path / "indice.json") == idx


def test_titulo_recortado_140():
    largo = "palabra " * 40
    t = recortar(largo, 140)
    assert len(t) <= 141 and t.endswith("…") and not t[:-1].endswith(" ")
    assert recortar("corto", 140) == "corto"


def test_estado_fallido_conserva_ultima_ok(tmp_path):
    t2 = AHORA + timedelta(days=1)
    escribir_estado(tmp_path, True, [], AHORA)
    escribir_estado(tmp_path, False, ["x"], t2)
    d = leer(tmp_path / "estado.json")
    assert d["ultima_actualizacion_ok"] == AHORA.isoformat()
    assert d["ultima_corrida"] == t2.isoformat()
    assert d["ok"] is False and d["advertencias"] == ["x"]


def test_json_utf8_sin_escapar(tmp_path):
    guardar_expediente(tmp_path, exp(), M)
    assert "Comisión" in (tmp_path / "expedientes" / "48498-L-26.json").read_text(encoding="utf-8")


def test_sin_cambios_no_reescribe(tmp_path):
    guardar_expediente(tmp_path, exp(), M)
    otra = exp()
    otra.recolectado = AHORA + timedelta(days=1)
    guardar_expediente(tmp_path, otra, M)
    assert leer(tmp_path / "expedientes" / "48498-L-26.json")["recolectado"] == AHORA.isoformat()


def test_rederivar_completa_datos_viejos_sin_consultar(tmp_path):
    aprobado = exp(eventos=[Evento("Estado", "Ingresado", "S", 148, date(2026, 3, 1)),
                            Evento("Estado", "Aprobado", "S", 148, date(2026, 4, 1))])
    guardar_expediente(tmp_path, aprobado, M)
    ruta = tmp_path / "expedientes" / "48498-L-26.json"
    d = leer(ruta)
    del d["estado"]["fecha_resultado"]          # archivo escrito por una versión anterior
    ruta.write_text(json.dumps(d), encoding="utf-8")
    assert rederivar(tmp_path, M) == 1
    nuevo = leer(ruta)
    assert nuevo["estado"]["fecha_resultado"] == "2026-04-01"
    assert nuevo["recolectado"] == d["recolectado"]
    assert rederivar(tmp_path, M) == 0          # la segunda vez no hay nada que cambiar


def test_indice_foto_solo_si_existe(tmp_path):
    datos = tmp_path / "data"
    (tmp_path / "fotos").mkdir()
    (tmp_path / "fotos" / "ferrero.webp").write_bytes(b"x")
    guardar_expediente(datos, exp(), M)
    idx = construir_indice(datos, CFG.legisladores, CFG.ajustes, AHORA)
    por = {l["slug"]: l for l in idx["legisladores"]}
    assert por["ferrero"]["foto"] == "fotos/ferrero.webp"
    assert por["austin"]["foto"] is None


def test_indice_cargo_y_nombre_portal(tmp_path):
    guardar_expediente(tmp_path, exp(), M)
    por = {l["slug"]: l for l in construir_indice(tmp_path, CFG.legisladores, CFG.ajustes, AHORA)["legisladores"]}
    assert por["ferrero"]["cargo"] == "Presidenta del bloque"
    assert por["austin"]["cargo"] is None
    assert por["bria"]["nombre_portal"] == "Bria, Jose Alberto" and por["bria"]["alias"] == []


def test_indice_n_autores(tmp_path):
    guardar_expediente(tmp_path, exp(autores=("Ferrero, Alejandra", "Otro, Ajeno", "Juez, Daniel")), M)
    idx = construir_indice(tmp_path, CFG.legisladores, CFG.ajustes, AHORA)
    assert idx["expedientes"]["48498/L/26"]["n_autores"] == 3


def test_titulo_del_indice_es_el_tema(tmp_path):
    guardar_expediente(tmp_path, exp(), M)
    idx = construir_indice(tmp_path, CFG.legisladores, CFG.ajustes, AHORA)
    assert idx["expedientes"]["48498/L/26"]["titulo"] == "Creando la Comisión…"
    assert leer(tmp_path / "expedientes" / "48498-L-26.json")["tema"] == "Creando la Comisión…"
