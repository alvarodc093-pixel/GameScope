"""Scoring de similitud competitivo v1 (GameScope Fase 4) — HEURÍSTICO, no ML.

Incluye el modo estricto (--estricto): admisión de parejas más dura (año en
ambas partes y >=2 géneros en común) con los mismos pesos y umbrales.
Sincronizado con web/js/scoring.js.

Idea: dos juegos son comparables si comparten de qué van (género), dónde se
juegan (plataforma) y de cuándo son (era). El estudio suma solo cuando ambas
partes lo tienen (IGDB); en RAWG ese componente no aplica y no penaliza.

Reglas anti-sesgo:
- Requisitos duros: sin género común o sin plataforma común no hay
  competidor (da igual el resto).
- Un campo ausente aporta 0 y queda registrado; nunca suma.
- La nota se normaliza por el máximo alcanzable con los datos presentes.
- Subgénero, modelo de negocio y audiencia NO entran: no hay fuente válida.

Base de datos: el ÚLTIMO snapshot de data/snapshots/ (antes estaba hardcodeado
a snapshot_20261013.csv y quedaba obsoleto al capturar uno nuevo).

Ejecución: python -m src.scoring --slug hollow-knight --source igdb
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import datos  # noqa: E402

PESOS = {"genero": 3.0, "plataforma": 2.0, "era": 1.0, "estudio": 1.0}
UMBRALES = {"directo": 0.75, "secundario": 0.45, "relacionado": 0.25}
ERA_CERCA = 2
ERA_ANCHA = 4


def puntuar(ref: dict, cand: dict, pesos: dict | None = None,
            umbrales: dict | None = None, estricto: bool = False) -> dict:
    """Devuelve nota normalizada, tier y qué aportó cada componente.

    estricto=True endurece la admisión de parejas SIN tocar pesos ni umbrales:
    exige año en ambas partes y >=2 géneros en común. Fecha ausente =>
    "insuficiente"; un solo género compartido => "descartado". El estudio sigue
    siendo opcional (RAWG no trae developers en listado: exigirlo eliminaría
    todas las parejas RAWG). Sincronizado con web/js/scoring.js.
    """
    pesos = {**PESOS, **(pesos or {})}
    umbrales = {**UMBRALES, **(umbrales or {})}
    if not ref.get("_g"):
        ref = {**ref, "_g": datos.generos_canonicos(ref["source"], ref["genre_names"])}
    if not cand.get("_g"):
        cand = {**cand, "_g": datos.generos_canonicos(cand["source"], cand["genre_names"])}

    g_com = sorted(ref["_g"] & cand["_g"])
    p_com = sorted(datos.conjunto_de(ref["platform_names"]) & datos.conjunto_de(cand["platform_names"]))
    if not ref["_g"] or not cand["_g"]:
        return _veredicto("insuficiente", 0.0, "género ausente en una parte")
    if not g_com:
        return _veredicto("descartado", 0.0, "sin género común")
    if not p_com:
        return _veredicto("descartado", 0.0, "sin plataforma común")
    if estricto:
        y_ref = datos.year_de(ref["release_date"])
        y_cand = datos.year_de(cand["release_date"])
        if y_ref is None or y_cand is None:
            return _veredicto("insuficiente", 0.0, "fecha ausente en modo estricto")
        if len(g_com) < 2:
            return _veredicto("descartado", 0.0, "solo 1 género en común (mínimo 2 en estricto)")

    partes: dict[str, tuple[float, float, str]] = {}  # comp -> (valor, peso, detalle)
    partes["genero"] = (1.0 if len(g_com) >= 2 else 0.6, pesos["genero"],
                        f"{len(g_com)} en común: {'|'.join(g_com)}")
    partes["plataforma"] = (1.0 if len(p_com) >= 2 else 0.5, pesos["plataforma"],
                            f"{len(p_com)} en común")
    y1, y2 = datos.year_de(ref["release_date"]), datos.year_de(cand["release_date"])
    if y1 is None or y2 is None:
        partes["era"] = (0.0, pesos["era"], "fecha ausente: no suma")
    else:
        d = abs(y1 - y2)
        partes["era"] = ((1.0 if d <= ERA_CERCA else 0.5 if d <= ERA_ANCHA else 0.0),
                         pesos["era"], f"diferencia={d} años")
    d1, d2 = datos.conjunto_de(ref["developer_names"]), datos.conjunto_de(cand["developer_names"])
    if d1 and d2:
        partes["estudio"] = (1.0 if d1 & d2 else 0.0, pesos["estudio"],
                             "mismo estudio" if d1 & d2 else "distinto estudio")
    # Sin dev en alguna parte el componente no aplica: ni suma ni resta.

    num = sum(v * w for v, w, _ in partes.values())
    den = sum(w for _, w, _ in partes.values())
    nota = round(num / den, 3)
    tier = ("directo" if nota >= umbrales["directo"]
            else "secundario" if nota >= umbrales["secundario"]
            else "relacionado" if nota >= umbrales["relacionado"] else "descartado")
    return {"tier": tier, "nota": nota, "partes": partes, "motivo": ""}


def _veredicto(tier: str, nota: float, motivo: str) -> dict:
    return {"tier": tier, "nota": nota, "partes": {}, "motivo": motivo}


def cargar(snap: Path | None = None) -> list[dict]:
    """Carga el último snapshot (o el indicado) ya deduplicado y con géneros canónicos."""
    path = snap or datos.ultimo_snapshot()
    if path is None or not path.exists():
        raise FileNotFoundError(
            "No hay snapshots en data/snapshots/: ejecuta `python -m src.snapshot` tras muestrear."
        )
    rows = datos.dedup_fuente_id(datos.cargar_csv(path))
    for r in rows:
        r["_g"] = datos.generos_canonicos(r["source"], r["genre_names"])
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Competidores de un juego (regla v1, con --estricto)")
    ap.add_argument("--slug", default="hollow-knight")
    ap.add_argument("--source", default="igdb", choices=("igdb", "rawg"))
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--estricto", action="store_true",
                    help="admision estricta: año en ambas partes y >=2 géneros en común")
    a = ap.parse_args(argv)
    try:
        rows = [r for r in cargar() if r["source"] == a.source]
    except FileNotFoundError as e:
        print(e)
        return 1
    refs = [r for r in rows if (r["slug"] or "") == a.slug]
    if not refs:
        print(f"El slug no está en el snapshot [{a.source}]")
        return 1
    ref = refs[0]
    modo = "estricto" if a.estricto else "v1"
    print(f"Referencia: {ref['name']} ({ref['release_date']}) [{a.source}] · modo {modo}")
    scored = []
    for r in rows:
        if r["source_id"] == ref["source_id"]:
            continue
        v = puntuar(ref, r, estricto=a.estricto)
        if v["tier"] in ("directo", "secundario"):
            scored.append((v["nota"], r["name"], r["slug"], v))
    scored.sort(key=lambda x: -x[0])
    print(f"Directos+secundarios: {len(scored)}")
    if not scored:
        # Diagnóstico honesto del vacío (nunca imputar datos para rellenar).
        motivos = Counter()
        for r in rows:
            if r["source_id"] == ref["source_id"]:
                continue
            v = puntuar(ref, r, estricto=a.estricto)
            motivos[v["motivo"] or v["tier"]] += 1
        gs = sorted(ref["_g"])
        print(f"  Referencia con {len(gs)} género(s): {', '.join(gs) or 'ninguno'}. "
              + ("Mínimo estricto = 2 géneros en común."
                 if a.estricto else "Revisa filtros/datos."))
        for m, n in motivos.most_common(4):
            print(f"  {n} candidatos: {m}")
    for nota, name, slug, v in scored[:a.top]:
        det = "; ".join(f"{k}={vv}({d})" for k, (vv, _, d) in v["partes"].items())
        print(f" {nota:.3f} [{v['tier']}] {name} ({slug}) :: {det}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
