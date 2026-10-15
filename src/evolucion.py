"""Evolución temporal entre snapshots (GameScope Fase 4).

Compara las dos últimas fotos versionadas y calcula los CAMBIOS de las
métricas observables (crítica, usuarios y sus conteos) por (source, source_id).

Reglas anti-invento:
- Solo compara lo realmente observado en ambos snapshots; un campo ausente
  en cualquiera de los dos queda como "sin dato" (no se calcula delta).
- Con menos de 2 snapshots NO hay evolución: se dice explícitamente en vez
  de reconstruir tendencias con datos actuales.
- No se comparan métricas entre fuentes (escalas y definiciones distintas).
- Estáticos (géneros, plataformas, fecha) no son serie temporal: se ignoran.

Salida: informe por consola + estructura JSON para la web (via src/export_web.py).

Ejecución: python -m src.evolucion
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import datos  # noqa: E402

# Métricas observables con serie temporal válida (intra-fuente).
METRICAS = ("critic_score", "critic_count", "user_score", "user_count")

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / "data" / "snapshots"


def _idx(rows: list[dict]) -> dict[tuple[str, str], dict]:
    return {(r["source"], str(r["source_id"])): r for r in rows}


def _delta(a, b) -> float | None:
    """Delta b-a si ambos son numéricos; None si falta alguno (no se inventa)."""
    na, nb = datos.numero(a), datos.numero(b)
    if na is None or nb is None:
        return None
    return round(nb - na, 3)


def calcular_deltas(anteriores: list[dict], actuales: list[dict]) -> dict:
    """Compara dos oleadas deduplicadas. Devuelve cambios + altas/bajas.

    Función pura (sin ficheros): entradas = filas de snapshot ya cargadas.
    """
    ia, ib = _idx(anteriores), _idx(actuales)
    cambios = []
    for k in sorted(ia.keys() & ib.keys()):
        ra, rb = ia[k], ib[k]
        fila = {
            "source": k[0], "source_id": k[1],
            "name": rb.get("name") or ra.get("name"),
            "slug": rb.get("slug") or ra.get("slug"),
            "metricas": {},
        }
        tiene = False
        for m in METRICAS:
            d = _delta(ra.get(m), rb.get(m))
            fila["metricas"][m] = {
                "antes": datos.numero(ra.get(m)),
                "ahora": datos.numero(rb.get(m)),
                "delta": d,
            }
            if d is not None and d != 0:
                tiene = True
        if tiene:
            cambios.append(fila)
    # Orden: mayor cambio absoluto de crítica primero (usuarios como desempate).
    cambios.sort(key=lambda f: (
        -abs(f["metricas"]["critic_score"]["delta"] or 0),
        -abs(f["metricas"]["user_score"]["delta"] or 0),
        (f["name"] or "").lower(),
    ))
    return {
        "n_anteriores": len(ia), "n_actuales": len(ib),
        "con_cambio": len(cambios),
        "altas": sorted([{"source": k[0], "source_id": k[1], "name": ib[k].get("name")}
                         for k in ib.keys() - ia.keys()], key=lambda x: (x["source"], x["name"] or "")),
        "bajas": sorted([{"source": k[0], "source_id": k[1], "name": ia[k].get("name")}
                         for k in ia.keys() - ib.keys()], key=lambda x: (x["source"], x["name"] or "")),
        "cambios": cambios,
    }


def comparar_ultimos(dir_: Path | None = None) -> dict | None:
    """None si no hay suficientes observaciones (menos de 2 snapshots)."""
    dir_ = dir_ or SNAP_DIR
    files = datos.snapshots() if dir_ == SNAP_DIR else datos.snapshots(list(dir_.glob("snapshot_*.csv")))
    if len(files) < 2:
        return None
    ant = datos.cargar_csv(files[-2])
    act = datos.cargar_csv(files[-1])
    res = calcular_deltas(ant, act)
    res["entre"] = {"anterior": files[-2].stem, "actual": files[-1].stem}
    res["suficientes_observaciones"] = True
    return res


def main() -> int:
    files = datos.snapshots()
    if len(files) < 2:
        print(f"Hay {len(files)} snapshot(s); hacen falta >=2 para calcular evolución.")
        print("Captura una foto nueva cuando repitas el muestreo: python -m src.snapshot")
        print("(No se reconstruyen tendencias con datos actuales: sin observación fechada no hay fila.)")
        return 0
    res = comparar_ultimos()
    print(f"Snapshots: {res['entre']['anterior']} -> {res['entre']['actual']}")
    print(f"Juegos comparados: {res['n_anteriores']} -> {res['n_actuales']}"
          f" | con cambio: {res['con_cambio']} | altas: {len(res['altas'])} | bajas: {len(res['bajas'])}")
    for f in res["cambios"][:15]:
        parts = []
        for m in METRICAS:
            d = f["metricas"][m]["delta"]
            if d:
                parts.append(f"{m} {f['metricas'][m]['antes']}->{f['metricas'][m]['ahora']} ({d:+g})")
        print(f"  {f['name']} [{f['source']}] :: {'; '.join(parts)}")
    if not res["cambios"]:
        print("  Sin cambios de métricas entre ambas fotos (datos idénticos o campos ausentes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
