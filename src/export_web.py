"""Exporta el snapshot a JSON estático para la web (sin secretos, sin claves).

Genera web/data/games.json + web/data/meta.json desde el último snapshot.
Ejecución: python -m src.export_web
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
SNAPS = sorted((ROOT / "data" / "snapshots").glob("snapshot_*.csv"))
WEB_DATA = ROOT / "web" / "data"
WEB_DATA.mkdir(parents=True, exist_ok=True)

SCALES = {"rawg": {"critic": 100, "user": 5}, "igdb": {"critic": 100, "user": 100}}


def _num(v):
    try:
        return float(v) if v not in (None, "", "None") else None
    except ValueError:
        return None


def _int(v):
    try:
        return int(float(v)) if v not in (None, "", "None") else None
    except ValueError:
        return None


def _list(v):
    return [x.strip() for x in (v or "").split("|") if x.strip()]


def main() -> int:
    snap = SNAPS[-1]
    games = []
    for r in csv.DictReader(snap.open(encoding="utf-8")):
        games.append({
            "source": r["source"], "source_id": r["source_id"], "slug": r["slug"],
            "name": r["name"], "grupo": r["grupo"], "oleada": r.get("oleada", ""),
            "platforms": _list(r["platform_names"]), "genres": _list(r["genre_names"]),
            "year": _int((r["release_date"] or "")[:4]) if (r["release_date"] or "")[:4].isdigit() else None,
            "devs": _list(r["developer_names"]), "pubs": _list(r["publisher_names"]),
            "critic": {"score": _num(r["critic_score"]), "count": _int(r["critic_count"]),
                       "scale": SCALES[r["source"]]["critic"]},
            "user": {"score": _num(r["user_score"]), "count": _int(r["user_count"]),
                     "scale": SCALES[r["source"]]["user"]},
            "game_url": r["game_url"] or None, "image_url": r["image_url"] or None,
            "observed_at": r["observed_at"],
        })
    games.sort(key=lambda g: (g["source"], g["name"].lower()))
    (WEB_DATA / "games.json").write_text(json.dumps(games, ensure_ascii=False), encoding="utf-8")
    meta = {"snapshot": snap.stem, "generated_at": games[0]["observed_at"] if games else None,
            "n": len(games),
            "por_fuente": {s: sum(1 for g in games if g["source"] == s) for s in ("igdb", "rawg")},
            "scoring": "v1", "nota": "Métricas por fuente y escala, sin fusionar."}
    (WEB_DATA / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Juegos: {len(games)} -> web/data/games.json + meta.json ({snap.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
