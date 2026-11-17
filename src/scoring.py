"""Scoring de competidores v2: heurístico y explicable, sin ML.

Dos juegos de la misma fuente son comparables si comparten de qué van
(género), dónde se juegan (plataforma) y de cuándo son (era). El estudio suma
solo cuando ambas partes lo tienen (IGDB); en RAWG no aplica y no penaliza.

Componentes (nota = suma ponderada / suma de pesos aplicables):
- genero (3): Jaccard ponderado por rareza. Cada género pesa
  log(N / nº de juegos de la fuente que lo tienen): compartir "Platform" dice
  más que compartir "Adventure", que está en dos de cada tres juegos de IGDB.
  En v1 bastaba un género común para sacar 0.6, y con eso más de la mitad del
  catálogo era competidor de cualquier juego.
- plataforma (2): 1 si comparten >=2, 0.5 si una.
- era (1): 1 si diferencia <=2 años, 0.5 si <=4, 0 si más o si falta la fecha.
- estudio (1): 1 mismo estudio, 0 distinto; no entra si falta en alguna parte.

Sin género común o sin plataforma común no hay competidor. El modo estricto
(--estricto) exige además año en ambas partes y >=2 géneros en común.

La tabla de rareza se calcula sobre el snapshot cargado (idf_generos). Sin ella
(tests, llamadas sueltas) todos los géneros pesan 1 y el componente es un
Jaccard simple. web/js/scoring.js replica esta lógica; tests/test_paridad_js.py
comprueba que ambas dan la misma nota.

Ejecución: python -m src.scoring --slug hollow-knight --source igdb
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import datos  # noqa: E402

PESOS = {"genero": 3.0, "plataforma": 2.0, "era": 1.0, "estudio": 1.0}
UMBRALES = {"directo": 0.75, "secundario": 0.60, "relacionado": 0.40}
ERA_CERCA = 2
ERA_ANCHA = 4


def redondear3(x: float) -> float:
    """Redondeo a 3 decimales con la misma aritmética que Math.round de la web.

    round() de Python redondea a par y daría notas distintas a la versión JS
    (0.525 frente a 0.526).
    """
    return math.floor(x * 1000 + 0.5) / 1000


def idf_generos(rows: list[dict]) -> dict[str, dict[str, float]]:
    """Rareza de cada género canónico por fuente: log(N / juegos con ese género)."""
    out: dict[str, dict[str, float]] = {}
    for src in sorted({r["source"] for r in rows}):
        sub = [r for r in rows if r["source"] == src]
        df = Counter(g for r in sub for g in _generos(r))
        out[src] = {g: math.log(len(sub) / n) for g, n in df.items()}
    return out


def _generos(r: dict) -> set[str]:
    return r["_g"] if r.get("_g") else datos.generos_canonicos(r["source"], r["genre_names"])


def similitud_genero(g_ref: set[str], g_cand: set[str], pesos_g: dict[str, float] | None) -> float:
    """Jaccard ponderado. Un género fuera de la tabla pesa 1."""
    def peso(g: str) -> float:
        return pesos_g.get(g, 1.0) if pesos_g else 1.0
    den = sum(peso(g) for g in g_ref | g_cand)
    return sum(peso(g) for g in g_ref & g_cand) / den if den else 0.0


def puntuar(ref: dict, cand: dict, pesos: dict | None = None,
            umbrales: dict | None = None, estricto: bool = False,
            idf: dict[str, dict[str, float]] | None = None) -> dict:
    """Nota normalizada (0-1), tier y aportación de cada componente."""
    pesos = {**PESOS, **(pesos or {})}
    umbrales = {**UMBRALES, **(umbrales or {})}
    g_ref, g_cand = _generos(ref), _generos(cand)
    if not g_ref or not g_cand:
        return _veredicto("insuficiente", "género ausente en una parte")
    g_com = sorted(g_ref & g_cand)
    p_com = sorted(datos.conjunto_de(ref["platform_names"]) & datos.conjunto_de(cand["platform_names"]))
    if not g_com:
        return _veredicto("descartado", "sin género común")
    if not p_com:
        return _veredicto("descartado", "sin plataforma común")
    y1, y2 = datos.year_de(ref["release_date"]), datos.year_de(cand["release_date"])
    if estricto:
        if y1 is None or y2 is None:
            return _veredicto("insuficiente", "fecha ausente en modo estricto")
        if len(g_com) < 2:
            return _veredicto("descartado", "solo 1 género en común (mínimo 2 en estricto)")

    partes: dict[str, tuple[float, float, str]] = {}  # componente -> (valor, peso, detalle)
    v_gen = redondear3(similitud_genero(g_ref, g_cand, (idf or {}).get(ref["source"])))
    partes["genero"] = (v_gen, pesos["genero"], f"{len(g_com)} en común: {'|'.join(g_com)}")
    partes["plataforma"] = (1.0 if len(p_com) >= 2 else 0.5, pesos["plataforma"],
                            f"{len(p_com)} en común")
    if y1 is None or y2 is None:
        partes["era"] = (0.0, pesos["era"], "fecha ausente")
    else:
        d = abs(y1 - y2)
        partes["era"] = ((1.0 if d <= ERA_CERCA else 0.5 if d <= ERA_ANCHA else 0.0),
                         pesos["era"], f"diferencia={d} años")
    d1, d2 = datos.conjunto_de(ref["developer_names"]), datos.conjunto_de(cand["developer_names"])
    if d1 and d2:
        partes["estudio"] = (1.0 if d1 & d2 else 0.0, pesos["estudio"],
                             "mismo estudio" if d1 & d2 else "distinto estudio")

    num = sum(v * w for v, w, _ in partes.values())
    den = sum(w for _, w, _ in partes.values())
    nota = redondear3(num / den)
    tier = ("directo" if nota >= umbrales["directo"]
            else "secundario" if nota >= umbrales["secundario"]
            else "relacionado" if nota >= umbrales["relacionado"] else "descartado")
    return {"tier": tier, "nota": nota, "partes": partes, "motivo": ""}


def orden_competidor(nota: float, r: dict) -> tuple:
    """Nota descendente; en empate, más votos de usuarios primero y luego nombre.

    RAWG solo tiene unos pocos géneros amplios, así que muchos candidatos empatan.
    """
    return (-nota, -(datos.entero(r.get("user_count")) or 0), (r.get("name") or "").lower())


def _veredicto(tier: str, motivo: str) -> dict:
    return {"tier": tier, "nota": 0.0, "partes": {}, "motivo": motivo}


def cargar(snap: Path | None = None) -> list[dict]:
    """Carga el último snapshot (o el indicado) deduplicado y con géneros canónicos."""
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
    ap = argparse.ArgumentParser(description="Competidores de un juego (scoring v2)")
    ap.add_argument("--slug", default="hollow-knight")
    ap.add_argument("--source", default="igdb", choices=("igdb", "rawg"))
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--estricto", action="store_true",
                    help="exige año en ambas partes y >=2 géneros en común")
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
    idf = idf_generos(rows)
    print(f"Referencia: {ref['name']} ({ref['release_date']}) [{a.source}] · "
          f"modo {'estricto' if a.estricto else 'normal'}")
    veredictos = [(puntuar(ref, r, estricto=a.estricto, idf=idf), r)
                  for r in rows if r["source_id"] != ref["source_id"]]
    tiers = Counter(v["tier"] for v, _ in veredictos)
    print("Por tier:", dict(tiers.most_common()))
    scored = sorted(((v, r) for v, r in veredictos if v["tier"] in ("directo", "secundario")),
                    key=lambda x: orden_competidor(x[0]["nota"], x[1]))
    print(f"Directos+secundarios: {len(scored)} de {len(veredictos)}")
    if not scored:
        motivos = Counter(v["motivo"] or v["tier"] for v, _ in veredictos)
        print(f"  Géneros de la referencia: {', '.join(sorted(ref['_g'])) or 'ninguno'}")
        for m, n in motivos.most_common(4):
            print(f"  {n} candidatos: {m}")
    for v, r in scored[:a.top]:
        det = "; ".join(f"{k}={vv}({d})" for k, (vv, _, d) in v["partes"].items())
        print(f" {v['nota']:.3f} [{v['tier']}] {r['name']} ({r['slug']}) :: {det}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
