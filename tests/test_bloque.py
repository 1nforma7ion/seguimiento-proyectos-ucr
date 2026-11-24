from conftest import RAIZ, fx
from recolector.bloque import verificar_bloque
from recolector.config import cargar_config


def test_bloque_sin_cambios():
    assert verificar_bloque(fx("legisladores_oficial.html"), cargar_config(RAIZ).legisladores) == []


def test_bloque_detecta_faltante_y_sobrante():
    legs = [l for l in cargar_config(RAIZ).legisladores if l.slug != "bottasso"]
    legs[0].nombre_portal = "Ajeno, Persona"
    adv = verificar_bloque(fx("legisladores_oficial.html"), legs)
    assert "Nuevo en el bloque según la web oficial: Bottasso Gustavo Armando" in adv
    assert any(a.startswith("Nuevo en el bloque según la web oficial: Austin") for a in adv)
    assert "Ya no figura en el bloque según la web oficial: Ajeno, Persona" in adv


def test_bloque_pagina_cambiada():
    adv = verificar_bloque("<html></html>", cargar_config(RAIZ).legisladores)
    assert adv == ["No se pudo leer la lista oficial de legisladores (¿cambió la página?)"]
