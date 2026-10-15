"""Regla de competidor directo + validación en 3 pilotos (Fase 2).

Idea (explicable a negocio): un competidor comparte dónde se juega,
de qué va y de cuándo es. Sin ML todavía: puntuación transparente.

Regla (v1 congelada, docs/05):
- Misma fuente que el piloto (no se mezclan universos).
- >=1 género equivalente (tabla MAPEO, no nombres literales) y >=1 plataforma.
- Era: |año - año_piloto| <= 4 suma 1 punto; sin fecha no elimina.
- Score = 2*generos_comunes + 1*plataformas_comunes + 1 si era OK.
- Se excluye el propio juego y se DEDUPLICA por (source, source_id): la
  muestra repite el mismo juego en varios grupos por ser multiplataforma
  (corregido: antes salían candidatos duplicados en la salida).
- Se ordena por score, luego por critic.

Pilotos (existen en ambas fuentes): grand-theft-auto-v, hollow-knight,
bioshock-infinite. Objetivo: >=10 candidatos por piloto y fuente.

Ejecución: python -m src.competidores
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import datos  # noqa: E402

# Tabla de equivalencias y helpers canónicos viven en src/datos.py.
# Se re-exportan aquí por compatibilidad con el código y docs existentes.
MAPEO = datos.MAPEO
INVERSO = datos.INVERSO

PILOTOS = ["grand-theft-auto-v", "hollow-knight", "bioshock-infinite"]
BASE = Path(__file__).resolve().parent.parent / "data" / "processed"


def load(base: Path | None = None) -> list[dict]:
    """Carga la muestra top deduplicada por (source, source_id)."""
    path = (base or BASE) / "muestra_normalizada.csv"
    rows = datos.dedup_fuente_id(datos.cargar_csv(path))
    for r in rows:
        r["_g"] = datos.generos_canonicos(r["source"], r["genre_names"])
        r["_p"] = datos.conjunto_de(r["platform_names"])
        r["_y"] = datos.year_de(r["release_date"])
    return rows


def _critic_key(v) -> float:
    """Clave de desempate: numérico o -1 si ausente (nunca rompe el orden)."""
    n = datos.numero(v)
    return n if n is not None else -1.0


def competidores(rows: list[dict], piloto: dict, n: int = 12) -> list[dict]:
    out = []
    for r in rows:
        if r["source"] != piloto["source"] or r["source_id"] == piloto["source_id"]:
            continue
        gs = sorted(piloto["_g"] & r["_g"])
        ps = sorted(piloto["_p"] & r["_p"])
        if not gs or not ps:
            continue
        era_ok = (
            piloto["_y"] is not None and r["_y"] is not None and abs(piloto["_y"] - r["_y"]) <= 4
        )
        out.append({
            "name": r["name"], "slug": r["slug"], "grupo": r["grupo"],
            "score": 2 * len(gs) + len(ps) + (1 if era_ok else 0),
            "generos": "|".join(gs), "plats_comunes": len(ps),
            "era_ok": era_ok, "critic": r["critic_score"], "user": r["user_score"],
        })
    out.sort(key=lambda x: (-x["score"], -_critic_key(x["critic"])))
    return out[:n]


def main() -> int:
    rows = load()
    print(f"Filas base (deduplicadas): {len(rows)}")
    ok = True
    for slug in PILOTOS:
        for src in ("rawg", "igdb"):
            cand = [r for r in rows if r["source"] == src and (r["slug"] or "") == slug]
            if not cand:
                print(f"\n{slug} [{src}]: NO está en la muestra")
                continue
            p = cand[0]
            print(f"\n{slug} [{src}]: {p['name']} | g={sorted(p['_g'])} | y={p['_y']} | plats={len(p['_p'])}")
            comps = competidores(rows, p)
            nombres = [c["name"] for c in comps]
            duplicados = len(nombres) - len(set(nombres))
            estado = "OK" if len(comps) >= 10 else "BAJO UMBRAL"
            if len(comps) < 10:
                ok = False
            print(f"  candidatos: {len(comps)} (objetivo >=10): {estado} | duplicados: {duplicados}")
            for c in comps[:5]:
                print(f"   {c['score']}pts {c['name']} [{c['grupo']}] g={c['generos']} "
                      f"era={c['era_ok']} critic={c['critic']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
