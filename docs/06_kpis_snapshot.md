# 06 — KPIs y snapshots (GameScope)

Generado por `src/snapshot.py`. Cada snapshot es append-only: un fichero fechado por ejecución, nunca se sobrescribe.

## KPIs v1 (todos medibles hoy)

| KPI | Fórmula | Fuentes | Advertencia |
|---|---|---|---|
| Cobertura crítica % | juegos con `critic_score` / total, por fuente y grupo | ambas | techo top; re-medir en long-tail |
| Cobertura usuarios % | idem con `user_score` | ambas | idem |
| Mediana crítica / usuarios | mediana por fuente y grupo, en su escala | ambas | escalas no comparables entre fuentes |
| Confianza crítica % | `critic_count ≥ 5` / total con crítica (solo IGDB; RAWG no da n) | IGDB | n<5 = orientativo |
| Multiplataforma % | juegos en >1 plataforma / total | ambas | el filtro por plataforma es obligatorio en la app |
| Competidores por piloto | únicos por `source_id` con regla v1 (`docs/05`) | ambas | umbral ≥10 validado en 3 pilotos |

## Log de snapshots

| Snapshot | Base | Filas únicas | Fecha |
|---|---|---|---|
| `snapshot_20261013.csv` | top 200 + mid 160 | 360 − duplicados entre oleadas | 2026-10-13 |

Regla dedup del snapshot: clave `(source, source_id)`; si un juego aparece en top y mid-tail, conserva la fila con más plataformas listadas (más información) y anota `oleada` de procedencia.
