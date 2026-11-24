"""Uso: python -m recolector [--solo SLUG] [--completo] [--pausa S] [--limite-minutos N] [--max-nuevos N]"""
import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import cargar_config
from .corrida import correr
from .portal import Portal

ARGENTINA = timezone(timedelta(hours=-3))
RAIZ = Path(__file__).resolve().parent.parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="recolector", description="Actualiza los datos del seguimiento de proyectos.")
    ap.add_argument("--solo", help="slug de un legislador (para probar)")
    ap.add_argument("--completo", action="store_true", help="recorre todo el mandato, no solo los últimos días")
    ap.add_argument("--pausa", type=float, help="segundos entre consultas al portal")
    ap.add_argument("--limite-minutos", type=int, help="cortar ordenadamente después de N minutos")
    ap.add_argument("--max-nuevos", type=int, help="traer como máximo N expedientes nuevos (para probar)")
    a = ap.parse_args(argv)

    ahora = datetime.now(ARGENTINA)
    pausa = a.pausa if a.pausa is not None else cargar_config(RAIZ).ajustes["pausa_segundos"]
    limite = ahora + timedelta(minutes=a.limite_minutos) if a.limite_minutos else None
    # El portal también conoce el límite, para no quedar colgado en una consulta larga.
    fin = time.monotonic() + a.limite_minutos * 60 if a.limite_minutos else None
    return correr(RAIZ, Portal(pausa=pausa, fin=fin), ahora.date(), ahora, solo=a.solo, completo=a.completo,
                  limite=limite, max_nuevos=a.max_nuevos)


if __name__ == "__main__":
    sys.exit(main())
