# 04 — Diccionario de datos y modelo histórico (Fase 2)

Base medida: snapshot 2026-10-15 (1.131 filas únicas = top 950 + mid 200 + cola 500 con dedup). % nulos = techo del top, no del catálogo.

## 1. Diccionario (esquema normalizado `muestra_normalizada.csv`)

| Campo | Tipo | Origen | Significado | Calidad top |
|---|---|---|---|---|
| source | texto | generado | `rawg` o `igdb` | 0% nulo |
| source_id | entero | `rawg.id` / `games.id` | ID original, clave de trazabilidad | 0% nulo |
| slug | texto | `slug` | legible, útil para URLs RAWG | 0% nulo |
| name | texto | `name` | título comercial | 0% nulo |
| grupo | texto | generado | grupo de muestreo con sufijo de oleada: `PC`, `Consola_Sony`, `Consola_MS`, `Nintendo`, `Nintendo_Switch2`, `Movil`; en mid/cola con `_mid`/`_long` | 0% nulo |
| platform_names | texto `\|` | `platforms[].platform.name` / `platforms[].name` | lista completa del juego (no solo el grupo) | 0% nulo |
| genre_names | texto `\|` | `genres[].name` | vocabulario distinto por fuente (ver §2) | 0% nulo |
| release_date | fecha ISO | `released` / `first_release_date`→fecha | lanzamiento global; por plataforma solo en `/release_dates` IGDB | 0% nulo en top |
| developer_names | texto `\|` | RAWG detalle `/games/{id}` / `involved_companies[developer]` | estudios | RAWG-lista 100% nulo (ausente en lista); IGDB 0% nulo |
| publisher_names | texto `\|` | RAWG detalle / `involved_companies[publisher]` | editoras | igual que developer |
| critic_score | número | `metacritic` 0–100 / `aggregated_rating` 0–100 | prensa externa, universos distintos | ~99–100% disponible en top |
| critic_count | entero | — / `aggregated_rating_count` | nº reseñas prensa (RAWG no lo da) | RAWG siempre nulo; IGDB disponible |
| user_score | número | `rating` 0–5 (RAWG) / 0–100 (IGDB) | usuarios de cada plataforma, no equiparables | 100% en top |
| user_count | entero | `ratings_count` / `rating_count` | nº votos usuarios | 100% en top |
| popularity_extra | texto | `added;reviews;playtime` / `total_rating;total_count` | contexto, no comparable entre fuentes | informativo |
| game_url | texto | — / `url` | página canónica (RAWG derivable `rawg.io/games/<slug>`) | RAWG nulo en lista; IGDB 0% nulo |
| image_url | texto | `background_image` / `cover.url` (añadir `https:`) | carátula/fondo (atribución obligatoria) | 0% nulo en top |
| price | — | — | sin fuente comparable en el esquema de muestra; el precio PC vive en `precios_pc.csv` (§4), no en esta tabla | 100% nulo |
| observed_at | timestamp UTC | generado | fecha-hora de consulta, corazón del histórico | siempre presente |

## 2. Equivalencias pendientes (no asumir)

* Géneros: `Action↔Adventure`, `RPG↔Role-playing (RPG)`, `Platformer↔Platform`, resto por tabla manual.
* Plataformas: `PC↔PC (Microsoft Windows)`, `PS5↔PlayStation 5`, `PS4↔PlayStation 4`, `Xbox One↔Xbox One`, `Series S/X↔Xbox Series X|S`, `Switch↔Nintendo Switch`, `iOS↔iOS`, `Android↔Android`.
* Métricas: mostrar `valor (n=…)` por fuente, nunca fusionar.

## 3. Modelo histórico propio (append-only, sin sobrescribir)

Tablas (nombres propuestos):

* `juego(game_id PK, nombre_canonico, notas_dedup)` — identidad editorial nuestra.
* `juego_fuente(source, source_id, slug, checksum, updated, game_id FK)` — conserva IDs originales; PK `(source, source_id)`.
* `plataforma(platform_id PK, source, source_platform_id, slug, nombre, familia, grupo)` — PC/consola/móvil.
* `observacion(id PK, juego_fuente FK, plataforma FK nullable, observed_at UTC, critic_score, critic_count, user_score, user_count, popularity_extra, source)` — **una fila por consulta, nunca UPDATE**.

Estático (cambia poco, versionado por `checksum`/`updated`): nombre, slug, géneros, dev/pub, fecha lanzamiento.
Observado (serie temporal válida solo intra-fuente+métrica): critic/user y conteos, popularidad; precio PC (USD) con `observed_at` propio en su tabla.
No histórico fiable: fechas pasadas (inmutables), métricas cruzadas entre fuentes, precio convertido a otra moneda (no se hace).

Ejemplo: GTA V tendría 1 `juego`, 2 `juego_fuente` (3498 + 1020) y N `observacion` semanales por fuente. Nada se inventa: sin `observed_at` real no hay fila.

## 4. Artefactos derivados (no entran en el snapshot)

* `data/processed/matching.csv` — identidad del mismo juego entre fuentes (`src/matching.py`): claves `(source, source_id)` ↔ contraparte, `confianza` (`exacto`/`cercano`) y `metodo`. Actualmente 375/1.131 filas con contraparte. **Derivado**: cambiarlo no altera observaciones; la web solo usa el enlace.
* `data/processed/precios_pc.csv` — precio PC (`src/precios.py`, CheapShark, USD): `precio_min_usd`, `moneda=USD`, `en_steam`, `observed_at` propio (independiente del `observed_at` de la muestra). Actualmente 38/60 títulos PC top; sin oferta equivalente → sin fila (nunca un precio de otra edición).
