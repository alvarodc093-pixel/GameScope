"""Prueba de conectividad IGDB + RAWG (Fase 2, paso 1).

Qué comprueba por API (sin confundir conexión con datos útiles):
- Autenticación correcta (401/403 = credencial inválida).
- Respuesta HTTP + tiempo de respuesta.
- Formato de los datos (claves principales, nº resultados).
- Errores de cuota (429), servidor (5xx) y red.

Seguridad: nunca imprime claves. Solo estados y metadatos.

Ejecución en Windows (VS Code, terminal PowerShell, desde la raíz del proyecto):
    .\\.venv\\Scripts\\Activate.ps1
    python -m src.check_connections

Salida esperada si todo va bien:
    RAWG ... OK (status=200) ... count=51
    IGDB ... OK (status=200) ... muestra 1 juego
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone

import requests

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_error(text: str, limit: int = 200) -> str:
    # Los cuerpos de error no deben arrastrar la key: solo fragmento.
    return (text or "")[:limit]


def test_rawg() -> dict:
    """Mínimo documentado: GET /platforms y GET /games con ?key= (rawg.io/apidocs)."""
    key = config.rawg_key()
    if not key:
        return {"api": "rawg", "ok": False, "error": "falta RAWG_API_KEY en .env"}

    out: dict = {"api": "rawg", "consultas": []}
    try:
        # 1) Plataformas: valida auth y da el mapa PC/consola/móvil (necesario Fase 2 §6).
        t0 = time.perf_counter()
        r = requests.get(
            "https://api.rawg.io/api/platforms",
            params={"key": key, "page_size": 1},
            timeout=20,
        )
        ms = round((time.perf_counter() - t0) * 1000)
        if r.status_code in (401, 403):
            return {"api": "rawg", "ok": False, "error": f"auth {r.status_code}: key inválida o sin permiso"}
        if r.status_code == 429:
            return {"api": "rawg", "ok": False, "error": "429 cuota: esperar y reintentar"}
        if r.status_code != 200:
            return {"api": "rawg", "ok": False, "error": f"{r.status_code}: {_redact_error(r.text)}"}
        body = r.json()
        out["consultas"].append(
            {"endpoint": "GET /platforms", "status": 200, "ms": ms,
             "claves": sorted(body.keys()), "count": body.get("count")}
        )

        # 2) Juegos: comprueba que además de conectar, hay datos útiles.
        time.sleep(1.2)  # respeta cuota Free 20k/mes en pruebas secuenciales
        t0 = time.perf_counter()
        r2 = requests.get(
            "https://api.rawg.io/api/games",
            params={"key": key, "page_size": 3},
            timeout=20,
        )
        ms2 = round((time.perf_counter() - t0) * 1000)
        if r2.status_code != 200:
            out["ok"] = False
            out["error"] = f"games {r2.status_code}: {_redact_error(r2.text)}"
            return out
        b2 = r2.json()
        results = b2.get("results", [])
        out["consultas"].append(
            {"endpoint": "GET /games?page_size=3", "status": 200, "ms": ms2,
             "devueltos": len(results),
             "ejemplo": {"id": results[0].get("id"), "name": results[0].get("name")} if results else None,
             "observed_at": _now(), "source": "rawg"}
        )
        out["ok"] = True
        return out
    except requests.RequestException as e:
        return {"api": "rawg", "ok": False, "error": f"red: {type(e).__name__}"}


def test_igdb() -> dict:
    """Mínimo documentado: token Twitch OAuth2 + POST Apicalypse (api-docs.igdb.com)."""
    cid, sec = config.igdb_credentials()
    if not (cid and sec):
        return {"api": "igdb", "ok": False, "error": "faltan IGDB_CLIENT_ID/SECRET en .env"}

    out: dict = {"api": "igdb", "consultas": []}
    try:
        # 1) Token client_credentials (~60 días). No lleva redirect_uri en este flujo.
        t0 = time.perf_counter()
        t = requests.post(
            "https://id.twitch.tv/oauth2/token",
            params={"client_id": cid, "client_secret": sec, "grant_type": "client_credentials"},
            timeout=20,
        )
        ms = round((time.perf_counter() - t0) * 1000)
        if t.status_code in (400, 401, 403):
            return {"api": "igdb", "ok": False, "error": f"token {t.status_code}: id/secret inválidos"}
        if t.status_code != 200:
            return {"api": "igdb", "ok": False, "error": f"token {t.status_code}: {_redact_error(t.text)}"}
        token = t.json().get("access_token", "")
        out["consultas"].append(
            {"endpoint": "POST oauth2/token", "status": 200, "ms": ms,
             "token_type": "bearer", "expira_aprox_dias": "~60"}
        )
        if not token:
            return {"api": "igdb", "ok": False, "error": "token vacío en respuesta"}

        headers = {"Client-ID": cid, "Authorization": f"Bearer {token}"}

        # 2) Juego mínimo: valida que el token autoriza consultas reales.
        time.sleep(0.3)  # mantiene <4 req/s
        t0 = time.perf_counter()
        g = requests.post(
            "https://api.igdb.com/v4/games",
            headers=headers,
            data="fields id,name; limit 1;",
            timeout=30,
        )
        ms2 = round((time.perf_counter() - t0) * 1000)
        if g.status_code == 401:
            return {"api": "igdb", "ok": False, "error": "401: token caducado o Client-ID inválido"}
        if g.status_code == 429:
            return {"api": "igdb", "ok": False, "error": "429 rate 4 req/s: reintentar con backoff"}
        if g.status_code != 200:
            return {"api": "igdb", "ok": False, "error": f"games {g.status_code}: {_redact_error(g.text)}"}
        sample = g.json()
        out["consultas"].append(
            {"endpoint": "POST /games limit 1", "status": 200, "ms": ms2,
             "devueltos": len(sample), "ejemplo": sample[0] if sample else None,
             "observed_at": _now(), "source": "igdb"}
        )

        # 3) Plataformas: base para cobertura PC/consola/móvil (§6).
        time.sleep(0.3)
        p = requests.post(
            "https://api.igdb.com/v4/platforms",
            headers=headers,
            data="fields id,name,platform_family; limit 3;",
            timeout=30,
        )
        if p.status_code == 200:
            out["consultas"].append(
                {"endpoint": "POST /platforms limit 3", "status": 200,
                 "ejemplo": p.json()[0] if p.json() else None}
            )
        out["ok"] = True
        return out
    except requests.RequestException:
        return {"api": "igdb", "ok": False, "error": "red: fallo de conexión"}


def main() -> int:
    print("Config:", config.status())
    print("Fecha UTC:", _now())
    rawg = test_rawg()
    print("\n--- RAWG ---")
    print(json.dumps(rawg, ensure_ascii=False, indent=2)[:2000])
    igdb = test_igdb()
    print("\n--- IGDB ---")
    print(json.dumps(igdb, ensure_ascii=False, indent=2)[:2000])

    ok = bool(rawg.get("ok") and igdb.get("ok"))
    print("\nResultado:", "OK ambas" if ok else "REVISAR errores arriba")
    print("Lectura: OK = conecta Y devuelve datos útiles (count/ejemplo).")
    print("Si 401/403: revisar .env. Si 429: esperar y repetir. Si red: revisar conexión.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
