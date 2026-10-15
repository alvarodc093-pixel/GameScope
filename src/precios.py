"""Precios de PC actuales vía CheapShark (USD, observación propia).

Por qué: el usuario pidió precios; la única fuente gratuita sin clave que
ofrece precio vigente de PC (multi-tienda, no solo Steam) es CheapShark.
Reglas de honestidad:
- Moneda USD (así publica CheapShark; NO se inventa conversión a EUR).
- Campo `precio_pc` con su PROPIO observed_at (la oferta cambia a diario):
  nunca entra en el snapshot de métricas ni en deltas de evolución.
- Selección determinista: los 60 juegos PC (por plataforma) del último
  snapshot con más votos de usuario, desempate por nombre. ~60 peticiones
  con pausa (CheapShark pide trato cortés, 1 req/~0.7s).
- Solo se acepta contraparte CheapShark con nombre casi idéntico
  (similitud >= 0.90 tras normalizar); si no, el juego queda sin precio en
  lugar de arriesgar un precio de otro título.

Ejecución: python -m src.precios   (tras python -m src.snapshot)
Salida: data/processed/precios_pc.csv (export_web lo adjunta como precio_pc).
"""
from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import datos  # noqa: E402
from src.matching import normalizar  # noqa: E402 (misma regla de nombres)

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"

SELECCION = 60
UMBRAL_NOMBRE = 0.90
PAUSA_S = 0.7
# normalizar() quita puntuación: "PC (Microsoft Windows)" -> "pc microsoft windows".
ES_PC = ("pc", "pc microsoft windows")
# CheapShark rechaza el UA genérico de requests (400 con mensaje explícito).
HEADERS = {"User-Agent": "GameScope-Bootcamp/1.0 (data-analyst project)"}


def es_pc(row: dict) -> bool:
    return any(normalizar(p) in ES_PC for p in datos.conjunto_de(row.get("platform_names")))


def seleccionar_pc(rows: list[dict], n: int = SELECCION) -> list[dict]:
    """Los `n` juegos PC con más votos de usuario (top por popularidad propia)."""
    pc = [r for r in rows if es_pc(r)]

    def clave(r: dict) -> tuple:
        u = datos.entero(r.get("user_count")) or -1
        c = datos.entero(r.get("critic_count")) or -1
        return (-u, -c, r.get("name") or "")
    return sorted(pc, key=clave)[:n]


def mejor_opcion(nombre: str, opciones: list[dict]) -> dict | None:
    """El resultado CheapShark cuyo nombre encaja con el del snapshot."""
    objetivo = normalizar(nombre)
    mejor, mejor_ratio = None, 0.0
    for o in opciones:
        ext = normalizar(o.get("external") or "")
        if not ext:
            continue
        r = 1.0 if ext == objetivo else _ratio(objetivo, ext)
        if r > mejor_ratio:
            mejor, mejor_ratio = o, r
    if mejor is not None and mejor_ratio >= UMBRAL_NOMBRE:
        return mejor
    return None


def _ratio(a: str, b: str) -> float:
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio()


def main() -> int:
    snap = datos.ultimo_snapshot()
    if snap is None:
        print("No hay snapshots: ejecuta `python -m src.snapshot` primero.")
        return 1
    rows = datos.dedup_fuente_id(datos.cargar_csv(snap))
    objetivo = seleccionar_pc(rows)
    observed = datetime.now(timezone.utc).isoformat()
    salidas: list[dict] = []
    consultados, con_precio, sin_coincidencia, errores = 0, 0, 0, 0
    primer_error = None
    cache: dict[str, dict | None] = {}  # mismo nombre en ambas fuentes => 1 petición
    for r in objetivo:
        clave = normalizar(r["name"])
        if clave in cache:
            match = cache[clave]
        else:
            consultados += 1
            time.sleep(PAUSA_S)
            try:
                resp = requests.get("https://www.cheapshark.com/api/1.0/games",
                                    params={"title": r["name"], "limit": 15},
                                    headers=HEADERS, timeout=20)
            except requests.RequestException as e:
                errores += 1
                primer_error = primer_error or f"{type(e).__name__}: {e}"
                continue
            if resp.status_code != 200:
                errores += 1
                primer_error = primer_error or f"HTTP {resp.status_code}: {resp.text[:100]}"
                continue
            match = mejor_opcion(r["name"], resp.json() or [])
            cache[clave] = match
        if not match:
            sin_coincidencia += 1
            continue
        con_precio += 1
        salidas.append({
            "source": r["source"], "source_id": r["source_id"],
            "slug": r.get("slug", ""), "name": r.get("name", ""),
            "cheapshark_game_id": match.get("gameID", ""),
            "steam_app_id": match.get("steamAppID") or "",
            "precio_min_usd": match.get("cheapest", ""),
            "moneda": "USD",
            "en_steam": "1" if match.get("steamAppID") else "0",
            "observed_at": observed,
        })
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    out = PROC_DIR / "precios_pc.csv"
    campos = ["source", "source_id", "slug", "name", "cheapshark_game_id",
              "steam_app_id", "precio_min_usd", "moneda", "en_steam", "observed_at"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(salidas)
    (RAW_DIR / f"precios_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json").write_text(
        json.dumps({"observed_at": observed, "consultados": consultados,
                    "con_precio": con_precio, "sin_coincidencia": sin_coincidencia,
                    "errores": errores, "primer_error": primer_error,
                    "fuente": "CheapShark (USD)", "seleccion": SELECCION},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PRECIOS PC: {con_precio}/{consultados} con precio -> {out.name} "
          f"(sin_coincidencia={sin_coincidencia}, errores={errores}, USD, observed_at propio)")
    if primer_error:
        print("Primer error:", primer_error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
