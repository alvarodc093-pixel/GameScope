# 08 — Caso de prueba: Hollow Knight + GTA V (datos reales 2026-10-15, snapshot 1.131)

## 1. Piloto IGDB — Hollow Knight (modo v1)

Comando: `python -m src.scoring --slug hollow-knight --source igdb --top 10`.

Referencia: Hollow Knight (2017-02-24) [igdb]. Directos+secundarios: **440** (114 directo + 326 secundario) de 629 candidatos IGDB. Descartes: 142 sin género común, 7 sin plataforma común, 10 con género ausente (30 relacionados quedan bajo el umbral).

| Nota | Tier | Juego | Por qué |
|---|---|---|---|
| 1.000 | directo | Hollow Knight: Godmaster | action+indie+platformer, 6 plats, Δ1a, mismo estudio |
| 1.000 | directo | She Sees Red | action+indie, 5 plats, Δ2a |
| 0.857 | directo | Night in the Woods / Brawlhalla | 2–3 géneros, 5–7 plats, Δ0a, distinto estudio |
| 0.857 | directo | Enter the Gungeon / What Remains of Edith Finch / Neo Cab… | action+indie, 4–8 plats, Δ0–2a |

Controles: Super Mario Odyssey (action+platformer, 2 plats, Δ0a) entra como directo 0.857; Call of Duty: Mobile queda descartado por "sin plataforma común"; 10 casos con género ausente dan `insuficiente`, nunca puntúan. En esta foto no hay filas sin fecha (0 en ambas fuentes): la regla "fecha ausente = era 0" sigue implementada y cubierta por tests unitarios.

## 2. Mismo piloto en modo estricto (`--estricto`)

Directos+secundarios: **191** (de 440). La admisión exige año en ambas partes y ≥2 géneros en común con los mismos pesos: la lista se limpia de "solo 1 género" sin mover umbrales. Top idéntico en las primeras plazas (Godmaster, She Sees Red…).

## 3. Piloto RAWG — Grand Theft Auto V (otra escala, sin estudio)

Comando: `python -m src.scoring --slug grand-theft-auto-v --source rawg --top 8`.

Referencia: Grand Theft Auto V (2013-09-17) [rawg]. Directos+secundarios: **340**; el top son todos 0.800 con **un solo género `action`** (0.6) — Transistor, Darksiders II Deathinitive, Path of Exile, Mortal Kombat X, CoD MW3, The Long Dark, SteamWorld Heist, Shadow of Mordor. Útil pero generoso: es la evidencia que justifica el endurecimiento.

## 4. GTA V en modo estricto: 0 con diagnóstico (caso límite documentado)

`--estricto` devuelve **0 competidores** y el motivo real, sin rellenar nada:

```
Referencia con 1 género(s): action. Mínimo estricto = 2 géneros en común.
340 candidatos: solo 1 género en común (mínimo 2 en estricto)
159 candidatos: sin género común
  1 candidatos: sin plataforma común
```

RAWG cataloga GTA V con un único género, así que **ningún** candidato puede superar el mínimo de 2: 0 es la respuesta correcta, no un fallo. La web muestra el mismo caso con mensaje explícito ("la referencia solo tiene 1 género… desactiva «Regla»") en lugar de una lista vacía sin explicación. Lección: el modo estricto es una admisión del usuario, no una verdad; con referencias de un solo género en RAWG hay que apagarlo.

## 5. Limitación

Candidatos = snapshot (muestra top+mid+cola, no el catálogo entero); era ±4; mismo título ≠ mismo juego (el matching cruzado es aparte y con confianza declarada). La evolución temporal sí está activa: hay ≥2 snapshots (`docs/06`).
