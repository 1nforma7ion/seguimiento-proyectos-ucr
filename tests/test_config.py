from conftest import RAIZ
from recolector.config import cargar_config


def test_config_tiene_18_legisladores_con_slug_unico():
    cfg = cargar_config(RAIZ)
    assert len(cfg.legisladores) == 18
    assert len({l.slug for l in cfg.legisladores}) == 18


def test_departamentales():
    cfg = cargar_config(RAIZ)
    assert {l.slug for l in cfg.legisladores if l.departamental} == {
        "valiente", "nigro", "jaimes", "luna", "saliba", "grich", "briner", "molina", "carignano"}


def test_es_autor_ignora_tildes():
    cfg = cargar_config(RAIZ)
    bria = next(l for l in cfg.legisladores if l.slug == "bria")
    assert bria.es_autor("Bria, Jose Alberto")
    assert bria.es_autor("BRÍA, José Alberto")
    assert not bria.es_autor("Bria, Otro")


def test_ajustes_y_etapas_cargados():
    cfg = cargar_config(RAIZ)
    assert cfg.ajustes["dias_por_caducar"] == 60
    assert cfg.etapas["estados"]["Caducado"]["resultado"] == "caduco"
