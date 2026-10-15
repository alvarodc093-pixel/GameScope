"""Matching cruzado RAWG↔IGDB: identidad del mismo juego entre fuentes.

Por qué: el mismo juego suele existir en las dos APIs. Enlazarlo permite saltar
de una fuente a la otra en la web SIN fusionar métricas (cada escala sigue
siendo propia y se muestra etiquetada). El enlace es DERIVADO (no observado):
por eso no entra en el snapshot; se exporta aparte a data/processed/matching.csv
y export_web lo adjunta como `contraparte`.

Reglas (explicables, deterministas, sin ML):
1. Nombre normalizado exacto + años compatibles (|Δ|<=2, o un año ausente).
   Si ambos años difieren >2 => NO enlace (evita unir remakes, p. ej.
   Resident Evil 2 de 1998 con el de 2019).
2. Si no hay nombre exacto: mejor similitud de secuencia >=0.95 con el mismo
   guardia de años ("cercano").
3. Varios candidatos exactos => se queda el de menor |Δaño| (desempate por
   orden de snapshot; determinista).
Confianzas: exacto (nombre exacto + año compatible), probable (nombre exacto,
un año ausente), cercano (similitud >=0.95 + año compatible).

Ejecución: python -m src.matching   (tras python -m src.snapshot)
"""
from __future__ import annotations

import csv
import difflib
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import datos  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"

UMBRAL_CERCANO = 0.95
DELTA_AÑO_MAX = 2

_PUNTOS = re.compile(r"[^\w\s]", re.UNICODE)
_ESPACIOS = re.compile(r"\s+")


def normalizar(nombre: str) -> str:
    """Minúsculas sin acentos, sin puntuación, espacios colapsados."""
    s = (nombre or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = _PUNTOS.sub(" ", s)
    return _ESPACIOS.sub(" ", s).strip()


def año_a_int(valor) -> int | None:
    if not valor:
        return None
    m = re.search(r"(19|20)\d{2}", str(valor))
    return int(m.group(0)) if m else None


def años_compatibles(y1: int | None, y2: int | None) -> tuple[bool, str]:
    """(compatible, motivo). Un año ausente => compatible con aviso 'probable'."""
    if y1 is None or y2 is None:
        return True, "año ausente en una parte"
    d = abs(y1 - y2)
    if d <= DELTA_AÑO_MAX:
        return True, f"Δaño={d}"
    return False, f"Δaño={d} > {DELTA_AÑO_MAX} (¿remake u otro juego?)"


def mejor_candidato(fila: dict, candidatos: list[dict]) -> dict | None:
    """Mejor contraparte para `fila` dentro de `candidatos` (otra fuente)."""
    n_obj = normalizar(fila["name"])
    y_obj = año_a_int(fila.get("release_date"))
    exactos = [c for c in candidatos if normalizar(c["name"]) == n_obj]
    if exactos:
        def clave(c: dict) -> tuple:
            y = año_a_int(c.get("release_date"))
            d = abs(y - y_obj) if (y is not None and y_obj is not None) else 99
            return (d, c.get("source_id") or "")
        mejor = min(exactos, key=clave)
        ok, motivo = años_compatibles(y_obj, año_a_int(mejor.get("release_date")))
        if not ok:
            return None
        ausente = y_obj is None or año_a_int(mejor.get("release_date")) is None
        return {"contraparte": mejor,
                "confianza": "probable" if ausente else "exacto",
                "metodo": f"nombre exacto ({motivo})"}
    # Nombre no exacto: similitud de secuencia con guardia de años.
    mejor, mejor_ratio = None, 0.0
    for c in candidatos:
        ok, _ = años_compatibles(y_obj, año_a_int(c.get("release_date")))
        if not ok:
            continue
        r = difflib.SequenceMatcher(None, n_obj, normalizar(c["name"])).ratio()
        if r > mejor_ratio:
            mejor, mejor_ratio = c, r
    if mejor is not None and mejor_ratio >= UMBRAL_CERCANO:
        ausente = y_obj is None or año_a_int(mejor.get("release_date")) is None
        if ausente:
            return {"contraparte": mejor, "confianza": "probable",
                    "metodo": f"similitud={mejor_ratio:.3f}, año ausente"}
        return {"contraparte": mejor, "confianza": "cercano",
                "metodo": f"similitud={mejor_ratio:.3f}"}
    return None


def construir(rows: list[dict]) -> list[dict]:
    """Pares enlazables en AMBAS direcciones a partir de filas del snapshot."""
    por_fuente: dict[str, list[dict]] = {"igdb": [], "rawg": []}
    for r in rows:
        if r.get("source") in por_fuente:
            por_fuente[r["source"]].append(r)
    enlaces: dict[tuple[str, str], dict] = {}
    for origen in ("igdb", "rawg"):
        otro = "rawg" if origen == "igdb" else "igdb"
        for fila in por_fuente[origen]:
            m = mejor_candidato(fila, por_fuente[otro])
            if not m:
                continue
            cp = m["contraparte"]
            enlaces[(fila["source"], fila["source_id"])] = {
                "origen": fila, "destino": cp,
                "confianza": m["confianza"], "metodo": m["metodo"],
            }
            # Simétrico: la contraparte también apunta de vuelta.
            clave_inv = (cp["source"], cp["source_id"])
            if clave_inv not in enlaces:
                enlaces[clave_inv] = {
                    "origen": cp, "destino": fila,
                    "confianza": m["confianza"], "metodo": m["metodo"],
                }
    return list(enlaces.values())


def main() -> int:
    snap = datos.ultimo_snapshot()
    if snap is None:
        print("No hay snapshots: ejecuta `python -m src.snapshot` primero.")
        return 1
    rows = datos.dedup_fuente_id(datos.cargar_csv(snap))
    pares = construir(rows)
    out = PROC_DIR / "matching.csv"
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    campos = ["source", "source_id", "nombre", "slug",
              "contraparte_source", "contraparte_id", "contraparte_nombre",
              "contraparte_slug", "confianza", "metodo"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for p in pares:
            o, d = p["origen"], p["destino"]
            w.writerow({
                "source": o["source"], "source_id": o["source_id"],
                "nombre": o["name"], "slug": o.get("slug", ""),
                "contraparte_source": d["source"], "contraparte_id": d["source_id"],
                "contraparte_nombre": d["name"], "contraparte_slug": d.get("slug", ""),
                "confianza": p["confianza"], "metodo": p["metodo"],
            })
    por_conf: dict[str, int] = {}
    for p in pares:
        por_conf[p["confianza"]] = por_conf.get(p["confianza"], 0) + 1
    pct = round(len(pares) / len(rows) * 100, 1) if rows else 0.0
    print(f"Matching: {len(pares)} filas con contraparte de {len(rows)} ({pct}%) "
          f"-> {out.name}")
    print("Por confianza:", por_conf or "sin enlaces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
