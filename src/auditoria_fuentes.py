"""Auditoría de fuentes con credenciales reales (Fase 2, medición C1–C7).

Qué hace (evidencia, no texto de manual):
1. Mapea plataformas RAWG (GET /platforms) e IGDB (POST /platform_families + /platforms)
   a familia PC / Consola / Movil / Otro (curaduría por slug/nombre, verificable).
2. Muestra top por familia (1 página por grupo y fuente) y mide:
   - % nulos por campo clave
   - duplicados por (source, source_id) y por (source, source_id, platform_names)
   - cobertura metacritic (RAWG) / aggregated_rating (IGDB) vs rating de usuarios
3. Guarda observed_at + source en cada fila y en el informe; nada se presenta
   como histórico si es una sola observación.

Salidas:
- data/processed/plataformas_mapeo.csv  (mapa vivo con observed_at/source)
- data/raw/auditoria_muestra_<ts>.json   (muestra cruda, gitignorado)
- data/processed/auditoria_cobertura.json (informe de métricas)

Ejecución Windows (raíz del proyecto):
    .\\.venv\\Scripts\\Activate.ps1
    python -m src.auditoria_fuentes

Cuota: ~8 peticiones RAWG + ~8 IGDB (con pausas <4 req/s). Nunca imprime claves.
"""
from __future__ import annotations

import csv
import json
import re
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

