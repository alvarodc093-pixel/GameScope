# 02 — Comparación y decisión de fuentes (GameScope Fase 1)

Fecha original: 2026-10-13 (criterios y decisión preliminar).
**Medición en vivo: 2026-10-16T08:54 UTC** (`python -m src.auditoria_fuentes`).
Base: `docs/01_validacion_fuentes.md`. Cifras de este documento = una sola observación con credenciales reales; **no es un histórico**. Cada fila/artefacto lleva `observed_at` + `source`. Artefactos: `data/processed/plataformas_mapeo.csv`, `data/processed/auditoria_cobertura.json`, raw en `data/raw/auditoria_*` (gitignorado).

> Nota posterior (Fase 2): decisión confirmada también en `docs/03_auditoria_exploratoria.md` y `docs/05_equivalencias_competidores.md`.

## 1. Comparativa resumida (documental)

| Dimensión | RAWG | IGDB (Twitch) | CheapShark / Steam (solo precio PC) |
|---|---|---|---|
| Acceso MVP | Simple: `GET + ?key=`. Ideal bootcamp. | Medio: OAuth Twitch + POST Apicalypse + paginación + CORS solo backend. | Simple (sin key), pero solo PC. |
| Cobertura PC/consola/móvil | **Medida 2026-10-16:** catálogo 51 plataformas → PC 7 / Consola 41 / Móvil 2 / Otro 1 (`Web`). | **Medida:** 220 plataformas + familias → PC 41 / Consola 85 / Móvil 3 / Otro 91 (retro sin `platform_family`; el top PC/consola/móvil sí tiene familia: win=6, ps/xbox/switch, ios=39, android=34). | Solo PC digital. No cubre consola/móvil. |
| Críticos vs usuarios | `metacritic` 0–100 vs `rating` 0–5 (interno). Universos distintos. | `aggregated_rating(+count)` 0–100 vs `rating(+count)` 0–100, bien separados. | `metacriticScore` + `steamRating*`. No mezclar. |
| Dev / Publisher | Ausentes en `/games` lista (hay que pedir detalle). | `involved_companies{developer,publisher}` en la misma llamada. | No aplica. |
| Fecha lanzamiento | `released` global. | `first_release_date` + `/release_dates` por plataforma/región. | `releaseDate` solo PC. |
| Precio / moneda | No en Free. | No existe. | Sí, USD PC-only. |
| Rate / cuota | 20k req/mes Free. | 4 req/s, sin tope mensual. | Límites no oficiales. |
| Almacenar snapshots | “No redistribution”: raw solo local gitignorado. | Permitido y recomendado. | Con atribución. |
| Deploy bootcamp | Backlink + no clonar. | Secret solo en backend. | Enlaces de deals. |
| Riesgo principal | Legal + nulos `metacritic` fuera del top. | OAuth/CORS/throttle. | Alcance PC-USD. |

## 2. Criterios de aceptación — propuestos vs medidos (2026-10-16)

Muestra: top por familia, 1 página por grupo (RAWG 3×40=120; IGDB 3×50=150), `ordering=-added` / `sort total_rating_count desc`. **Es el techo de cobertura, no el catálogo medio.**

| Criterio | Umbral | RAWG medido | IGDB medido | Resultado |
|---|---|---|---|---|
| **C1 Cobertura multiplataforma** | ≥95% con plataforma válida; ≥30/juego por grupo PC/consola/móvil; familias sin ambigüedad | 120/120 con `platforms`; grupos 40/40/40; mapa 51/51 clasificadas (1 `Web`=Otro) | 150/150 con `platforms`; grupos 50/50/50; familias IGDB resuelven el top (PC/consola/móvil); 91 plataformas retro sin familia → `Otro` (fuera del MVP) | **Pasa ambas** |
| **C2 Calidad base** | IDs únicos sin nulos; % nulos por campo; 0 dups tras identidad | `id/name/slug` 0% nulos; dups brutos 40 (mismo juego en 2 grupos; identidad=`source+source_id` → 80 únicos/120) | `id/name/slug` 0% nulos; dups brutos 45 (150→100 únicos) | **Pasa** (dups esperados multiplataforma; dedup en `src/datos.py`) |
| **C3 Completitud fechas** | ≥90% fecha válida | `released` 0% nulos (100%) | `first_release_date` 0% nulos (100%) | **Pasa ambas** en top |
| **C4 Comparabilidad valoraciones** | ≥40% con alguna; ≥20% con ambas | críticos `metacritic` **97,5%**; usuarios `rating` **100%**; ambas **97,5%** (PC 100 / consola 97,5 / móvil 95) | críticos `aggregated_rating` **99,3%**; usuarios `rating` **100%**; ambas **99,3%** (PC 100 / consola 100 / móvil 98) | **Pasa ambas** (IGDB algo mejor) |
| **C5 Estabilidad acceso** | 0×401; 429 con backoff; <5% 5xx | TODO 200 en la corrida de auditoría | Token + games 200; throttle 0,4 s OK | **Pasa** |
| **C6 Compatibilidad deploy** | Cachear snapshots sin exponer secretos | Restringido a raw local | Permitido | **Solo IGDB apta como principal** |
| **C7 Precio** | Comparable trilateral o aislado | No | No | **Fuera del MVP** (igual que en Fase 1) |

