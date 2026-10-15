# GameScope

Comparador de videojuegos frente a sus competidores directos en PC, consolas y móvil, con fuentes verificadas, comparación lado a lado y observaciones fechadas.

## 1. Problema y para quién

Quien sigue el mercado del videojuego (aficionados exigentes, pequeños estudios, tiendas) no tiene una forma rápida de responder: “¿cómo se posiciona este juego frente a sus competidores directos?”. Las notas de prensa y de usuarios viven en sitios distintos, con escalas y coberturas distintas, y nadie las pone lado a lado por plataforma.

GameScope responde a eso: eliges un juego y ves sus competidores (mismo género, mismas plataformas, misma era) con crítica y usuarios separados, cada métrica con su escala y su número de votos, más una tabla de diferencias cuantificadas y un resumen de fortalezas/debilidades.

## 2. Datos: origen y obtención

* **IGDB (principal):** `POST api.igdb.com/v4/games|platforms|release_dates` con OAuth2 de Twitch. Permite almacenar snapshots.
* **RAWG (complemento):** `GET api.rawg.io/api/games|platforms?key=` + detalle `/games/{id}` para desarrollador/editor. Plan Free 20.000 req/mes; raw solo local (no redistribuir).
* Precio descartado del MVP: ninguna fuente lo da comparable para PC+consola+móvil.
* Todo el acceso está en `src/` y usa `.env` (`RAWG_API_KEY`, `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`). Detalle en `docs/01_validacion_fuentes.md` y `docs/02_decision_fuentes.md`.

## 3. Preprocesamiento y EDA: decisiones y hallazgos

* Normalización a esquema común con `observed_at` + `source` (`src/muestreo.py` → `data/processed/muestra_normalizada.csv`, 200 filas top; `src/muestreo_midtail.py` → 160 mid-tail + `release_dates_10.csv`).
* Decisiones: identidad por `(source, source_id)`, nunca por título; **deduplicación siempre por `(source, source_id)`** conservando la fila con más plataformas (`src/datos.py`); métricas lado a lado sin fusionar; géneros con tabla de equivalencias (`docs/05`).
* Hallazgos (`notebooks/02_eda.ipynb`, n=360): medianas al techo por sesgo top (85/100 y 4.11/5); Pearson crítica-usuarios ≈0.69 con n dispares (prensa n≈11 vs usuarios n≈miles); casi todo multiplataforma (filtro por plataforma obligatorio); mediana de año 2014; pocos estudios concentran el top. RAWG-lista no trae dev/editor (se recuperan al 10/10 vía detalle, +1 req/juego).

## 4. Ciencia de datos: enfoque, métricas y limitaciones

* Enfoque: scoring heurístico v1 y configurable (`src/scoring.py`, pesos y umbrales ajustables): género + plataforma (requisitos duros) + era + estudio si existe, normalizado por máximo aplicable y con explicación por pareja (`docs/07_metodologia.md`, caso real `docs/08_caso_prueba.md`). Subgénero, negocio y audiencia excluidos por falta de fuente.
* Métricas: cobertura crítica/usuarios %, medianas por escala, confianza crítica (n≥5), multiplataforma % (`docs/06_kpis_snapshot.md`), deltas intra-fuente ref vs competidores (absolutos y relativos) en la tabla comparativa de la web.
* Histórico: snapshots append-only con timestamp UTC (`data/snapshots/snapshot_AAAAMMDDTHHMMSSZ.csv` + `.meta.json` de trazabilidad). Evolución = deltas de métricas observables entre los 2 últimos snapshots (`src/evolucion.py`); con menos de 2 snapshots la app muestra un estado vacío honesto (nunca reconstruye tendencias).
* Limitaciones: muestra top = techo de cobertura; `Action↔Adventure` es aproximada; era ±4 arbitraria; mismo título ≠ mismo juego; sin precio; `/release_dates` no universal (7/10); puntuaciones y votos no son ventas.

## 5. Aplicación web (estado: funcional)

Web estática (HTML + CSS + JS sin build) en `web/`, generada desde el snapshot versionado:

* Buscador de juego de referencia por fuente (IGDB/RAWG), umbral de tier y nº de resultados.
* Filtros de plataforma y género (opciones derivadas de los datos reales) que restringen competidores.
* **Tabla comparativa** ref vs competidores con Δ crítica, Δ usuarios, Δ años (solo intra-fuente y misma escala).
* **Resumen de diferencias** (insights): mediana del grupo, cuántos superan a la referencia, rango del top, caveats explícitos (sin ventas, sin fusionar escalas).
* Scoring v1 replicado en JS con los mismos pesos/umbrales (`web/js/scoring.js`) y explicación por competidor.
* Sección **Evolución temporal**: deltas reales entre snapshots si hay ≥2; si no, estado vacío honesto.

Para ejecutarla en local y desplegarla: `web/README.md`. La web no llama a las APIs en tiempo real: no lleva claves ni consume cuota.

## 6. Instalación y ejecución (Windows, PowerShell, desde la raíz)

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # solo la primera vez; luego rellena tus 3 claves
python -m src.check_connections  # conectividad IGDB+RAWG
python -m src.muestreo           # muestra top 200 (consume cuota: ~12 peticiones)
python -m src.muestreo_midtail   # mid-tail + release_dates + detalle RAWG
python -m src.snapshot           # snapshot versionado (append-only, con hora)
python -m src.competidores       # regla v1 en 3 pilotos (sin API, deduplicado)
python -m src.scoring --slug hollow-knight --source igdb  # scoring v1 + explicación
python -m src.evolucion          # deltas entre los 2 últimos snapshots (si existen)
python -m src.export_web         # regenera web/data/*.json desde el último snapshot
python -m unittest discover tests  # 40 tests (sin API)
jupyter notebook notebooks/02_eda.ipynb

# app web en local (desde web/)
python -m http.server 8000       # abrir http://localhost:8000
```

`.env` está gitignorado y ninguna salida imprime claves.

## 7. Estructura del repositorio

```
├── README.md
├── requirements.txt
├── .env.example
├── src/                  # config, datos, check_connections, muestreo, muestreo_midtail,
│                         # competidores, scoring, snapshot, evolucion, export_web
├── tests/                # 40 tests: scoring, datos, snapshot, evolución, export (sin API)
├── notebooks/            # 01 plan de auditoría, 02 EDA ejecutado
├── web/                  # app estática (index.html, js/, styles/, data/ generada)
├── data/
│   ├── raw/              # respuestas originales (gitignorado, solo local)
│   ├── processed/        # muestras normalizadas + release_dates (versionado)
│   └── snapshots/        # fotos deduplicadas y fechadas, append-only (+ .meta.json)
└── docs/                 # 01 validación, 02 decisión, 03 auditoría, 04 diccionario+modelo,
                          # 05 equivalencias, 06 KPIs, 07 metodología, 08 caso de prueba
```

## 8. Qué mejoraría con más tiempo

1. Muestra long-tail aleatoria para medir el suelo real de cobertura.
2. Endurecer la regla (≥2 géneros o peso por rareza, penalizar mismo estudio).
3. Matching cruzado RAWG↔IGDB semi-automático con validación manual.
4. Repetir snapshots al calendario (semanal ratings, mensual estáticos): con 2+ fotos la sección de evolución de la web pasa a mostrar deltas reales.
5. Módulo de precio solo-PC (CheapShark, USD) aislado del comparador principal.
