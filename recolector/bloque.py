"""Compara la lista del bloque con la página oficial de legisladores."""
import re

from bs4 import BeautifulSoup

from .config import Legislador
from .util import normalizar

URL_LEGISLADORES = "https://legislaturacba.gob.ar/legisladores/"
CLASE_UCR = "unión-cívica-radical"


def verificar_bloque(html: str, legisladores: list[Legislador]) -> list[str]:
    oficiales = {}
    for span in BeautifulSoup(html, "html.parser").select("span.premium-gallery-img-name"):
        item = span.find_parent(class_=lambda c: c and "premium-gallery-item" in c)
        if item and CLASE_UCR in (item.get("class") or []):
            nombre = re.sub(r"^\d+\s*-\s*", "", span.get_text(strip=True))
            oficiales[normalizar(nombre)] = nombre
    if not oficiales:
        return ["No se pudo leer la lista oficial de legisladores (¿cambió la página?)"]
    propios = {normalizar(l.nombre_portal.replace(",", "")): l.nombre_portal for l in legisladores}
    return ([f"Nuevo en el bloque según la web oficial: {oficiales[k]}" for k in oficiales if k not in propios]
            + [f"Ya no figura en el bloque según la web oficial: {propios[k]}" for k in propios if k not in oficiales])
