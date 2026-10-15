"""Muestreo long-tail aleatorio (cubierta de la cola, fuera del top y el mid).

Por qué: top mide el techo y mid el suelo inmediato; esta oleada mide la cola
real del catálogo, donde vive la mayoría de títulos. Sirve para comparar
cobertura de métricas (crítica/usuario/fecha) entre cola y top sin inventar
nada: cada fila es una observación directa de la API con observed_at.

Cómo elige (trazable, sin semillas ocultas):
- RAWG: página ALEATORIA en rango profundo del mismo orden popular que
  top/mid (`ordering=-added`, página 12..50 con page_size 20 => puestos
  240..1000 aproximadamente). Las páginas elegidas se guardan en data/raw/.
- IGDB: offset ALEATORIO (0..800) sobre `total_rating_count != null` con
  `total_rating_count <= 50` (definición operativa de "cola": <=50 votos).
  Si un offset devuelve vacío, se reintenta a mitad (hasta 3 intentos).
- Se excluye todo id ya presente en las oleadas top/mid y en la propia cola
  acumulada: la cola NO rota (rotarla inflaría altas/bajas de la evolución con
  puro ruido de muestreo; ahora solo se añaden juegos nuevos).
- Acumulativo con tope CAP_COLA: al llegar al tope la ejecución se ahorra las
  peticiones y no toca el fichero.

Ejecución: python -m src.muestreo_longtail
Cuota prevista: ~5 peticiones RAWG + ~6 IGDB (con reintentos) + 1 token.
"""
from __future__ import annotations

import csv
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.muestreo import (  # noqa: E402
    IGDB_FIELDS,
    IGDB_GROUPS,
    RAWG_GROUPS,
    _now,
    norm_igdb,
    norm_rawg,
)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
COLA_PATH = PROC_DIR / "muestra_longtail.csv"

RAWG_PAG_MIN, RAWG_PAG_MAX = 12, 50
RAWG_PAGE_SIZE = 20
IGDB_OFFSET_MAX = 800
IGDB_COLA_MAX = 50  # <=50 votos de usuario = cola operativa
IGDB_LIMIT = 20
CAP_COLA = 500


def _ids_existentes() -> set[tuple[str, str]]:
    """Ids ya cubiertos por top/mid: la cola solo aporta juegos nuevos."""
    ids: set[tuple[str, str]] = set()
    for fn in ("muestra_normalizada.csv", "muestra_midtail.csv"):
        path = PROC_DIR / fn
        if not path.exists():
            continue
        for r in csv.DictReader(path.open(encoding="utf-8")):
            ids.add((r["source"], r["source_id"]))
    return ids


def _present(v) -> bool:
    return str(v if v is not None else "").strip() not in ("", "None")


