"""Primer snapshot versionado + KPIs v1 (GameScope).

Por qué: congela una foto deduplicada y fechada de lo observado para poder
comparar la evolución cuando se repita el muestreo. Append-only: cada
ejecución crea `data/snapshots/snapshot_AAAAMMDD.csv` sin tocar los anteriores.

Ejecución: python -m src.snapshot
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
SNAP_DIR = ROOT / "data" / "snapshots"
SNAP_DIR.mkdir(parents=True, exist_ok=True)


def _present(v) -> bool:
    return str(v if v is not None else "").strip() not in ("", "None")


def main() -> int:
    rows: list[dict] = []
    for fn, oleada in (("muestra_normalizada.csv", "top"), ("muestra_midtail.csv", "mid")):
        for r in csv.DictReader((PROC_DIR / fn).open(encoding="utf-8")):
            r["oleada"] = oleada
            rows.append(r)
    # Dedup por (source, source_id): conserva la fila con más plataformas.
    best: dict[tuple, dict] = {}
    for r in rows:
        k = (r["source"], r["source_id"])
        nplat = len([x for x in (r["platform_names"] or "").split("|") if x.strip()])
        if k not in best or nplat > best[k]["_nplat"]:
            r["_nplat"] = nplat
            best[k] = r
    uniq = sorted(best.values(), key=lambda r: (r["source"], r["source_id"]))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out = SNAP_DIR / f"snapshot_{stamp}.csv"
    cols = [c for c in uniq[0] if not c.startswith("_")] + ["n_plataformas"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in uniq:
            row = {c: r[c] for c in cols if c != "n_plataformas"}
            row["n_plataformas"] = r["_nplat"]
            w.writerow(row)
    print(f"Snapshot: {out.name} filas_unicas={len(uniq)} (base={len(rows)})")
    for src in ("rawg", "igdb"):
        sub = [r for r in uniq if r["source"] == src]
        cc = sum(1 for r in sub if _present(r["critic_score"]))
        uu = sum(1 for r in sub if _present(r["user_score"]))
        mp = sum(1 for r in sub if r["_nplat"] > 1)
        print(f"{src}: n={len(sub)} critic={cc} user={uu} multi={mp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
