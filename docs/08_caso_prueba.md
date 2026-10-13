# 08 — Caso de prueba: Hollow Knight + GTA V (datos reales 2026-10-13)

Comando: `python -m src.scoring --slug hollow-knight --source igdb --top 10`.

Referencia: Hollow Knight (2017-02-24) [igdb]. Directos+secundarios: 85 de 118.

| Nota | Tier | Juego | Por qué |
|---|---|---|---|
| 0.857 | directo | Ratchet & Clank | action+platformer, 2 plats, Δ1a |
| 0.857 | directo | What Remains of Edith Finch | action+indie, 8 plats, Δ0a |
| 0.857 | directo | Hollow Knight: Silksong | 3 géneros + mismo estudio, Δ8a (era 0 compensada) |
| 0.857 | directo | Undertale / Stardew Valley / Moonlighter / Inside / Abzu… | action+indie, 4–8 plats, Δ0–2a |

Controles: Super Mario Odyssey (platformer, Δ0a) entra; un Puzzle sin plataforma común queda descartado; sin fecha la era aporta 0.

Segundo piloto (RAWG, otra escala y sin estudio): `GTA V` → 84 candidatos; top 0.800 con 1 solo género `action` (Transistor, MKX, Shadow of Mordor…): útil pero generoso — justifica el endurecimiento propuesto en `docs/07 §4`.

Limitación: un solo snapshot (sin deltas temporales) y muestra top (candidatos populares).
