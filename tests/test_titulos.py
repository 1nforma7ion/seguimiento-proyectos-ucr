import pytest

from recolector.titulos import titulo_de

CASOS = [
    ("Derogando el Decreto N° 1112/2004 y toda otra normativa que otorgue competencia a la Administración Pública "
     "provincial, para extraer fondos depositados en cuentas bancarias sin previa autorización.",
     "Derogación del Decreto N° 1112/2004"),
    ("Expresando beneplácito por el Festival de las Noches Fortineras, a desarrollarse del 19 al 21 de enero de 2024.",
     "Beneplácito por el Festival de las Noches Fortineras"),
    ("Adhiriendo a las fiestas patronales de la ciudad de Oncativo, Dpto. Río Segundo, a celebrarse el día 15 de mayo.",
     "Adhesión a las fiestas patronales de la ciudad de Oncativo"),
    ("Creando el Régimen de Promoción para Jóvenes Emprendedores de la provincia de Córdoba.",
     "Régimen de Promoción para Jóvenes Emprendedores de la provincia de Córdoba"),
    ("Solicitando al Poder Ejecutivo informe (art. 102 C.P.) sobre diversos aspectos referidos al funcionamiento del "
     "Refugio del Polo Integral de la Mujer, especialmente…",
     "Pedido de informes sobre el funcionamiento del Refugio del Polo Integral de la Mujer"),
    ("Solicitando al Poder Ejecutivo informe (art. 102 C.P.) la cantidad estimada de personas en situación de calle.",
     "Pedido de informes sobre la cantidad estimada de personas en situación de calle"),
    ("Solicitando al Ministerio de Salud la compra de un tomógrafo para el Hospital de Bell Ville.",
     "Pedido al Ministerio de Salud: compra de un tomógrafo para el Hospital de Bell Ville"),
    ("Solicitando al Poder Ejecutivo disponga la reparación de la Ruta Provincial N° 1.",
     "Pedido al Poder Ejecutivo que disponga la reparación de la Ruta Provincial N° 1"),
    ("Reconociendo a la Asociación Civil \"Maestros con Huellas\" de la ciudad de San Francisco, por su labor.",
     "Reconocimiento a la Asociación Civil \"Maestros con Huellas\" de la ciudad de San Francisco"),
    ("Declarando de Interés Legislativo la Semana Provincial de Prevención del Consumo de Drogas.",
     "Declaración de interés legislativo de la Semana Provincial de Prevención del Consumo de Drogas"),
    ("Nota remitida por la Legisladora Gudiño, solicitando la rehabilitación del Proyecto N° 35613/L/22, conforme al art. 111 del R.I.",
     "Pedido de rehabilitación del Proyecto N° 35613/L/22"),
    ("ADHIRIENDO LA PROVINCIA DE CÓRDOBA A LA LEY NACIONAL N° 27043, QUE DECLARA DE INTERÉS NACIONAL EL ABORDAJE INTEGRAL.",
     "Adhesión a la Ley Nacional N° 27043, que declara de interés Nacional el abordaje integral"),
    ("Modificando los artículos 2, 23, 59 y 60 del Reglamento Interno de la Legislatura.",
     "Modificación de los artículos 2, 23, 59 y 60 del Reglamento Interno de la Legislatura"),
    ("Estableciendo que la tasa del 0,2% de la facturación se destinará al ERSeP.",
     "Dispone que la tasa del 0,2% de la facturación se destinará al ERSeP"),
]


@pytest.mark.parametrize("tema,esperado", CASOS)
def test_titulo_de(tema, esperado):
    assert titulo_de(tema) == esperado


def test_titulo_largo_se_corta_en_una_palabra():
    t = titulo_de("Creando el " + "Programa de Acompañamiento Integral " * 6)
    assert len(t) <= 111 and t.endswith("…") and not t.endswith(" …")


def test_tema_mal_separado_usa_el_extracto():
    extracto = "Proyecto de Ley, iniciado por la Legisladora Ferrero, creando el Programa Provincial de Huertas."
    assert titulo_de("Que deberá garantizar el derecho", extracto) == "Programa Provincial de Huertas"
