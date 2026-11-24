import json
from dataclasses import dataclass, field
from pathlib import Path

from .util import normalizar


@dataclass
class Legislador:
    slug: str
    id_portal: int
    nombre_portal: str
    nombre_mostrar: str
    departamental: bool = False
    alias: list[str] = field(default_factory=list)

    def es_autor(self, nombre: str) -> bool:
        n = normalizar(nombre)
        return any(n == normalizar(x) for x in [self.nombre_portal, *self.alias])


@dataclass
class Config:
    legisladores: list[Legislador]
    etapas: dict
    ajustes: dict


def _leer(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


def cargar_config(raiz: Path) -> Config:
    d = Path(raiz) / "config"
    return Config(
        legisladores=[Legislador(**x) for x in _leer(d / "legisladores.json")],
        etapas=_leer(d / "etapas.json"),
        ajustes=_leer(d / "ajustes.json"),
    )
