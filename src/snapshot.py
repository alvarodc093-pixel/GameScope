"""Snapshot versionado + KPIs (GameScope) — append-only real.

Por qué: congela una foto deduplicada y fechada de lo observado para poder
comparar la evolución cuando se repita el muestreo. Cada ejecución crea
`data/snapshots/snapshot_AAAAMMDDTHHMMSSZ.csv` (timestamp UTC): dos ejecuciones
del mismo día NO se pisan (antes el nombre solo-fecha sobrescribia la foto del
mismo día, rompiendo la garantía append-only documentada en docs/06).

Al lado del CSV escribe un `*.meta.json` con los KPIs de la captura
(n por fuente, cobertura, rango de observed_at) para trazabilidad.

Ejecución: python -m src.snapshot
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import datos  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
SNAP_DIR = ROOT / "data" / "snapshots"


def dedup_con_nplat(rows: list[dict]) -> list[dict]:
    """Dedup por (source, source_id) conservando la fila con más plataformas.

    Devuelve copias con `n_plataformas` calculado (columna del snapshot).
    """
    out = []
    for r in datos.dedup_fuente_id(rows):
        r = dict(r)
        r["n_plataformas"] = datos.n_plataformas(r)
        out.append(r)
    return out


def kpis(uniq: list[dict]) -> dict:
    resumen: dict = {"n": len(uniq), "por_fuente": {}}
    for src in ("rawg", "igdb"):
        sub = [r for r in uniq if r.get("source") == src]
        con_critica = sum(1 for r in sub if datos.presente(r.get("critic_score")))
        con_usuario = sum(1 for r in sub if datos.presente(r.get("user_score")))
        multi = sum(1 for r in sub if datos.n_plataformas(r) > 1)
        resumen["por_fuente"][src] = {
            "n": len(sub), "con_critica": con_critica, "con_usuario": con_usuario,
            "multiplataforma": multi,
        }
    obs = [r.get("observed_at") for r in uniq if datos.presente(r.get("observed_at"))]
    resumen["observed_at_min"] = min(obs) if obs else None
    resumen["observed_at_max"] = max(obs) if obs else None
    return resumen


def escribir_snapshot(uniq: list[dict], snap_dir: Path) -> tuple[Path, Path]:
    """Escribe CSV + meta.json en snap_dir. Nombre con hora: nunca sobrescribe."""
    snap_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = snap_dir / f"snapshot_{stamp}.csv"
    n = 1
    while out.exists():  # defensa: dos ejecuciones en el mismo segundo
        n += 1
        out = snap_dir / f"snapshot_{stamp}_{n}.csv"
    cols = [c for c in uniq[0] if not c.startswith("_")] if uniq else []
    if uniq and "n_plataformas" not in cols:
        cols.append("n_plataformas")
    import csv as _csv
    with out.open("w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in uniq:
            w.writerow({c: r.get(c, "") for c in cols})
    meta = kpis(uniq)
    meta["archivo"] = out.name
    meta["creado_en"] = datetime.now(timezone.utc).isoformat()
    meta["append_only"] = True
    meta_path = out.with_suffix(".csv.meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return out, meta_path


def main(proc_dir: Path | None = None, snap_dir: Path | None = None) -> int:
    proc_dir = proc_dir or PROC_DIR
    snap_dir = snap_dir or SNAP_DIR
    rows: list[dict] = []
    for fn, oleada in (("muestra_normalizada.csv", "top"),
                       ("muestra_midtail.csv", "mid"),
                       ("muestra_longtail.csv", "longtail")):
        path = proc_dir / fn
        if not path.exists():
            print(f"Aviso: falta {fn}; se omite esta oleada.")
            continue
        for r in datos.cargar_csv(path):
            r["oleada"] = oleada
            rows.append(r)
    if not rows:
        print("No hay muestras en data/processed/: ejecuta primero src.muestreo.")
        return 1
    uniq = dedup_con_nplat(rows)
    out, meta_path = escribir_snapshot(uniq, snap_dir)
    k = kpis(uniq)
    print(f"Snapshot: {out.name} filas_unicas={len(uniq)} (base={len(rows)}) -> {meta_path.name}")
    for src, s in k["por_fuente"].items():
        print(f"{src}: n={s['n']} critic={s['con_critica']} user={s['con_usuario']} multi={s['multiplataforma']}")
    print("Observed_at:", k["observed_at_min"], "->", k["observed_at_max"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
