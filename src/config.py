"""Configuración segura GameScope (Fase 2).

Lee credenciales desde .env sin mostrarlas en logs.
Las claves solo viven en memoria y en el archivo local .env (gitignorado).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

RAW_DIR = ROOT / "data" / "raw"


def _get(name: str) -> str:
    return (os.getenv(name) or "").strip()


def rawg_key() -> str:
    return _get("RAWG_API_KEY")


def igdb_credentials() -> tuple[str, str]:
    return _get("IGDB_CLIENT_ID"), _get("IGDB_CLIENT_SECRET")


def status() -> dict:
    """Solo booleanos y longitudes: nunca devuelve valores reales."""
    k = rawg_key()
    cid, sec = igdb_credentials()
    return {
        "rawg_configurada": bool(k),
        "rawg_longitud": len(k),
        "igdb_configurada": bool(cid and sec),
        "igdb_id_longitud": len(cid),
    }
