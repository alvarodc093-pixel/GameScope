"""Muestreo mid-tail + release_dates + detalle RAWG (post-Fase 2).

Por qué: el top popular mide el techo. Esto mide el suelo realista:
1) Mid-tail (offset/página 6): % nulos fuera del top.
2) IGDB /release_dates de 10 juegos: granularidad por plataforma.
3) RAWG detalle /games/{id} de 10 juegos: recupera dev/pub y coste.

Ejecución: python -m src.muestreo_midtail
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
from src.muestreo import (  # noqa: E402
    IGDB_GROUPS,
    RAWG_GROUPS,
    IGDB_FIELDS,
    _now,
    norm_igdb,
    norm_rawg,
)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"


def _ids(csv_path: Path, source: str, n: int, step: int = 7) -> list[str]:
    rows = [r for r in csv.DictReader(csv_path.open(encoding="utf-8")) if r["source"] == source]
    groups: dict[str, list[str]] = {}
    for r in rows:
        groups.setdefault(r["grupo"], []).append(r["source_id"])
    out: list[str] = []
    for g in ("PC", "Consola_Sony", "Consola_MS_Nintendo", "Movil"):
        ids = groups.get(g, [])
        out += [ids[i] for i in range(0, len(ids), step)][:3]
    return out[:n]


def main() -> int:
    observed = _now()
    base = PROC_DIR / "muestra_normalizada.csv"
    key = config.rawg_key()
    cid, sec = config.igdb_credentials()
    assert key and cid and sec, "falta .env"

    # 1) MID-TAIL -------------------------------------------------------------
    mid: list[dict] = []
    for grupo, plats in RAWG_GROUPS.items():  # página 6 = fuera del top
        time.sleep(1.2)
        r = requests.get(
            "https://api.rawg.io/api/games",
            params={"key": key, "page": 6, "page_size": 20,
                    "platforms": plats, "ordering": "-added"},
            timeout=30,
        )
        if r.status_code == 200:
            for g in r.json().get("results", []):
                g["_grupo"] = grupo + "_mid"
                mid.append(("rawg", g))
    tok = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={"client_id": cid, "client_secret": sec, "grant_type": "client_credentials"},
        timeout=20,
    ).json()["access_token"]
    h = {"Client-ID": cid, "Authorization": f"Bearer {tok}"}
    for grupo, plats in IGDB_GROUPS.items():  # offset 150 = fuera del top
        time.sleep(0.4)
        body = (f"{IGDB_FIELDS} where platforms = {plats}; "
                f"sort total_rating_count desc; limit 20; offset 150;")
        r = requests.post("https://api.igdb.com/v4/games", headers=h, data=body, timeout=30)
        if r.status_code == 200:
            for g in r.json():
                g["_grupo"] = grupo + "_mid"
                mid.append(("igdb", g))
    rows = [(norm_rawg(g, observed) if s == "rawg" else norm_igdb(g, observed))
            for s, g in mid]
    with (PROC_DIR / "muestra_midtail.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"MID-TAIL filas: {len(rows)}")

    def pct(sub: list[dict], col: str) -> float:
        v = [str(r.get(col) if r.get(col) is not None else "").strip() for r in sub]
        return round(sum(1 for x in v if x in ("", "None")) / len(v) * 100, 1)

    for src in ("rawg", "igdb"):
        sub = [r for r in rows if r["source"] == src]
        cs = sum(1 for r in sub if str(r["critic_score"] if r["critic_score"] is not None else "").strip() not in ("", "None"))
        us = sum(1 for r in sub if str(r["user_score"] if r["user_score"] is not None else "").strip() not in ("", "None"))
        print(f"{src}: n={len(sub)} critic={cs} user={us} "
              f"nulos_fecha={pct(sub,'release_date')}% generos={pct(sub,'genre_names')}%")

    # 2) RELEASE_DATES (10 juegos IGDB) ---------------------------------------
    ig_ids = _ids(base, "igdb", 10)
    time.sleep(0.4)
    rd = requests.post(
        "https://api.igdb.com/v4/release_dates", headers=h,
        data=f"fields game.name,platform.name,date,human,region; "
             f"where game = ({','.join(ig_ids)}); limit 100;",
        timeout=30,
    )
    rd_rows = rd.json() if rd.status_code == 200 else []
    with (PROC_DIR / "release_dates_10.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["game", "platform", "date_iso", "human", "region"])
        w.writeheader()
        for x in rd_rows:
            g = (x.get("game") or {}).get("name", "") if isinstance(x.get("game"), dict) else ""
            p = (x.get("platform") or {}).get("name", "") if isinstance(x.get("platform"), dict) else ""
            ts = x.get("date")
            iso = (datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
                   if ts else "")
            w.writerow({"game": g, "platform": p, "date_iso": iso,
                        "human": x.get("human", ""), "region": x.get("region", "")})
    ngames = len({(x.get("game") or {}).get("name") if isinstance(x.get("game"), dict) else x for x in rd_rows})
    print(f"RELEASE_DATES: status={rd.status_code} filas={len(rd_rows)} juegos_distintos~{ngames}")

    # 3) DETALLE RAWG x10 (dev/pub + coste) ------------------------------------
    rw_ids = _ids(base, "rawg", 10)
    det_ok, dev_ok, pub_ok, ms_tot = 0, 0, 0, 0
    for i in rw_ids:
        time.sleep(1.2)
        t0 = time.perf_counter()
        d = requests.get(f"https://api.rawg.io/api/games/{i}",
                         params={"key": key}, timeout=30)
        ms_tot += round((time.perf_counter() - t0) * 1000)
        if d.status_code == 200:
            det_ok += 1
            b = d.json()
            dev_ok += 1 if b.get("developers") else 0
            pub_ok += 1 if b.get("publishers") else 0
    print(f"RAWG detalle: ok={det_ok}/10 con_dev={dev_ok} con_pub={pub_ok} "
          f"ms_medio={round(ms_tot/max(det_ok,1))} (+1 req/juego)")
    (RAW_DIR / f"midtail_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json").write_text(
        json.dumps({"observed_at": observed, "midtail_n": len(rows),
                    "release_dates_n": len(rd_rows),
                    "rawg_detalle": {"ok": det_ok, "dev": dev_ok, "pub": pub_ok}},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