# Grupos de muestreo: ids verificados en vivo 2026-10-15 (ver src/muestreo.py).
RAWG_GRUPOS = {"PC": "4", "Consola": "187,18,1,186,7", "Movil": "3,21"}
IGDB_GRUPOS = {"PC": "(6)", "Consola": "(167,48,49,169,130)", "Movil": "(39,34)"}
CAMPOS_NULOS_RAWG = (
    "id", "name", "slug", "released", "metacritic", "rating", "ratings_count",
    "background_image", "platforms", "genres",
)
CAMPOS_NULOS_IGDB = (
    "id", "name", "slug", "first_release_date", "aggregated_rating",
    "aggregated_rating_count", "rating", "rating_count", "cover", "platforms", "genres",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pct(n: int, total: int) -> float:
    return round(100.0 * n / total, 1) if total else 0.0


# ---------------------------------------------------------------------------
# 1) Mapeo de plataformas a PC / Consola / Movil
# ---------------------------------------------------------------------------

def clasificar_rawg(p: dict) -> str:
    """Clasifica una plataforma RAWG por slug/nombre (curaduría explícita)."""
    slug = (p.get("slug") or "").lower()
    name = (p.get("name") or "").lower()
    if slug in {"ios", "android"} or "ios" in slug or "android" in slug:
        return "Movil"
    if slug in {"pc", "macos", "linux", "macintosh", "apple-ii", "commodore-amiga",
                "atari-st", "msx", "zx-spectrum", "amiga", "3do"} and slug != "3do":
        return "PC"
    if any(k in name for k in ("playstation", "xbox", "nintendo", "wii", "game boy",
                               "snes", "nes", "gamecube", "switch", "sega", "dreamcast",
                               "saturn", "mega drive", "master system", "atari 2600",
                               "atari 5200", "atari 7800", "atari 8-bit", "atari lynx",
                               "atari xegs", "atari flashback", "psp", "ps vita",
                               "3ds", "dsi", "super cassette")):
        return "Consola"
    if slug in {"pc", "macos", "linux"}:
        return "PC"
    # Retro ordenadores y outliers: se dejan en Otro salvo que el nombre ayude.
    if slug in {"3do", "jaguar", "game-gear", "neogeo", "neo-geo", "mega-cd",
                "segacd", "dreamcast", "saturn", "master-system", "mega-drive"}:
        return "Consola"
    if slug in {"web", "steam", "itch-io", "epic-games", "gog", "humble-store",
                "nintendo-eshop", "playstation-store", "xbox-store", "app-store",
                "googleplay", "amazon-appstore"}:
        return "Otro"  # tiendas/locales digitales, no hardware
    if any(k in name for k in ("macintosh", "amiga", "commodore", "apple ii", "atari st")):
        return "PC"
    return "Otro"


def clasificar_igdb(platform: dict, familias: dict[int, str]) -> str:
    """Clasifica por platform_family de IGDB; si no hay familia, por nombre/slug."""
    fam_id = platform.get("platform_family")
    fam_name = (familias.get(int(fam_id), "") if fam_id is not None else "").lower()
    name = (platform.get("name") or "").lower()
    slug = (platform.get("slug") or "").lower()
    if fam_name in {"playstation", "xbox", "nintendo", "sega", "snk", "atari"}:
        return "Consola"
    if slug in {"ios", "android", "android-tv", "nokia", "blackberry"} or "ios" in slug:
        return "Movil"
    # Ordenadores domésticos / PCs sin familia en IGDB.
    if any(k in name for k in ("windows", "pc", "mac", "linux", "steam", "dos",
                               "commodore", "amiga", "msx", "zx spectrum", "sharp",
                               "bbc micro", "apple ii", "amstrad", "dragon",
                               "thomson", "microcomputer", "oric", "spectrum",
                               "enterprise 64", "klein", "uzebox")):
        return "PC"
    if fam_name in {"pc", "computer", "macintosh", "linux"}:
        return "PC"
    if fam_name in {"mobile", "ios", "android"}:
        return "Movil"
    # Consolas retro/arcade sin familia: Atari*, Neo Geo, Vectrex, etc.
    if any(k in name for k in ("atari", "neo geo", "vectrex", "intellivision",
                               "colecovision", "odyssey", "fairchild", "channel f",
                               "casio", "epoch", "evercade", "jaguar", "lynx",
                               "wonderswan", "pc engine", "turbografx", "3do",
                               "cd-i", "amico", "ouya", "steam deck", "quest")):
        return "Consola"
    if fam_name:
        return "Consola"
    return "Otro"


def fetch_rawg_plataformas() -> tuple[list[dict], str]:
    """Catálogo completo: RAWG limita page_size a 40, así que se pagina hasta count."""
    key = config.rawg_key()
    assert key, "falta RAWG_API_KEY en .env"
    out: list[dict] = []
    page = 1
    while True:
        time.sleep(1.2)
        r = requests.get(
            "https://api.rawg.io/api/platforms",
            params={"key": key, "page_size": 40, "page": page},
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        results = body.get("results", [])
        out.extend(results)
        if not body.get("next") or not results:
            break
        page += 1
    return out, _now()


def fetch_igdb_plataformas() -> tuple[list[dict], dict[int, str], str]:
    cid, sec = config.igdb_credentials()
    assert cid and sec, "faltan IGDB_CLIENT_ID/SECRET en .env"
    t = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={"client_id": cid, "client_secret": sec, "grant_type": "client_credentials"},
        timeout=20,
    )
    t.raise_for_status()
    headers = {"Client-ID": cid, "Authorization": f"Bearer {t.json()['access_token']}"}
    time.sleep(0.3)
    rf = requests.post(
        "https://api.igdb.com/v4/platform_families",
        headers=headers, data="fields id,name; limit 50;", timeout=30,
    )
    rf.raise_for_status()
    familias = {int(f["id"]): f.get("name") or "" for f in rf.json()}
    time.sleep(0.3)
    rp = requests.post(
        "https://api.igdb.com/v4/platforms",
        headers=headers,
        data="fields id,name,slug,platform_family; limit 500;",
        timeout=30,
    )
    rp.raise_for_status()
    return rp.json(), familias, _now()


def construir_mapeo() -> tuple[list[dict], dict]:
    """Une ambos catálogos en una tabla común PC/Consola/Movil/Otro."""
    observed = _now()
    filas: list[dict] = []

    plats, obs_rawg = fetch_rawg_plataformas()
    for p in plats:
        filas.append({
            "source": "rawg",
            "platform_id": p.get("id"),
            "platform_name": p.get("name"),
            "platform_slug": p.get("slug"),
            "platform_family_id": None,  # RAWG no expone familias en Free
            "platform_family_name": None,
            "familia": clasificar_rawg(p),
            "observed_at": obs_rawg,
        })

    plats_ig, familias, obs_igdb = fetch_igdb_plataformas()
    for p in plats_ig:
        fid = p.get("platform_family")
        filas.append({
            "source": "igdb",
            "platform_id": p.get("id"),
            "platform_name": p.get("name"),
            "platform_slug": p.get("slug"),
            "platform_family_id": fid,
            "platform_family_name": familias.get(int(fid)) if fid is not None else None,
            "familia": clasificar_igdb(p, familias),
            "observed_at": obs_igdb,
        })

    out = PROC_DIR / "plataformas_mapeo.csv"
    cols = list(filas[0].keys())
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)

    resumen: dict = {"observed_at": observed, "filas": len(filas), "por_fuente": {}, "por_familia": {}}
    for r in filas:
        resumen["por_fuente"][r["source"]] = resumen["por_fuente"].get(r["source"], 0) + 1
        k = f"{r['source']}:{r['familia']}"
        resumen["por_familia"][k] = resumen["por_familia"].get(k, 0) + 1
    return filas, resumen


