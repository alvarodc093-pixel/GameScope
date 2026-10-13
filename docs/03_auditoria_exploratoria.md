# 03 — Auditoría exploratoria y viabilidad (Fase 2, datos reales)

Fecha muestra: 2026-10-13T18:34 UTC. Código: `src/muestreo.py` (4 grupos x 25 x 2 fuentes = 200 filas en `data/processed/muestra_normalizada.csv`; raw gitignorado en `data/raw/`).
Muestreo **top popular** (`ordering=-added` RAWG, `sort total_rating_count desc` IGDB): mide el **techo** de cobertura, no el catálogo medio. Todo % es de ese top.

## 1. Muestra obtenida

* RAWG: 25/25 en PC, Consola_Sony (187,18), Consola_MS_Nintendo (1,186,7), Móvil (3,21). Todos `status=200`.
* IGDB: 25/25 en PC (6), Consola_Sony (167,48), Consola_MS_Nintendo (49,169,130), Móvil (39,34). Todos `status=200`.
* Plataformas verificadas: RAWG `count=51` (PC=4, PS5=187, PS4=18, XOne=1, Series=186, Switch=7, iOS=3, Android=21). IGDB familias (PlayStation=1, Xbox=2, Nintendo=5, Linux=4) y slugs (`win=6, ps5=167, ps4--1=48, xboxone=49, series-x-s=169, switch=130, ios=39, android=34`).

## 2. Campos: lo que hay de verdad (ver `04_diccionario_y_modelo.md` para el detalle)

* IDs y nombres: 0% nulos en ambas. Trazabilidad OK.
* Plataformas/géneros/fecha/imagen: 0% nulos en el top de ambas.
* **RAWG lista `/games` NO trae `developers`/`publishers`** (claves ausentes en el JSON: hay `genres,platforms,stores,tags,esrb_rating,updated` pero no dev/pub). Para dev/pub hay que llamar a `/games/{id}` (+1 req/juego). En la muestra normalizada salen 100% nulos por este motivo, no porque no existan.
* RAWG no da `critic_count` (nº reseñas Metacritic) ni `game_url` canónica en lista (derivable como `rawg.io/games/<slug>`). `released` es **global por juego**, no por plataforma.
* IGDB expande todo en 1 llamada: `involved_companies{company,developer,publisher}` (0% nulos), `cover.url` (prefijo `https:` necesario), `url` canónica, `checksum`. `first_release_date` es global; el detalle por plataforma/región vive en `/release_dates` (pendiente de muestrear).
* Precio: 100% nulo en ambas. **Sin precio comparable** (ver §5).

## 3. Cobertura por grupo (top popular)

| Grupo | RAWG critic/user/ambas (n=25) | IGDB critic/user/ambas (n=25) |
|---|---|---|
| PC | 25/25/25 | 25/25/25 |
| Consola_Sony | 25/25/25 | 25/25/25 |
| Consola_MS_Nintendo | 25/25/25 | 25/25/25 |
| Móvil | 24/25/24 | 25/25/25 |

Lectura honesta: en el top hay casi todo. Fuera del top los nulos subirán (juegos nicho/móvil indie). El umbral 90% **pasa en el top pero no es generalizable**: hay que re-medirlo en una muestra aleatoria/mid-tail antes de prometerlo.

## 4. Comparabilidad de métricas (no mezclar)

* RAWG: `metacritic` 0–100 (prensa externa) vs `rating` 0–5 (usuarios RAWG, ej. GTA V 92 vs 4.47) + `ratings_count` (7453). Distinta escala Y distinto universo: jamás promediar ni equiparar.
* IGDB: `aggregated_rating` 0–100 (prensa, n pequeña, ej. 88.1 con n=27) vs `rating` 0–100 (miembros, n grande, ej. 89.6 con n=5987). Misma escala pero distinto universo y n. `total_rating` es combinado IGDB: no usarlo como tercera métrica sin justificar.
* Entre fuentes: Metacritic-RAWG vs aggregated-IGDB vs rating-RAWG(0–5) vs rating-IGDB(0–100) vs Steam (otra fuente) son **4–5 universos distintos**. En la app se muestran lado a lado con su n, nunca fusionados.
* Géneros con nombres distintos: `Action` (RAWG 87) vs `Adventure` (IGDB 84), `RPG` vs `Role-playing (RPG)`, `Platformer` vs `Platform`. Necesitan tabla de equivalencias antes de comparar competidores.

