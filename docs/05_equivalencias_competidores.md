# 05 — Equivalencias y regla de competidor directo (Fase 2)

Código: `src/competidores.py` (`python -m src.competidores`). Base: 200 filas top.
Medido el 2026-10-13, sin inventar: todo candidato sale de la muestra real.

## 1. Tabla de equivalencias de géneros (vocabularios medidos)

| RAWG | IGDB | Tipo |
|---|---|---|
| Action | Adventure | aproximada (cajón amplio en ambas) |
| Adventure | Adventure | directa |
| Shooter | Shooter | exacta |
| RPG | Role-playing (RPG) | directa |
| Indie | Indie | exacta |
| Platformer | Platform | directa |
| Puzzle | Puzzle | exacta |
| Racing | Racing | exacta |
| Sports | Sport | directa (distinto plural) |
| Simulation | Simulator | directa |
| Strategy | Strategy, Turn-based strategy (TBS), Tactical, Real time strategy (RTS) | 1 a N (subgéneros IGDB) |
| Arcade | Arcade | exacta |
| Fighting | Fighting | exacta |
| Family | Family | directa (poco frecuente) |
| Massively Multiplayer | — | **sin equivalente** |
| Casual | — | **sin equivalente** |
| — | Hack and slash/Beat 'em up, Point-and-click | solo IGDB |

Advertencia: `Action↔Adventure` es la más débil (cubre 84–87% del top). Los pilotos la usan junto a un segundo género para no comparar “todo contra todo”.

## 2. Regla de competidor directo (congelada v1)

1. Misma fuente que el piloto (no se mezclan universos).
2. ≥1 género equivalente (tabla §1) **y** ≥1 plataforma en común.
3. Era: |año − año_piloto| ≤ 4 suma 1 punto; sin fecha no elimina.
4. Score = 2·géneros + 1·plataformas + 1 si era. Se excluye el propio juego y se **deduplica por `source_id`** (la muestra repite el mismo juego en varios grupos por ser multiplataforma).
5. Se ordena por score y luego por crítica.

## 3. Validación en 3 pilotos (únicos, deduplicados)

| Piloto | RAWG únicos | IGDB únicos | Umbral ≥10 | Ejemplos top |
|---|---|---|---|---|
| grand-theft-auto-v (2013) | 22 | 29 | OK | Skyrim, BioShock Infinite / RE7, San Andreas |
| hollow-knight (2017) | 24 | 26 | OK | Limbo, INSIDE / Hades, Stardew Valley |
| bioshock-infinite (2013) | 24 | 27 | OK | MGS V, Tomb Raider / GTA V, Tomb Raider |

Lectura: los 6 casos superan el umbral con resultados sensatos (mismo estante mental del jugador). El conteo bruto sin deduplicar (12/12 topado) inflaba por el mismo juego en varios grupos: **contar siempre únicos por `source_id`**.

## 4. Limitaciones

1. Muestra top: los candidatos son populares; el long-tail dará menos y peores.
2. `Action` es demasiado ancha: endurecer a ≥2 géneros o peso por género raro en la app.
3. Era ±4 es arbitraria: calibrar por franquicia (remasters) en EDA.
4. Mismo título ≠ mismo juego: la regla no fusiona por nombre; el matching cruzado RAWG↔IGDB sigue siendo manual.
5. Sin precio ni región en el score (no hay fuente).

## 5. Decisión

Regla v1 congelada para EDA/app con dedup por `source_id` y métricas lado a lado con su n. Siguiente: EDA de distribuciones/relaciones por grupo y primer snapshot versionado según `04 §3`.
