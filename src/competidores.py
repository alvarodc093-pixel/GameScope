"""Regla de competidor directo + validación en 3 pilotos (Fase 2).

Idea (explicable a negocio): un competidor comparte dónde se juega,
de qué va y de cuándo es. Sin ML todavía: puntuación transparente.

Regla:
- Mismo grupo (PC / Consola_Sony / Consola_MS_Nintendo / Movil) o familia
  multiplataforma (el juego lista varias plataformas: basta 1 en común).
- >=1 género equivalente (tabla MAPEO, no nombres literales).
- Era: |año - año_piloto| <= 4 (si falta fecha, no elimina pero no suma).
- Score = 2*generos_comunes + 1*plataformas_comunes + 1 si era OK.
- Se excluye el propio juego. Se ordena por score, luego por critic.

Pilotos (existen en ambas fuentes): grand-theft-auto-v, hollow-knight,
bioshock-infinite. Objetivo: >=10 candidatos por piloto y fuente.

Ejecución: python -m src.competidores
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Género RAWG (minúsculas) -> conjunto de géneros IGDB equivalentes.
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
# Inverso para normalizar filas IGDB al vocabulario RAWG.
INVERSO: dict[str, str] = {}
for k, vs in MAPEO.items():
    for v in vs:
        INVERSO.setdefault(v, k)

PILOTOS = ["grand-theft-auto-v", "hollow-knight", "bioshock-infinite"]
BASE = Path(__file__).resolve().parent.parent / "data" / "processed"


def _set(v: str) -> set[str]:
    return {x.strip().lower() for x in (v or "").split("|") if x.strip()}


def _canon_genres(source: str, raw: str) -> set[str]:
    gs = _set(raw)
    if source == "igdb":
        return {INVERSO.get(g, g) for g in gs}
    return gs


def _year(d: str) -> int | None:
    try:
        return int((d or "")[:4])
    except ValueError:
        return None


def load() -> list[dict]:
    rows = list(csv.DictReader((BASE / "muestra_normalizada.csv").open(encoding="utf-8")))
    for r in rows:
        r["_g"] = _canon_genres(r["source"], r["genre_names"])
        r["_p"] = _set(r["platform_names"])
        r["_y"] = _year(r["release_date"])
    return rows


def _critic_key(v) -> float:
    """Clave de desempate: numérico o -1 si ausente (nunca rompe el orden)."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return -1.0


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
    print(f"Filas base: {len(rows)}")
    for slug in PILOTOS:
        for src in ("rawg", "igdb"):
            cand = [r for r in rows if r["source"] == src and (r["slug"] or "") == slug]
            if not cand:
                print(f"\n{slug} [{src}]: NO está en la muestra")
                continue
            p = cand[0]
            print(f"\n{slug} [{src}]: {p['name']} | g={sorted(p['_g'])} | y={p['_y']} | plats={len(p['_p'])}")
            comps = competidores(rows, p)
            print(f"  candidatos: {len(comps)} (objetivo >=10): "
                  f"{'OK' if len(comps) >= 10 else 'BAJO UMBRAL'}")
            for c in comps[:5]:
                print(f"   {c['score']}pts {c['name']} [{c['grupo']}] g={c['generos']} "
                      f"era={c['era_ok']} critic={c['critic']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
