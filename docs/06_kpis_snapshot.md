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
| Cobertura crítica % | juegos con `critic_score` / total, por fuente y grupo | ambas | techo top; re-medir en long-tail |
| Cobertura usuarios % | idem con `user_score` | ambas | idem |
| Mediana crítica / usuarios | mediana por fuente y grupo, en su escala | ambas | escalas no comparables entre fuentes |
| Confianza crítica % | `critic_count ≥ 5` / total con crítica (solo IGDB; RAWG no da n) | IGDB | n<5 = orientativo |
| Multiplataforma % | juegos en >1 plataforma / total | ambas | el filtro por plataforma es obligatorio en la app |
| Competidores por piloto | únicos por `source_id` con regla v1 (`docs/05`) | ambas | umbral ≥10 validado en 3 pilotos; dedup verificado en la salida |
| Deltas ref vs competidores | score_comp − score_ref por métrica, intra-fuente | ambas | no fusiona escalas ni es serie temporal |
| Evolución entre snapshots | deltas de métricas observables entre las 2 últimas fotos | ambas | requiere ≥2 snapshots; con 1 la app muestra estado vacío |

## Log de snapshots

| Snapshot | Base | Filas únicas | Fecha |
|---|---|---|---|
| `snapshot_20261013.csv` | top 200 + mid 160 | 360 − duplicados entre oleadas → 229 | 2026-10-13 |

Regla dedup del snapshot: clave `(source, source_id)`; si un juego aparece en top y mid-tail (o en varios grupos por ser multiplataforma), conserva la fila con más plataformas listadas (más información) y anota `oleada` de procedencia. La misma regla se aplica al cargar en `src/scoring.py` y `src/competidores.py` (`src/datos.py::dedup_fuente_id`), por lo que la muestra top pasa de 200 filas a 110 únicos sin duplicados en la salida.

## Evolución

`python -m src.evolucion` compara los dos últimos snapshots y reporta altas, bajas y
deltas de `critic_score`, `critic_count`, `user_score` y `user_count` por
`(source, source_id)`. Un campo ausente en cualquiera de los dos lados queda como
`delta = null` (no se rellena con datos actuales). `python -m src.export_web` exporta
el resultado a `web/data/evolucion.json`; con menos de 2 snapshots la web muestra un
estado vacío con el comando para capturar la siguiente foto.
