# 08 — Caso de prueba del scoring v2 (snapshot 2026-11-16, 1.130 juegos)

Salidas reales de `python -m src.scoring` sobre `snapshot_20261116T152255Z.csv`.
Los nombres de género del detalle son canónicos: el "Adventure" de IGDB aparece
como `action` y "Platform" como `platformer` (tabla de `docs/05`).

## 1. Hollow Knight en IGDB

Comando: `python -m src.scoring --slug hollow-knight --source igdb --top 10`.

Por tier: 9 directos, 35 secundarios, 227 relacionados, 349 descartados y 9 con
género ausente. **Directos+secundarios: 44 de 629.**

| Nota | Tier | Juego | Por qué |
|---|---|---|---|
| 0.857 | directo | Celeste, Dead Cells, Night in the Woods, Arise | mismos 3 géneros, ≥4 plataformas, Δ0–2 años, distinto estudio |
| 0.857 | directo | Hollow Knight: Silksong | mismos géneros y estudio, pero Δ8 años (era = 0) |
| 0.820 | directo | Hollow Knight: Godmaster | añade "Hack and slash", así que el género baja a 0.581; mismo estudio |
| 0.786 | directo | Shovel Knight, Pumpkin Jack, Shantae | mismos géneros, Δ3 años (era = 0.5) |
| 0.720 | secundario | Super Mario Odyssey | comparte Platform y Adventure, no Indie (género 0.679) |

Con la regla v1 este mismo juego tenía 440 competidores directos o secundarios
(el 70 % del catálogo IGDB), y una novela visual en FMV (*She Sees Red*) salía
con 1.000 por compartir Adventure e Indie. En v2 queda en 0.607, justo por
encima del umbral de secundario.

En modo estricto (`--estricto`) siguen siendo 44: todos comparten al menos dos
géneros. El modo estricto solo saca de la lista relacionados con un único género
común.

## 2. Grand Theft Auto V en RAWG: el límite del Jaccard

Comando: `python -m src.scoring --slug grand-theft-auto-v --source rawg --top 6`.

**Directos+secundarios: 55 de 499** (22 directos, 33 secundarios). El top son
todos 1.000: Tomb Raider, Rise of the Tomb Raider, Batman: Arkham Knight,
Assassin's Creed IV, Arkham City y Arkham Origins.

RAWG cataloga GTA V con un único género, `Action`, y esos juegos también. Dos
conjuntos idénticos dan Jaccard 1 aunque el género sea el más común: la rareza
solo baja la nota cuando los conjuntos difieren. Con solo un género la nota
la deciden plataforma y época. El desempate de la lista es el número de votos de
usuarios.

En modo estricto devuelve 0 y explica por qué:

```
Géneros de la referencia: action
339 candidatos: solo 1 género en común (mínimo 2 en estricto)
159 candidatos: sin género común
  1 candidatos: sin plataforma común
```

Con referencias de un solo género el modo estricto no aplica; la web lo indica
con un mensaje en lugar de una lista vacía.

## 3. Limitaciones

Los candidatos son el snapshot (capas top, intermedia y cola larga), no el
catálogo entero. La rareza de cada género se calcula sobre ese mismo snapshot, así
que cambia un poco de una semana a otra. El mismo título no implica el mismo juego:
el enlace entre fuentes va aparte (`src/matching.py`).
