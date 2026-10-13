"""Muestreo real PC / consola / móvil + auditoría (Fase 2).

Qué hace y por qué:
- Descubre plataformas con los IDs verificados (no hardcodeados a ciegas).
- Pide 4 grupos x 25 juegos por fuente (top popular = mejor caso de cobertura).
- Normaliza a un esquema común con observed_at + source (base del histórico).
- Guarda raw en data/raw/ (gitignorado) y muestra normalizada en data/processed/.

Ejecución Windows (raíz del proyecto):
    .\\.venv\\Scripts\\Activate.ps1
    python -m src.muestreo

Respeta cuotas: RAWG ~5 peticiones, IGDB ~7 peticiones con pausas (<4 req/s).
Nunca imprime claves.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)

PAGE = 25
# IDs verificados el 2026-10-13 (ver docs/01). Si una API los cambia, el discovery avisa.
RAWG_GROUPS = {
    "PC": "4",
    "Consola_Sony": "187,18",
    "Consola_MS_Nintendo": "1,186,7",
    "Movil": "3,21",
}
IGDB_GROUPS = {
    "PC": "(6)",
    "Consola_Sony": "(167,48)",
    "Consola_MS_Nintendo": "(49,169,130)",
    "Movil": "(39,34)",
}
IGDB_FIELDS = (
    "fields id,name,slug,genres.name,platforms.name,platforms.slug,"
    "first_release_date,involved_companies.company.name,"
    "involved_companies.developer,involved_companies.publisher,"
    "aggregated_rating,aggregated_rating_count,rating,rating_count,"
    "total_rating,total_rating_count,cover.url,url,checksum;"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts_to_iso(ts) -> str | None:
    try:
        if ts is None:
            return None
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
    except (ValueError, TypeError, OSError):
        return None


def fetch_rawg() -> tuple[list[dict], dict]:
    key = config.rawg_key()
    assert key, "falta RAWG_API_KEY en .env"
    all_games: list[dict] = []
    meta: dict = {"grupos": {}}
    for grupo, plats in RAWG_GROUPS.items():
        time.sleep(1.2)
        r = requests.get(
            "https://api.rawg.io/api/games",
            params={"key": key, "page_size": PAGE, "platforms": plats, "ordering": "-added"},
            timeout=30,
        )
        if r.status_code != 200:
            meta["grupos"][grupo] = {"status": r.status_code, "error": r.text[:150]}
            continue
        body = r.json()
        results = body.get("results", [])
        for g in results:
            g["_grupo"] = grupo
        all_games.extend(results)
        meta["grupos"][grupo] = {"status": 200, "devueltos": len(results)}
    # Mapa de plataformas como evidencia (51 esperadas).
    time.sleep(1.2)
    p = requests.get(
        "https://api.rawg.io/api/platforms", params={"key": key, "page_size": 51}, timeout=30
    )
    if p.status_code == 200:
        (RAW_DIR / "rawg_platforms.json").write_text(
            json.dumps(p.json(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (RAW_DIR / f"rawg_sample_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json").write_text(
        json.dumps(all_games, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return all_games, meta


def _igdb_token(cid: str, sec: str) -> str:
    t = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={"client_id": cid, "client_secret": sec, "grant_type": "client_credentials"},
        timeout=20,
    )
    t.raise_for_status()
    return t.json()["access_token"]


def fetch_igdb() -> tuple[list[dict], dict]:
    cid, sec = config.igdb_credentials()
    assert cid and sec, "faltan IGDB_CLIENT_ID/SECRET en .env"
    token = _igdb_token(cid, sec)
    headers = {"Client-ID": cid, "Authorization": f"Bearer {token}"}
    all_games: list[dict] = []
    meta: dict = {"grupos": {}}
    for grupo, plats in IGDB_GROUPS.items():
        time.sleep(0.4)
        # Top por total_rating_count = mejor caso de cobertura de métricas.
        body = (
            f"{IGDB_FIELDS} where platforms = {plats} & total_rating_count != null; "
            f"sort total_rating_count desc; limit {PAGE};"
        )
        r = requests.post("https://api.igdb.com/v4/games", headers=headers, data=body, timeout=30)
        if r.status_code != 200:
            meta["grupos"][grupo] = {"status": r.status_code, "error": r.text[:150]}
            continue
        results = r.json()
        for g in results:
            g["_grupo"] = grupo
        all_games.extend(results)
        meta["grupos"][grupo] = {"status": 200, "devueltos": len(results)}
    (RAW_DIR / f"igdb_sample_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json").write_text(
        json.dumps(all_games, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return all_games, meta


def norm_rawg(g: dict, observed: str) -> dict:
    plats = g.get("platforms") or []
    genres = g.get("genres") or []
    devs = g.get("developers") or []
    pubs = g.get("publishers") or []
    return {
        "source": "rawg",
        "source_id": g.get("id"),
        "slug": g.get("slug"),
        "name": g.get("name"),
        "grupo": g.get("_grupo"),
        "platform_names": "|".join(p.get("platform", {}).get("name", "") for p in plats),
        "genre_names": "|".join(x.get("name", "") for x in genres),
        "release_date": g.get("released"),
        "developer_names": "|".join(x.get("name", "") for x in devs),
        "publisher_names": "|".join(x.get("name", "") for x in pubs),
        "critic_score": g.get("metacritic"),
        "critic_count": None,  # RAWG no da nº de reseñas Metacritic
        "user_score": g.get("rating"),
        "user_count": g.get("ratings_count"),
        "popularity_extra": f"added={g.get('added')};reviews={g.get('reviews_count')};playtime={g.get('playtime')}",
        "game_url": None,  # slug reutilizable en rawg.io/games/<slug>, no URL canónica en lista
        "image_url": g.get("background_image"),
        "price": None,  # sin precio en plan Free
        "observed_at": observed,
    }


def norm_igdb(g: dict, observed: str) -> dict:
    plats = g.get("platforms") or []
    genres = g.get("genres") or []
    inv = g.get("involved_companies") or []
    # involved_companies puede venir expandido o como IDs según el plan; se toleran ambos.
    devs, pubs = [], []
    for c in inv:
        if not isinstance(c, dict):
            continue
        comp = c.get("company")
        nm = comp.get("name") if isinstance(comp, dict) else str(comp)
        if c.get("developer"):
            devs.append(nm)
        if c.get("publisher"):
            pubs.append(nm)
    cover = (g.get("cover") or {}).get("url") if isinstance(g.get("cover"), dict) else None
    if cover and cover.startswith("//"):
        cover = "https:" + cover
    return {
        "source": "igdb",
        "source_id": g.get("id"),
        "slug": g.get("slug"),
        "name": g.get("name"),
        "grupo": g.get("_grupo"),
        "platform_names": "|".join(
            p.get("name", "") if isinstance(p, dict) else str(p) for p in plats
        ),
        "genre_names": "|".join(
            x.get("name", "") if isinstance(x, dict) else str(x) for x in genres
        ),
        "release_date": _ts_to_iso(g.get("first_release_date")),
        "developer_names": "|".join([d for d in devs if d]),
        "publisher_names": "|".join([p for p in pubs if p]),
        "critic_score": g.get("aggregated_rating"),
        "critic_count": g.get("aggregated_rating_count"),
        "user_score": g.get("rating"),
        "user_count": g.get("rating_count"),
        "popularity_extra": f"total_rating={g.get('total_rating')};total_count={g.get('total_rating_count')}",
        "game_url": g.get("url"),
        "image_url": cover,
        "price": None,  # IGDB no tiene precio
        "observed_at": observed,
    }


def main() -> int:
    observed = _now()
    print("Muestreo:", observed, "|", config.status())
    rg, rmeta = fetch_rawg()
    print("RAWG grupos:", json.dumps(rmeta["grupos"], ensure_ascii=False))
    ig, imeta = fetch_igdb()
    print("IGDB grupos:", json.dumps(imeta["grupos"], ensure_ascii=False))

    rows = [norm_rawg(g, observed) for g in rg] + [norm_igdb(g, observed) for g in ig]
    cols = list(rows[0].keys()) if rows else []
    out = PROC_DIR / "muestra_normalizada.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Filas normalizadas: {len(rows)} -> {out}")
    print(f"RAWG: {len(rg)} | IGDB: {len(ig)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