# ---------------------------------------------------------------------------
# 2) Muestra + métricas de nulos / duplicados / ratings
# ---------------------------------------------------------------------------

def fetch_muestra_rawg() -> tuple[list[dict], str]:
    key = config.rawg_key()
    assert key, "falta RAWG_API_KEY en .env"
    out: list[dict] = []
    obs = _now()
    for grupo, plats in RAWG_GRUPOS.items():
        time.sleep(1.2)
        r = requests.get(
            "https://api.rawg.io/api/games",
            params={"key": key, "page_size": 40, "platforms": plats, "ordering": "-added"},
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"RAWG {grupo}: {r.status_code} {r.text[:120]}")
        for g in r.json().get("results", []):
            g["_grupo"] = grupo
            g["_source"] = "rawg"
            g["_observed_at"] = obs
            out.append(g)
    (RAW_DIR / f"auditoria_rawg_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out, obs


def fetch_muestra_igdb() -> tuple[list[dict], str]:
    cid, sec = config.igdb_credentials()
    assert cid and sec, "faltan IGDB_CLIENT_ID/SECRET en .env"
    t = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={"client_id": cid, "client_secret": sec, "grant_type": "client_credentials"},
        timeout=20,
    )
    t.raise_for_status()
    headers = {"Client-ID": cid, "Authorization": f"Bearer {t.json()['access_token']}"}
    campos = (
        "fields id,name,slug,platforms.name,genres.name,first_release_date,"
        "aggregated_rating,aggregated_rating_count,rating,rating_count,cover.url;"
    )
    out: list[dict] = []
    obs = _now()
    for grupo, plats in IGDB_GRUPOS.items():
        time.sleep(0.4)
        r = requests.post(
            "https://api.igdb.com/v4/games",
            headers=headers,
            data=f"{campos} where platforms = {plats} & total_rating_count != null; "
                 f"sort total_rating_count desc; limit 50;",
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"IGDB {grupo}: {r.status_code} {r.text[:120]}")
        for g in r.json():
            g["_grupo"] = grupo
            g["_source"] = "igdb"
            g["_observed_at"] = obs
            out.append(g)
    (RAW_DIR / f"auditoria_igdb_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out, obs


def _presente(v) -> bool:
    return v is not None and str(v).strip() not in ("", "None")


def _plataformas(g: dict, source: str) -> str:
    plats = g.get("platforms") or []
    parts = []
    for p in plats:
        if isinstance(p, dict):
            parts.append(p.get("platform", {}).get("name") if source == "rawg" else p.get("name"))
        else:
            parts.append(str(p))
    return "|".join(x for x in parts if x)


def metricas_fuente(rows: list[dict], source: str) -> dict:
    """Nulos, duplicados y cobertura de ratings para una fuente (una observación)."""
    n = len(rows)
    if not n:
        return {"n": 0}

    def nulo_raw(g: dict, campo: str):
        if source == "rawg":
            return not _presente(g.get(campo))
        # IGDB: cover/url embebidos
        if campo == "cover":
            return not isinstance(g.get("cover"), dict) or not g["cover"].get("url")
        if campo == "platforms":
            return not g.get("platforms")
        return not _presente(g.get(campo))

    campos = CAMPOS_NULOS_RAWG if source == "rawg" else CAMPOS_NULOS_IGDB
    nulos = {c: sum(1 for g in rows if nulo_raw(g, c)) for c in campos}
    nulos_pct = {c: _pct(v, n) for c, v in nulos.items()}

    claves_id = [(source, g.get("id")) for g in rows]
    claves_plat = [(source, g.get("id"), _plataformas(g, source)) for g in rows]
    dup_id = n - len(set(claves_id))
    dup_plat = n - len(set(claves_plat))

    def critic(g):
        return g.get("metacritic") if source == "rawg" else g.get("aggregated_rating")

    def user(g):
        return g.get("rating")

    con_critic = sum(1 for g in rows if _presente(critic(g)))
    con_user = sum(1 for g in rows if _presente(user(g)))
    con_ambas = sum(1 for g in rows if _presente(critic(g)) and _presente(user(g)))

    por_grupo: dict[str, dict] = {}
    for g in rows:
        grupo = g.get("_grupo") or "?"
        d = por_grupo.setdefault(grupo, {"n": 0, "critic": 0, "user": 0, "ambas": 0})
        d["n"] += 1
        if _presente(critic(g)):
            d["critic"] += 1
        if _presente(user(g)):
            d["user"] += 1
        if _presente(critic(g)) and _presente(user(g)):
            d["ambas"] += 1
    for d in por_grupo.values():
        d["critic_pct"] = _pct(d["critic"], d["n"])
        d["user_pct"] = _pct(d["user"], d["n"])
        d["ambas_pct"] = _pct(d["ambas"], d["n"])

    campo_critico = "metacritic" if source == "rawg" else "aggregated_rating"
    return {
        "source": source,
        "n": n,
        "observed_at": rows[0].get("_observed_at"),
        "nulos_conteo": nulos,
        "nulos_pct": nulos_pct,
        "duplicados_source_id": dup_id,
        "duplicados_source_id_platform": dup_plat,
        "unicos_source_id": len(set(claves_id)),
        "ratings": {
            "campo_criticos": campo_critico,
            "con_criticos_pct": _pct(con_critic, n),
            "con_usuarios_pct": _pct(con_user, n),
            "con_ambas_pct": _pct(con_ambas, n),
            "con_alguna_pct": _pct(sum(1 for g in rows if _presente(critic(g)) or _presente(user(g))), n),
        },
        "por_grupo": por_grupo,
    }


def main() -> int:
    print("Auditoría fuentes |", _now(), "|", config.status())
    mapeo, mres = construir_mapeo()
    print(f"Mapeo plataformas: {mres['filas']} filas -> data/processed/plataformas_mapeo.csv")
    print("  por familia:", json.dumps(mres["por_familia"], ensure_ascii=False))

    rg, obs_r = fetch_muestra_rawg()
    ig, obs_i = fetch_muestra_igdb()
    print(f"Muestra RAWG: {len(rg)} filas (observed_at={obs_r})")
    print(f"Muestra IGDB: {len(ig)} filas (observed_at={obs_i})")

    informe = {
        "observed_at": _now(),
        "nota": "Una sola observación (snapshot de auditoría). No es histórico: "
                "comparar solo con futuros observed_at distintos.",
        "mapeo_plataformas": mres,
        "rawg": metricas_fuente(rg, "rawg"),
        "igdb": metricas_fuente(ig, "igdb"),
    }
    out = PROC_DIR / "auditoria_cobertura.json"
    out.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")

    for fuente in ("rawg", "igdb"):
        m = informe[fuente]
        print(f"\n--- {fuente.upper()} (n={m['n']}) ---")
        print("  nulos %:", json.dumps(m["nulos_pct"], ensure_ascii=False))
        print("  dup (source,id):", m["duplicados_source_id"],
              "| dup (source,id,platform):", m["duplicados_source_id_platform"])
        print("  ratings:", json.dumps(m["ratings"], ensure_ascii=False))
        for gname, g in m["por_grupo"].items():
            print(f"  {gname}: n={g['n']} critic={g['critic_pct']}% user={g['user_pct']}% ambas={g['ambas_pct']}%")
    print(f"\nInforme -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
