# 06 — KPIs y snapshots (GameScope)

Generado por `src/snapshot.py`. Cada snapshot es **append-only real**: un fichero
`snapshot_AAAAMMDDTHHMMSSZ.csv` (timestamp UTC) por ejecución; dos ejecuciones del
mismo día NO se pisan. Junto al CSV se escribe un `*.meta.json` con los KPIs de la
captura (n por fuente, cobertura, rango de `observed_at`).

Nota histórica: la versión original usaba nombre solo-fecha (`snapshot_AAAAMMDD.csv`)
y sí podía sobrescribir la foto de un mismo día; corregido en la auditoría 2026-10-15.
Los ficheros existentes no se renombran (son observaciones válidas tal cual).

## KPIs v1 (todos medibles hoy)

| KPI | Fórmula | Fuentes | Advertencia |
|---|---|---|---|
| Cobertura crítica % | juegos con `critic_score` / total, por fuente, grupo y **oleada** (top/mid/cola) | ambas | ya medida en las 3 oleadas: top+mid ≈95%/90% vs cola ≈79%/73% |
| Cobertura usuarios % | idem con `user_score` | ambas | ≈100% en todas las oleadas |
| Mediana crítica / usuarios | mediana por fuente y grupo, en su escala | ambas | escalas no comparables entre fuentes |
| Confianza crítica % | `critic_count ≥ 5` / total con crítica (solo IGDB; RAWG no da n) | IGDB | n<5 = orientativo |
| Multiplataforma % | juegos en >1 plataforma / total | ambas | el filtro por plataforma es obligatorio en la app |
| Competidores por piloto | únicos por `source_id` con regla v1 (`docs/05`); con `--estricto` se exige año y ≥2 géneros | ambas | modo base y estricto tienen salida propia; el estricto reduce de 334 a 139 en el piloto actual |
| Deltas ref vs competidores | score_comp − score_ref por métrica, intra-fuente | ambas | no fusiona escalas ni es serie temporal |
| Matching cruzado % | filas con contraparte en la otra fuente / total (`matching.csv`) | derivado | 375/1.131 (33,2%); confianza `exacto` 374, `cercano` 1 |
| Precios PC encontrados | filas en `precios_pc.csv` / títulos PC top evaluados (60) | CheapShark | 38/60 con precio; el resto sin oferta equivalente (no se rellena) |
| Evolución entre snapshots | deltas de métricas observables entre las 2 últimas fotos | ambas | requiere ≥2 snapshots; con 1 la app muestra estado vacío |

## Log de snapshots

| Snapshot | Base (filas de oleadas) | Filas únicas | Fecha (UTC) |
|---|---|---|---|
| `snapshot_20261013.csv` | top 200 + mid 160 → 360 | 229 | 2026-10-13 (nombre solo-fecha, versión previa) |
| `snapshot_20261015T183336Z.csv` | top ampliado (5 grupos × 2 páginas/fuente + extras Switch 2) → 950 | 639 | 2026-10-15 18:33 |
| `snapshot_20261015T185736Z.csv` | top + mid → 1.150 | 831 | 2026-10-15 18:57 |
| `snapshot_20261015T200549Z.csv` | top + mid + cola acumulativa → 1.650 | **1.131** (foto actual de la web) | 2026-10-15 20:05 |

Regla dedup del snapshot: clave `(source, source_id)`; si un juego aparece en varias oleadas o grupos por ser multiplataforma, conserva la fila con más plataformas listadas (más información) y anota `oleada` de procedencia. La misma regla se aplica al cargar en `src/scoring.py` y `src/competidores.py` (`src/datos.py::dedup_fuente_id`): con la base actual, las 1.650 filas de oleadas (950 top + 200 mid + 500 cola) dan **1.131 únicos** en el snapshot.

## Evolución

`python -m src.evolucion` compara los dos últimos snapshots y reporta altas, bajas y
deltas de `critic_score`, `critic_count`, `user_score` y `user_count` por
`(source, source_id)`. Un campo ausente en cualquiera de los dos lados queda como
`delta = null` (no se rellena con datos actuales). `python -m src.export_web` exporta
el resultado a `web/data/evolucion.json`; con menos de 2 snapshots la web muestra un
estado vacío con el comando para capturar la siguiente foto.

Última comparación (831 → 1.131, 2026-10-15): **300 altas** (las de la cola
acumulativa), 0 bajas, 0 cambios de métricas (las filas comunes no se re-consultaron:
las oleadas top/mid conservan su `observed_at` original). La cola es acumulativa a
propósito: cada semana solo puede sumar cobertura nueva, nunca rotar aleatoriamente
y fabricar altas/bajas de muestreo. El Action semanal
(`.github/workflows/weekly_snapshot.yml`) repite este ciclo cada lunes con tests
previos al commit.
