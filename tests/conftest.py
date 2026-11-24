from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"


def fx_bytes(nombre: str) -> bytes:
    return (FIXTURES / nombre).read_bytes()


def fx(nombre: str) -> str:
    from recolector.util import decodificar
    return decodificar(fx_bytes(nombre))


@pytest.fixture
def raiz():
    return RAIZ
