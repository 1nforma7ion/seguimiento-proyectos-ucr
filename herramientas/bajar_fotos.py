"""Copia una vez las fotos de los legisladores desde la web pública del bloque a sitio/fotos/.

Uso manual: python herramientas/bajar_fotos.py
Para agregar a alguien: sumar su slug y la URL de su foto (la de la web del bloque).
"""
from pathlib import Path

import requests

BASE = "https://aaryktyqpkubsycqoqdo.supabase.co/storage/v1/object/public/fotos/"
FOTOS = {
    "austin": "4bb3ded9-76f2-4573-9a58-7c5f4e9c1660/1790354197742.webp",
    "bottasso": "c61bd3a7-656b-4ed5-9af2-d752006add81/1790357834157.webp",
    "bria": "5e3a2c00-398f-4904-be0f-bbfd18c8c710/1790822400531.webp",
    "briner": "da93717b-0ebb-4c4b-b67b-56b5278be804/1790355447226.webp",
    "carignano": "193a26be-c57c-4a06-bbc1-101e9a893ff1/1790822405600.webp",
    "contrera": "f6f2f8f1-d306-4ca8-b4df-a83be67c1c0b/1790822404191.webp",
    "ferrero": "ce2c86ca-218f-4b4d-9e9f-2e975641a84a/1790320460726.webp",
    "grich": "eb863c71-d082-4102-ae00-296df3ce1981/1790355303925.webp",
    "gudino": "0742d8d2-dbd4-4f49-b796-49cab08f1b9a/1790354777934.webp",
    "gvozdenovich": "dae550eb-eeb7-400f-a195-7f61ffe4d01b/1790354388314.webp",
    "jaimes": "2a3d841b-dfce-45a4-86f7-937271d12a3d/1790354904925.webp",
    "luna": "24b1da26-ffa9-4405-880a-3f885ac81568/1790355053828.webp",
    "molina": "69281310-808d-40d1-8f4b-7efb3e210dbc/1790822402216.webp",
    "nicolas": "8e5e0a1d-b925-4555-a9fa-3a372c49e896/1790354671750.webp",
    "nigro": "c7d3ea53-05f4-438f-aa1f-8021cae70a30/1790354030602.webp",
    "saliba": "acac4e47-a0cd-4048-bd9d-e3cf4ee6f7e7/1790355172632.webp",
    "szpanin": "3c432e98-9dab-4b7c-853b-0490fa862f8a/1790353862660.webp",
    "valiente": "4ff5f54a-682a-4b06-ba24-44f27d1687df/1790353676058.webp",
}

destino = Path(__file__).resolve().parent.parent / "sitio" / "fotos"
destino.mkdir(parents=True, exist_ok=True)
for slug, ruta in FOTOS.items():
    r = requests.get(BASE + ruta, timeout=30)
    r.raise_for_status()
    if not r.content.startswith(b"RIFF"):
        raise SystemExit(f"{slug}: no es una imagen webp")
    (destino / f"{slug}.webp").write_bytes(r.content)
    print(slug, len(r.content) // 1024, "KB")