## 5. Multiplataforma, duplicados e identidad

* Duplicados por `(source,source_id,platform_names)`: RAWG 48, IGDB 42. No es error: el mismo juego sale en varios grupos porque es multiplataforma (ej. GTA V en PC y Sony con la misma lista completa de plataformas). La clave de identidad debe ser `(source, source_id)`; la disponibilidad va por plataforma aparte.
* RAWG 100/100 registros con >1 plataforma en su lista (PC 100, XOne 76, PS4 76...). IGDB similar (win 94, PS4 73, XOne 60...). El comparador debe filtrar por plataforma, no asumir “un juego = una plataforma”.
* Solape indicativo por título normalizado: 23/87 (ej. `grandtheftautov, bioshock, hollowknight`). **Mismo título ≠ mismo juego**: remasters, ediciones, secuelas y versiones regionales comparten nombre. Estrategia: conservar `source+source_id+slug+checksum`, agrupar candidatos por título+géneros+ventana de fecha y validar manualmente los competidores; nunca fusionar automáticamente por nombre.
* Competidores (≥10 por juego): plausible por solape de géneros/plataformas, pero “directo” exige definir regla (mismos géneros + mismas plataformas + era ±2 años) y validarla. Pendiente.

## 6. Tabla comparativa (resumen decisión)

| Dimensión | IGDB (principal) | RAWG (complemento) |
|---|---|---|
| Conexión medida | token 443ms + games 1129ms, todo 200 | platforms 204ms + games 355ms, todo 200 |
| Cobertura top | critic+user 100/100, dev/pub 0% nulos | critic ~99/100, user 100/100, dev/pub ausentes en lista |
| Granularidad fecha | global + `/release_dates` por plataforma (pendiente) | solo global `released` |
| Identidad | `id+slug+checksum`, ediciones filtrables | `id+slug`, `updated` útil para re-fetch |
| Almacenamiento | permitido y recomendado (histórico viable) | no redistribuir (raw solo local gitignorado) |
| Coste técnico | OAuth + Apicalypse + throttle 4 req/s | `?key=` simple, cuota 20k/mes |
| Precio | no existe | no en Free |

## 7. Criterios de viabilidad (propuestos vs medidos en top)

* Validez campos esenciales ≥90%: **pasa en top** (salvo dev/pub RAWG-lista y precio). Re-medir en mid-tail.
* Cobertura PC/consola/móvil (25/grupo conseguidos, plataformas mapeadas): **pasa**.
* IDs únicos, 0 ausentes: **pasa** (0% nulos id/name).
* Duplicados/ambigüedad: **controlado con modelo** (identidad por IDs, no por título).
* Consistencia entre fuentes: **lado a lado con n**, sin fusionar.
* ≥10 competidores: **pendiente de regla + validación manual**.
* Repetir + almacenar: **pasa en IGDB**, restringido en RAWG.
* Cuota/uso: **pasa** (muestreo 200 filas ≈ 12 peticiones totales).

## 8. Limitaciones a comunicar en la app

1. Muestra top = techo; el catálogo real tendrá más nulos.
2. Métricas de universos distintos, con su n visible.
3. Fechas globales salvo `/release_dates` (IGDB).
4. Dev/pub RAWG exigen detalle por juego (coste cuota).
5. Géneros con vocabularios distintos (tabla equivalencias pendiente).
6. Sin precio comparable trilateral.
7. Identidad por IDs; el matching por título es solo candidato.

## 9. Conclusión y siguientes pasos

Viabilidad **sí, condicional**: IGDB principal + RAWG complemento para el comparador con snapshots. Próximos pasos priorizados:
1. Muestreo mid-tail aleatorio + `/release_dates` IGDB y detalle RAWG de 10 juegos (mide 90% real y coste dev/pub).
2. Tabla equivalencias géneros + regla de competidor directo validada en 3 juegos piloto.
3. Congelar esquema histórico (`04_diccionario_y_modelo.md`) y primer snapshot versionado.
4. Solo entonces, diseño EDA/KPIs y app. Precio fuera del MVP.