def main() -> int:
    # Cola acumulada: si ya está al tope, no se consume cuota.
    existentes_filas: list[dict] = []
    cols_previas: list[str] | None = None
    if COLA_PATH.exists():
        rd = csv.DictReader(COLA_PATH.open(encoding="utf-8"))
        cols_previas = rd.fieldnames
        existentes_filas = list(rd)
        if len(existentes_filas) >= CAP_COLA:
            print(f"LONG-TAIL: cola completa ({len(existentes_filas)}/{CAP_COLA}); "
                  "sin peticiones nuevas esta ejecución.")
            return 0

    observed = _now()
    key = config.rawg_key()
    cid, sec = config.igdb_credentials()
    assert key and cid and sec, "falta .env"
    rng = random.Random()  # sin semilla fija: trazabilidad vía meta en data/raw/
    existentes = _ids_existentes()
    for r in existentes_filas:
        existentes.add((r.get("source", ""), r.get("source_id", "")))

    elecciones: dict = {"rawg_paginas": {}, "igdb_offsets": {}}
    filas: list[tuple[str, dict]] = []
    excluidos = 0

    # RAWG: página profunda aleatoria por grupo (mismo orden que top/mid).
    for grupo, plats in RAWG_GROUPS.items():
        pagina = rng.randint(RAWG_PAG_MIN, RAWG_PAG_MAX)
        elecciones["rawg_paginas"][grupo] = pagina
        time.sleep(1.2)
        r = requests.get(
            "https://api.rawg.io/api/games",
            params={"key": key, "page": pagina, "page_size": RAWG_PAGE_SIZE,
                    "platforms": plats, "ordering": "-added"},
            timeout=30,
        )
        if r.status_code != 200:
            elecciones["rawg_paginas"][grupo] = f"error {r.status_code}"
            continue
        for g in r.json().get("results", []):
            if ("rawg", str(g.get("id"))) in existentes:
                excluidos += 1
                continue
            g["_grupo"] = grupo + "_long"
            filas.append(("rawg", g))

    # IGDB: offset aleatorio sobre la cola (<=50 votos, sin nulos).
    tok = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={"client_id": cid, "client_secret": sec, "grant_type": "client_credentials"},
        timeout=20,
    ).json()["access_token"]
    h = {"Client-ID": cid, "Authorization": f"Bearer {tok}"}
    for grupo, plats in IGDB_GROUPS.items():
        offset = rng.randint(0, IGDB_OFFSET_MAX)
        for intento in range(3):
            elecciones["igdb_offsets"][grupo] = offset
            time.sleep(0.4)
            body = (f"{IGDB_FIELDS} where platforms = {plats} "
                    f"& total_rating_count != null & total_rating_count <= {IGDB_COLA_MAX}; "
                    f"sort total_rating_count desc; limit {IGDB_LIMIT}; offset {offset};")
            r = requests.post("https://api.igdb.com/v4/games", headers=h, data=body, timeout=30)
            results = r.json() if r.status_code == 200 else []
            if results:
                break
            offset //= 2  # fuera de rango: acortar
        for g in results:
            if ("igdb", str(g.get("id"))) in existentes:
                excluidos += 1
                continue
            g["_grupo"] = grupo + "_long"
            filas.append(("igdb", g))

    rows = [(norm_rawg(g, observed) if s == "rawg" else norm_igdb(g, observed))
            for s, g in filas]
    if not rows:
        print("LONG-TAIL: 0 filas nuevas (revisa elecciones en data/raw/).")
        return 1
    hueco = max(0, CAP_COLA - len(existentes_filas))
    nuevas = rows[:hueco]
    if not nuevas:
        print(f"LONG-TAIL: sin hueco bajo el tope ({CAP_COLA}); nada que añadir.")
        return 0
    cols = cols_previas or list(nuevas[0].keys())
    with COLA_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(existentes_filas)
        w.writerows(nuevas)
    total = len(existentes_filas) + len(nuevas)
    (RAW_DIR / f"longtail_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json").write_text(
        json.dumps({"observed_at": observed, "elecciones": elecciones,
                    "nuevas": len(nuevas), "cola_total": total, "cap": CAP_COLA,
                    "excluidos_por_duplicado": excluidos,
                    "descartadas_por_cap": len(rows) - len(nuevas),
                    "nota": "RAWG pagina profundo -added; IGDB cola total_rating_count<=50; "
                            "cola acumulativa (no rota) para no inflar altas/bajas"},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"LONG-TAIL: +{len(nuevas)} nuevas (cola total {total}/{CAP_COLA}) "
          f"-> {COLA_PATH.name}")
    print("Elecciones:", json.dumps(elecciones, ensure_ascii=False))

    # Cobertura comparada: cola acumulada vs lo ya observado (top+mid).
    def cob(rows_all: list[dict], etiqueta: str) -> None:
        for src in ("rawg", "igdb"):
            sub = [r for r in rows_all if r.get("source") == src]
            if not sub:
                continue
            cs = sum(1 for r in sub if _present(r.get("critic_score")))
            us = sum(1 for r in sub if _present(r.get("user_score")))
            print(f"  [{etiqueta}] {src}: n={len(sub)} critic={cs} user={us}")

    base = []
    for fn in ("muestra_normalizada.csv", "muestra_midtail.csv"):
        p = PROC_DIR / fn
        if p.exists():
            base += list(csv.DictReader(p.open(encoding="utf-8")))
    print("Cobertura comparada:")
    cob(base, "top+mid")
    cob(existentes_filas + nuevas, "long-tail")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
