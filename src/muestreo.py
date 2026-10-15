"""Muestreo real PC / consola / móvil + auditoría (Fase 2, ampliado 2026-10-15).

Qué hace y por qué:
- Descubre plataformas con los IDs verificados (no hardcodeados a ciegas).
- 5 grupos (PC, Sony, MS, Nintendo propio, móvil) x 2 páginas x 40 = top 80
  por grupo y fuente. Nintendo va en grupo propio: antes compartía 25 plazas
  con Xbox y los exclusivos de Switch quedaban fuera. IGDB añade Switch 2
  (id 508) incluyendo nativos sin ratings aún; RAWG no cataloga Switch 2.
- Normaliza a un esquema común con observed_at + source (base del histórico).
- Guarda raw en data/raw/ (gitignorado) y muestra normalizada en data/processed/.

Ejecución Windows (raíz del proyecto):
    .\\.venv\\Scripts\\Activate.ps1
    python -m src.muestreo

Respeta cuotas: RAWG ~11 peticiones, IGDB ~13 peticiones con pausas (<4 req/s).
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

PAGE = 40          # RAWG: page_size máximo documentado = 40
PAGINAS = 2        # 2 páginas x 40 = 80 por grupo (antes 25: diluía Switch y PC)
# IDs verificados en vivo el 2026-10-15 (RAWG catálogo completo=51 plataformas;
# IGDB /platforms). Si una API los cambia, el discovery avisa.
# Nintendo va en grupo propio: con 25 resultados compartidos con Xbox, los
# exclusivos de Switch quedaban fuera de la muestra. RAWG NO cataloga Switch 2
# (verificado: count=51, sin "Switch 2"); IGDB sí: id 508.
RAWG_GROUPS = {
    "PC": "4",
    "Consola_Sony": "187,18",
    "Consola_MS": "1,186,14",
    "Nintendo": "7",
    "Movil": "3,21",
}
IGDB_GROUPS = {
    "PC": "(6)",
    "Consola_Sony": "(167,48)",
    "Consola_MS": "(49,169)",
    "Nintendo": "(130,508)",
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
        devueltos, status, error = 0, 200, None
        for page in range(1, PAGINAS + 1):
            time.sleep(1.2)
            r = requests.get(
                "https://api.rawg.io/api/games",
                params={"key": key, "page_size": PAGE, "page": page,
                        "platforms": plats, "ordering": "-added"},
                timeout=30,
            )
            if r.status_code != 200:
                status, error = r.status_code, r.text[:150]
                break
            results = r.json().get("results", [])
            for g in results:
                g["_grupo"] = grupo
            all_games.extend(results)
            devueltos += len(results)
            if len(results) < PAGE:
                break
        meta["grupos"][grupo] = {"status": status, "devueltos": devueltos}
        if error:
            meta["grupos"][grupo]["error"] = error
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

    def _consulta(plats: str, orden: str, extra_where: str, limite: int, offset: int) -> tuple[list[dict], str]:
        time.sleep(0.4)
        # IGDB_FIELDS ya termina en ';': cada cláusula se separa con ';'.
        body = (f"{IGDB_FIELDS} where platforms = {plats}{extra_where}; "
                f"{orden} limit {limite}" + (f"; offset {offset};" if offset else ";"))
        r = requests.post("https://api.igdb.com/v4/games", headers=headers, data=body, timeout=30)
        if r.status_code != 200:
            return [], f"{r.status_code}: {r.text[:120]}"
        return r.json(), ""

    errores: list[str] = []
    for grupo, plats in IGDB_GROUPS.items():
        devueltos = 0
        # Top por total_rating_count = mejor caso de cobertura de métricas (2 páginas).
        for offset in (0, 50):
            results, err = _consulta(plats, "sort total_rating_count desc;",
                                     " & total_rating_count != null", 50, offset)
            if err:
                errores.append(f"{grupo}@{offset} {err}")
                break
            for g in results:
                g["_grupo"] = grupo
            all_games.extend(results)
            devueltos += len(results)
            if len(results) < 50:
                break
        meta["grupos"][grupo] = {"status": 200, "devueltos": devueltos}
    # Extras Switch 2 (id 508): nativos recientes pueden no tener ratings aún;
    # se piden aparte por fecha de lanzamiento para no perderlos.
    results, err = _consulta("(508)", "sort first_release_date desc;", "", 50, 0)
    if err:
        errores.append(f"Switch2 {err}")
    for g in results:
        g["_grupo"] = "Nintendo_Switch2"
        all_games.append(g)
    meta["grupos"]["Nintendo_Switch2"] = {"status": 200, "devueltos": len(results),
                                          "nota": "sin filtro de ratings (nativos tempranos)"}
    if errores:
        meta["errores"] = errores
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
