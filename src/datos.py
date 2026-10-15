"""Helpers de datos compartidos por snapshot, scoring, competidores y export.

Concentra aquí lo que antes estaba duplicado entre módulos:
- Tabla de equivalencias de géneros RAWG<->IGDB (MAPEO/INVERSO).
- Deduplicacion por (source, source_id) conservando la fila con mas plataformas.
- Utilidades de parsing: presente, year, conjuntos, numeros.
- Localizacion del ultimo snapshot versionado (sin fechas hardcodeadas).
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / "data" / "snapshots"

# Género RAWG (minúsculas) -> conjunto de géneros IGDB equivalentes.
# Documentado en docs/05_equivalencias_competidores.md.
MAPEO = {
    "action": {"adventure"},
    "adventure": {"adventure"},
    "shooter": {"shooter"},
    "rpg": {"role-playing (rpg)"},
    "indie": {"indie"},
    "platformer": {"platform"},
    "puzzle": {"puzzle"},
    "racing": {"racing"},
    "sports": {"sport"},
    "simulation": {"simulator"},
    "strategy": {"strategy", "turn-based strategy (tbs)", "tactical", "real time strategy (rts)"},
    "arcade": {"arcade"},
    "fighting": {"fighting"},
    "massively multiplayer": set(),  # sin equivalente directo en IGDB
    "casual": set(),
    "family": {"family"},
}
# Inverso: vocabulario IGDB -> vocabulario canónico RAWG (primera clave gana).
INVERSO: dict[str, str] = {}
for _k, _vs in MAPEO.items():
    for _v in _vs:
        INVERSO.setdefault(_v, _k)


def presente(v) -> bool:
    """Hay dato util: ni vacio ni el literal 'None' (los CSV guardan nulos como '')."""
    return str(v if v is not None else "").strip() not in ("", "None")


def numero(v) -> float | None:
    try:
        return float(v) if presente(v) else None
    except (TypeError, ValueError):
        return None


def entero(v) -> int | None:
    n = numero(v)
    return int(n) if n is not None else None


def year_de(d: str | None) -> int | None:
    try:
        return int((d or "")[:4])
    except ValueError:
        return None


def conjunto_de(v: str | None) -> set[str]:
    return {x.strip().lower() for x in (v or "").split("|") if x.strip()}


def generos_canonicos(source: str, raw: str | None) -> set[str]:
    """Normaliza géneros al vocabulario canónico (RAWG) para poder comparar."""
    gs = conjunto_de(raw)
    return {INVERSO.get(g, g) for g in gs} if source == "igdb" else gs


def n_plataformas(row: dict) -> int:
    return len([x for x in (row.get("platform_names") or "").split("|") if x.strip()])


def dedup_fuente_id(rows: list[dict]) -> list[dict]:
    """Una fila por (source, source_id): conserva la de mas plataformas (mas informacion).

    Las APIs devuelven el mismo juego en varios grupos de muestreo cuando es
    multiplataforma; sin esto la muestra top pasa de 200 filas a 110 unicos.
    """
    best: dict[tuple, dict] = {}
    for r in rows:
        k = (r.get("source"), str(r.get("source_id")))
        n = n_plataformas(r)
        prev = best.get(k)
        if prev is None or n > n_plataformas(prev):
            best[k] = r
    return sorted(best.values(), key=lambda r: (r.get("source") or "", str(r.get("source_id") or "")))


def cargar_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def snapshots(disponibles: list[Path] | None = None) -> list[Path]:
    """Snapshots ordenados cronologicamente (nombre ISO-like: fecha [+ hora])."""
    files = disponibles if disponibles is not None else list(SNAP_DIR.glob("snapshot_*.csv"))
    return sorted(files, key=lambda p: p.stem)


def ultimo_snapshot(dir_: Path | None = None) -> Path | None:
    files = snapshots() if dir_ is None else sorted(dir_.glob("snapshot_*.csv"), key=lambda p: p.stem)
    return files[-1] if files else None
