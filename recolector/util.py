import re
import unicodedata


def normalizar(s: str) -> str:
    """Sin tildes, en minúsculas y con los espacios colapsados."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalizar(s)).strip("-")


def decodificar(b: bytes) -> str:
    """El portal responde en cp1252; algunas páginas pueden venir en UTF-8."""
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp1252", errors="replace")
