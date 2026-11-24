from recolector.util import decodificar, normalizar, slug


def test_normalizar():
    assert normalizar("  Bría,  José Alberto ") == "bria, jose alberto"
    assert normalizar("Gudiño") == "gudino"


def test_slug():
    assert slug("Hernández Maqueda") == "hernandez-maqueda"


def test_decodificar_cp1252():
    assert decodificar("Comisión".encode("cp1252")) == "Comisión"


def test_decodificar_utf8():
    assert decodificar("Comisión".encode("utf-8")) == "Comisión"
