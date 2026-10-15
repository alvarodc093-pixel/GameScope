"""Exporta el snapshot a JSON estático para la web (sin secretos, sin claves).

Genera desde el ÚLTIMO snapshot:
- web/data/games.json     juegos con métricas por fuente y escala (sin fusionar),
  más `contraparte` (identidad cruzada derivada de src/matching.py; el enlace
  apunta a la otra fuente, sus métricas siguen siendo las de su propia fila).
- web/data/meta.json      trazabilidad: snapshot, fechas de observación, cobertura.
- web/data/evolucion.json deltas entre los 2 últimos snapshots; si hay menos de 2,
  queda `suficientes_observaciones: false` (la web lo muestra como estado vacío
  honesto en vez de inventar una tendencia).

Ejecución: python -m src.export_web
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import datos, evolucion  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPS = ROOT / "data" / "snapshots"
WEB_DATA = ROOT / "web" / "data"

SCALES = {"rawg": {"critic": 100, "user": 5}, "igdb": {"critic": 100, "user": 100}}


def _list(v):
    return [x.strip() for x in (v or "").split("|") if x.strip()]


def contrapartes(matching_csv: Path | None = None) -> dict[tuple[str, str], dict]:
    """Identidad cruzada derivada (src/matching.py). Vacío si no existe aún.

    Solo aporta el ENLACE a la otra fuente (id/nombre/confianza); las métricas
    de la contraparte se leen de su propia fila, nunca se copian ni fusionan.
    """
    path = matching_csv or (ROOT / "data" / "processed" / "matching.csv")
    if not path.exists():
        return {}
    out: dict[tuple[str, str], dict] = {}
    for r in csv.DictReader(path.open(encoding="utf-8")):
        out[(r["source"], r["source_id"])] = {
            "source": r["contraparte_source"], "source_id": r["contraparte_id"],
            "slug": r["contraparte_slug"] or None, "name": r["contraparte_nombre"],
            "confianza": r["confianza"],
        }
    return out


def precios_pc(precios_csv: Path | None = None) -> dict[tuple[str, str], dict]:
    """Precio PC de CheapShark (USD) con su PROPIO observed_at. Vacío si falta.

    El precio es una observación aparte (cambia a diario): no entra en el
    snapshot ni en la evolución; solo se adjunta al juego para mostrarlo con
    su fecha y su moneda (USD, sin convertir).
    """
    path = precios_csv or (ROOT / "data" / "processed" / "precios_pc.csv")
    if not path.exists():
        return {}
    out: dict[tuple[str, str], dict] = {}
    for r in csv.DictReader(path.open(encoding="utf-8")):
        if not r.get("precio_min_usd"):
            continue
        out[(r["source"], r["source_id"])] = {
            "usd": r["precio_min_usd"], "moneda": "USD",
            "en_steam": r.get("en_steam") == "1",
            "observed_at": r.get("observed_at"),
            "fuente": "CheapShark",
        }
    return out


def juego_desde_fila(r: dict, contraparte: dict | None = None,
                     precio: dict | None = None) -> dict:
    """Convierte una fila de snapshot al modelo JSON de la web."""
    src = r["source"]
    escala = SCALES.get(src, {"critic": 100, "user": 100})
    year = datos.year_de(r.get("release_date"))
    return {
        "source": src, "source_id": r["source_id"], "slug": r.get("slug"),
        "name": r.get("name"), "grupo": r.get("grupo"), "oleada": r.get("oleada", ""),
        "platforms": _list(r.get("platform_names")), "genres": _list(r.get("genre_names")),
        "year": year,
        "devs": _list(r.get("developer_names")), "pubs": _list(r.get("publisher_names")),
        "critic": {"score": datos.numero(r.get("critic_score")),
                   "count": datos.entero(r.get("critic_count")), "scale": escala["critic"]},
        "user": {"score": datos.numero(r.get("user_score")),
                 "count": datos.entero(r.get("user_count")), "scale": escala["user"]},
        "game_url": r.get("game_url") or None, "image_url": r.get("image_url") or None,
        "observed_at": r.get("observed_at"),
        "contraparte": contraparte,
        "precio_pc": precio,
    }


def construir_juegos(rows: list[dict],
                     cps: dict[tuple[str, str], dict] | None = None,
                     pcs: dict[tuple[str, str], dict] | None = None) -> list[dict]:
    cps = cps or {}
    pcs = pcs or {}
    games = [juego_desde_fila(r, cps.get((r["source"], r["source_id"])),
                              pcs.get((r["source"], r["source_id"])))
             for r in rows]
    games.sort(key=lambda g: (g["source"], (g["name"] or "").lower()))
    return games


def meta_para(games: list[dict], snap: Path, n_snapshots: int) -> dict:
    obs = [g["observed_at"] for g in games if g.get("observed_at")]
    n_cp = sum(1 for g in games if g.get("contraparte"))
    n_precio = sum(1 for g in games if g.get("precio_pc"))
    return {
        "snapshot": snap.stem,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "observed_at_min": min(obs) if obs else None,
        "observed_at_max": max(obs) if obs else None,
        "n_snapshots": n_snapshots,
        "n": len(games),
        "por_fuente": {s: sum(1 for g in games if g["source"] == s) for s in ("igdb", "rawg")},
        "scoring": "v1",
        "matching": {"filas_con_contraparte": n_cp,
                     "nota": "Identidad cruzada derivada (src/matching.py); "
                             "las metricas nunca se fusionan entre fuentes."},
        "precios_pc": {"n": n_precio, "moneda": "USD", "fuente": "CheapShark",
                       "nota": "Observacion propia con fecha (observed_at) fuera del "
                               "snapshot; sin conversion de moneda."},
        "nota": "Metricas por fuente y escala, sin fusionar. observed_at = consulta a la API; generated_at = export.",
    }


def evolucion_para(snap_dir: Path) -> dict:
    """Evolución para la web: deltas reales o bandera honesta de datos insuficientes."""
    files = datos.snapshots(list(snap_dir.glob("snapshot_*.csv")))
    base = {
        "suficientes_observaciones": False,
        "n_snapshots": len(files),
        "mensaje": ("Con 1 solo snapshot no hay serie temporal. Captura una foto nueva "
                    "(python -m src.muestreo y luego python -m src.snapshot) para poder "
                    "comparar observaciones fechadas."),
    }
    if len(files) < 2:
        return base
    res = evolucion.calcular_deltas(datos.cargar_csv(files[-2]), datos.cargar_csv(files[-1]))
    res.update(base)
    res["suficientes_observaciones"] = True
    res["entre"] = {"anterior": files[-2].stem, "actual": files[-1].stem}
    res["mensaje"] = ""
    return res


def main(snap_dir: Path | None = None, web_data: Path | None = None) -> int:
    snap_dir = snap_dir or SNAPS
    web_data = web_data or WEB_DATA
    snap = datos.ultimo_snapshot(snap_dir)
    if snap is None:
        print("No hay snapshots en data/snapshots/: ejecuta `python -m src.snapshot` primero.")
        return 1
    web_data.mkdir(parents=True, exist_ok=True)
    cps = contrapartes()
    pcs = precios_pc()
    games = construir_juegos(datos.cargar_csv(snap), cps, pcs)
    (web_data / "games.json").write_text(json.dumps(games, ensure_ascii=False), encoding="utf-8")
    n_snaps = len(datos.snapshots(list(snap_dir.glob("snapshot_*.csv"))))
    meta = meta_para(games, snap, n_snaps)
    (web_data / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    evo = evolucion_para(snap_dir)
    (web_data / "evolucion.json").write_text(json.dumps(evo, ensure_ascii=False, indent=2), encoding="utf-8")
    # datos.js: los mismos datos como script global. Los modulos ES y fetch() de
    # JSON estan bloqueados en file:// (doble clic); como script, la web funciona
    # con servidor local y tambien abriendo index.html directamente.
    payload = {"games": games, "meta": meta, "evolucion": evo}
    (web_data / "datos.js").write_text(
        "window.GS_DATOS = " + json.dumps(payload, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"Juegos: {len(games)} -> web/data/games.json + meta.json + evolucion.json + datos.js ({snap.name})")
    print("Evolucion:", "activa" if evo["suficientes_observaciones"] else "insuficiente (hace falta 2do snapshot)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