Detalle nulos ( % de la muestra top, `auditoria_cobertura.json` ):

| Campo | RAWG | IGDB |
|---|---|---|
| críticos (`metacritic` / `aggregated_rating`) | 2,5 | 0,7 |
| usuarios (`rating`) | 0,0 | 0,0 |
| fecha | 0,0 | 0,0 |
| plataformas / géneros | 0,0 | 0,0 |
| imagen / cover | 0,0 | 0,0 |

## 3. Decisión final (revisada con cifras de 2026-10-16)

* **Se mantiene fuente principal: IGDB.** No se invierte.
  Por qué, con números:
  1. Cobertura de críticos en top **99,3% vs 97,5%** (y móvil 98% vs 95%).
  2. `aggregated_rating` y `rating` en la **misma escala 0–100** con `*_count` explícitos; RAWG mezcla Metacritic 0–100 con `rating` 0–5.
  3. Dev/publisher y cover en la **misma consulta** (0% nulos en la muestra IGDB); en RAWG hay +1 req/juego.
  4. **C6 decisivo:** IGDB permite snapshots versionados; RAWG prohíbe redistribution del raw, así que no puede ser la base del histórico ni del deploy.
* **Fuente secundaria: RAWG** — validación cruzada de `metacritic` y contraste de cobertura; raw solo local gitignorado; atribución con hyperlink.
* **Precio: sigue descartado del MVP** (C7).

Campos utilizables (confirmados en la muestra de 2026-10-16):

* IGDB: `id`, `name`, `slug`, `platforms`, `genres`, `first_release_date` (+ `/release_dates` por plataforma), `involved_companies`, `aggregated_rating(+count)`, `rating(+count)`, `cover.url`, más `observed_at` + `source`.
* RAWG: `id/slug`, `name`, `platforms`, `genres`, `released`, `metacritic`, `rating`, `ratings_count`, `background_image` (dev/pub solo vía detalle), más `observed_at` + `source`.

Campos a descartar en MVP: precio/moneda, stores Free, promedios que mezclen universos, `similar_games` Free, imágenes sin atribución.

## 4. Limitaciones conocidas (para comunicar en la app)

1. Cobertura medida = **top**; el catálogo real tendrá más nulos (re-medir en mid/long-tail con el mismo script).
2. Universos de métricas distintos; mostrar siempre n y fuente, nunca fusionar.
3. Fechas: RAWG global vs IGDB por región/plataforma.
4. Ediciones: filtrar `version_parent = null` en IGDB.
5. Atribución obligatoria; RAWG exige hyperlink y no redistribuir raw.
6. El mapa de familias IGDB deja 91 plataformas retro en `Otro` (sin `platform_family`); el MVP no las usa.

## 5. Riesgos restantes (actualizados)

* ~~Sin credenciales~~ — **resuelto**: RAWG + IGDB OK el 2026-10-16.
* RAWG puede denegar versionar raw en repo del bootcamp aunque sea privado → raw siempre gitignorado.
* Token IGDB caduca (~60 días); CORS si se llama desde frontend → backend/Streamlit server.
* `429` si se olvida throttle (<4 req/s).
* Si se muestrea long-tail, C4 puede caer: recortar a “comparador top” con disclaimer, no forzar métricas.

## 6. Próximo paso

1. ~~Credenciales + auditoría C1–C7~~ — **hecho 2026-10-16** (`src/auditoria_fuentes.py`).
2. Mantener IGDB-principal; RAWG solo enriquecimiento/cruzado.
3. EDA/KPIs y app Streamlit con snapshots semanales (`src/snapshot.py`), sin exponer secretos.

