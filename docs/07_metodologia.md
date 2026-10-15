# 07 — Metodología de análisis competitivo (Fase 4, v1 heurística)

Código: `src/scoring.py` (`python -m src.scoring --slug <slug> --source <igdb|rawg> [--estricto]`).
Carga el **último** snapshot de `data/snapshots/` (antes hardcodeado a una fecha; corregido
en la auditoría 2026-10-15) ya deduplicado por `(source, source_id)`.
Tests: `python -m unittest discover tests` (61: scoring + modo estricto, matching, precios, datos, snapshot, evolución, export; sin API).
Base usada en el caso real: último snapshot (1.131 únicas, 2026-10-15).

## 1. Dimensiones evaluadas y veredicto de fuente

| Dimensión | Fuente válida | Uso en v1 |
|---|---|---|
| Género (mapeado `docs/05`) | ambas | sí, requisito duro |
| Plataforma compartida | ambas | sí, requisito duro |
| Periodo lanzamiento | ambas | sí, componente era |
| Estudio (dev) | solo IGDB | sí, solo si ambas partes lo tienen |
| Subgénero/mecánicas | ninguna normalizada | excluido |
| Modelo de negocio | ninguna | excluido |
| Audiencia | no justificable | excluido |
| Popularidad | intra-fuente (`added`, `total_rating`) | contexto, no scoring |

## 2. Scoring v1 (pesos configurables en `PESOS`, umbrales en `UMBRALES`)

* `genero` (3.0): 1.0 si ≥2 géneros equivalentes, 0.6 si 1, descarte si 0 o ausente (`insuficiente` si falta el dato).
* `plataforma` (2.0): 1.0 si ≥2 en común, 0.5 si 1, descarte si 0.
* `era` (1.0): 1.0 si Δ≤2 años, 0.5 si ≤4, 0.0 si mayor o fecha ausente (ausente = 0, nunca suma).
* `estudio` (1.0): 1.0 mismo estudio, 0.0 distinto; no aplica si falta en alguna parte (no penaliza a RAWG).
* Nota = Σ(w·v)/Σw sobre componentes aplicables. Tiers: ≥0.75 directo, ≥0.45 secundario, ≥0.25 relacionado, resto descartado.

### Modo estricto (admisión, no pesos)

Mismos pesos y umbrales; cambia quién **entra** a la lista de competidores, y es
sincrónico entre `src/scoring.py --estricto` y `web/js/scoring.js` (interruptor “Regla”):

* Año presente en ambas partes → si falta en alguna, `insuficiente` (no se imputa).
* ≥2 géneros equivalentes en común → 1 (`descartado` con ese motivo); 1 género ya no basta.
* Estudio sigue siendo opcional: RAWG no publica desarrolladores en listado y exigirlo
  borraría todas las parejas RAWG (decisión documentada, no accidental).
* Motivos visibles en la web (`v.motivo`) y en la explicación CLI. Efecto medido en el
  piloto actual: 334 → 139 competidores; la web declara el modo en el encabezado de resultados.

## 3. KPIs competitivos v1 (extienden `docs/06`)

Directos+secundarios por juego, similitud media del top-10, diferencia de crítica/usuarios frente a la mediana del grupo comparable (misma fuente y escala), y bandera de confianza (n de prensa <5 = orientativo). La tabla comparativa de la web calcula deltas absolutos y relativos intra-fuente. Evolución temporal: `src/evolucion.py` compara los dos últimos snapshots (hoy ≥2 fotos con deltas reales; el estado vacío honesto solo aplica a repos con 1 snapshot).

## 4. Validación

Tests: género-solo no basta sin plataforma; ausentes no inflan; estudio N/A no penaliza; pesos/umbrales configurables; determinismo; **paridad modo estricto Python↔JS** (tier y nota en 12 casos). Caso real en `docs/08_caso_prueba.md`. Límite conocido (antes recomendación, ahora implementado): con el cajón `Action` solo el tier directo es generoso (ej. GTA V–Transistor 0.800); el **modo estricto** cierra eso exigiendo ≥2 géneros, y el usuario elige el modo en la web o por `--estricto`.
