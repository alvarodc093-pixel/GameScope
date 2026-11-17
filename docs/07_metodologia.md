# 07 — Metodología de análisis competitivo (scoring v2, heurístico)

Código: `src/scoring.py` (`python -m src.scoring --slug <slug> --source <igdb|rawg> [--estricto]`).
Carga el último snapshot de `data/snapshots/`, deduplicado por `(source, source_id)`.
Tests: `python -m unittest discover tests` (sin llamadas a las APIs).
Caso real: `docs/08_caso_prueba.md` (snapshot del 2026-11-16, 1.130 juegos).

## 1. Dimensiones evaluadas y veredicto de fuente

| Dimensión | Fuente válida | Uso en el scoring |
|---|---|---|
| Género (mapeado `docs/05`) | ambas | sí, requisito duro |
| Plataforma compartida | ambas | sí, requisito duro |
| Periodo lanzamiento | ambas | sí, componente era |
| Estudio (dev) | solo IGDB | sí, solo si ambas partes lo tienen |
| Subgénero/mecánicas | ninguna normalizada | excluido |
| Modelo de negocio | ninguna | excluido |
| Audiencia | no justificable | excluido |
| Popularidad | intra-fuente (`added`, `total_rating`) | contexto, no scoring |

## 2. Scoring v2 (pesos en `PESOS`, umbrales en `UMBRALES`)

* `genero` (3.0): Jaccard ponderado por rareza. Cada género canónico pesa
  `log(N / juegos de la fuente que lo tienen)`, calculado sobre el snapshot cargado.
  Un género presente en todos los juegos pesa 0. Descarte si no hay género común;
  `insuficiente` si falta el dato.
* `plataforma` (2.0): 1.0 si ≥2 en común, 0.5 si 1, descarte si 0.
* `era` (1.0): 1.0 si Δ≤2 años, 0.5 si ≤4, 0.0 si mayor o si falta la fecha.
* `estudio` (1.0): 1.0 mismo estudio, 0.0 distinto; no aplica si falta en alguna parte (RAWG).
* Nota = Σ(w·v)/Σw sobre componentes aplicables, redondeada a 3 decimales.
  Tiers: ≥0.75 directo, ≥0.60 secundario, ≥0.40 relacionado, resto descartado.
* Empates: más votos de usuarios primero, luego nombre.

### Por qué v2

En v1 el género valía 0.6 con un solo género común y 1.0 con dos, sin mirar cuáles.
Con género y plataforma obligatorios, la nota mínima de una pareja admitida era
2.8/6 = 0.467, por encima del umbral de secundario (0.45): casi cualquier juego
que compartiera Adventure y una plataforma era competidor. Medido sobre 60
referencias al azar, la mediana era el 56 % del catálogo IGDB y el 69 % del RAWG.
Con v2 baja al 3 % y al 12 % (RAWG tiene pocos géneros, muy amplios).

Límite: dos juegos con exactamente los mismos géneros dan Jaccard 1 aunque esos
géneros sean comunes (GTA V en RAWG solo tiene `Action`; ver `docs/08`).

### Modo estricto (admisión, no pesos)

Mismos pesos y umbrales; cambia quién entra en la lista. Igual en
`src/scoring.py --estricto` y en `web/js/scoring.js` (interruptor «Regla»):

* Año presente en ambas partes; si falta en alguna, `insuficiente`.
* ≥2 géneros en común; con uno solo, `descartado` con ese motivo.
* El estudio sigue siendo opcional: RAWG no publica desarrolladores en el listado
  y exigirlo dejaría a RAWG sin parejas.

## 3. KPIs competitivos (extienden `docs/06`)

Directos+secundarios por juego, similitud media del top-10, diferencia de crítica/usuarios frente a la mediana del grupo comparable (misma fuente y escala), y bandera de confianza (n de prensa <5 = orientativo). La tabla comparativa de la web calcula deltas absolutos y relativos intra-fuente. Evolución temporal: `src/evolucion.py` compara los dos últimos snapshots (hoy ≥2 fotos con deltas reales; el estado vacío honesto solo aplica a repos con 1 snapshot).

## 4. Validación

Tests de `tests/test_scoring.py`: sin plataforma común no hay competidor, los ausentes
no inflan la nota, el estudio ausente no penaliza, los pesos son configurables, el
resultado es determinista, un género universal no aporta y compartir un género raro
puntúa más que compartir uno común.

`tests/test_paridad_js.py` ejecuta `web/js/scoring.js` con Node y compara nota y
tier con la versión Python en todos los pares de 12 juegos sintéticos (ambos modos) y
en 8 referencias del último snapshot contra todo su catálogo. Se salta si no hay Node.
