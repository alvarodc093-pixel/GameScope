# GameScope

Comparador de videojuegos frente a sus competidores directos en PC, consolas y móvil, con fuentes verificadas, comparación lado a lado y observaciones fechadas.

## 1. Problema y para quién

Quien sigue el mercado del videojuego (aficionados exigentes, pequeños estudios, tiendas) no tiene una forma rápida de responder: “¿cómo se posiciona este juego frente a sus competidores directos?”. Las notas de prensa y de usuarios viven en sitios distintos, con escalas y coberturas distintas, y nadie las pone lado a lado por plataforma.

GameScope responde a eso: eliges un juego y ves sus competidores (mismo género, mismas plataformas, misma era) con crítica y usuarios separados, cada métrica con su escala y su número de votos, más una tabla de diferencias cuantificadas y un resumen de fortalezas/debilidades.

## 2. Datos: origen y obtención

* **IGDB (principal):** `POST api.igdb.com/v4/games|platforms|release_dates` con OAuth2 de Twitch. Permite almacenar snapshots.
* **RAWG (complemento):** `GET api.rawg.io/api/games|platforms?key=` + detalle `/games/{id}` para desarrollador/editor. Plan Free 20.000 req/mes; raw solo local (no redistribuir).
* **CheapShark (precio PC):** `GET www.cheapshark.com/api/1.0/games` sin clave, USD y con su propio `observed_at` (`src/precios.py`, 60 títulos PC top, umbral de nombre ≥0.90: si no hay producto equivalente, el juego queda sin precio en vez de arriesgar otro). Consolas siguen sin fuente de precio: no se estima.
* IDs de plataformas verificados en vivo (2026-10-15): RAWG tiene Nintendo Switch=`7` pero **no cataloga Switch 2** (catálogo completo=51 plataformas); IGDB sí, **Switch 2=`508`** (Switch=`130`). Nintendo se muestrea en grupo propio.
* Todo el acceso está en `src/` y usa `.env` (`RAWG_API_KEY`, `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`). Detalle en `docs/01_validacion_fuentes.md` y `docs/02_decision_fuentes.md`.

## 3. Preprocesamiento y EDA: decisiones y hallazgos

* Normalización a esquema común con `observed_at` + `source`. Tres oleadas complementarias: **top** (`src/muestreo.py`: 5 grupos —PC, Sony, MS, Nintendo propio, móvil— × 2 páginas × 40 RAWG + 2 × 50 IGDB + extras Switch 2 → 950 filas), **mid** (`src/muestreo_midtail.py` → 200 filas + `release_dates_10.csv` + detalle RAWG) y **cola** (`src/muestreo_longtail.py`: muestra aleatoria profunda, **acumulativa con tope 500** para no inflar altas/bajas de la evolución con ruido de muestreo).
* Decisiones: identidad por `(source, source_id)`, nunca por título; **deduplicación siempre por `(source, source_id)`** conservando la fila con más plataformas (`src/datos.py`); métricas lado a lado sin fusionar; géneros con tabla de equivalencias (`docs/05`).
* Hallazgos (`notebooks/02_eda.ipynb`, re-ejecutado con la base 2026-10-15, n=1.150 top+mid): medianas al techo por sesgo top (84–85/100; 4.12/5); Pearson crítica-usuarios 0.64 (RAWG) / 0.68 (IGDB) con n dispares (prensa IGDB mediana n=12, usuarios hasta miles de votos); casi todo multiplataforma (99% RAWG, 98% IGDB → filtro por plataforma obligatorio); medianas de año 2014/2015; pocos estudios concentran el top (Ubisoft Montreal 30, Capcom 21, Telltale 20). Cobertura de crítica top+mid ≈95% (RAWG) / 90% (IGDB) vs cola ≈79% / 73% (usuarios ≈100% en ambas, RAWG e IGDB lo publican siempre). RAWG-lista no trae dev/editor (500/500 nulos en dev en la muestra: se recuperan vía detalle, +1 req/juego).

## 4. Ciencia de datos: enfoque, métricas y limitaciones

* Enfoque: scoring heurístico v1 y configurable (`src/scoring.py`, pesos y umbrales ajustables): género + plataforma (requisitos duros) + era + estudio si existe, normalizado por máximo aplicable y con explicación por pareja (`docs/07_metodologia.md`, caso real `docs/08_caso_prueba.md`). Subgénero, negocio y audiencia excluidos por falta de fuente. **Modo estricto** (`--estricto` en Python, interruptor en la web, sincronizado con `web/js/scoring.js`): admisión más dura con los mismos pesos — exige año en ambas partes y ≥2 géneros en común; el estudio sigue siendo opcional porque RAWG no publica desarrolladores en listado (exigirlo borraría todas las parejas RAWG).
* Matching cruzado (`src/matching.py`): identidad del mismo juego entre RAWG e IGDB por nombre normalizado + guardia de años (|Δ|≤2 evita unir remakes; similitud ≥0.95 para “cercano”). Es **derivado, no observado**: no entra en el snapshot; la web solo muestra el enlace “También en la otra fuente” y cada métrica sigue en su propia escala.
* Métricas: cobertura crítica/usuarios %, medianas por escala, confianza crítica (n≥5), multiplataforma % (`docs/06_kpis_snapshot.md`), deltas intra-fuente ref vs competidores (absolutos y relativos) en la tabla comparativa de la web.
* Histórico: snapshots append-only con timestamp UTC (`data/snapshots/snapshot_AAAAMMDDTHHMMSSZ.csv` + `.meta.json` de trazabilidad). Evolución = deltas de métricas observables entre los 2 últimos snapshots (`src/evolucion.py`); con menos de 2 snapshots la app muestra un estado vacío honesto (nunca reconstruye tendencias). La cola es acumulativa justamente para que altas/bajas reflejen cobertura nueva y no rotación de la muestra.
* Automatización: `.github/workflows/weekly_snapshot.yml` captura un snapshot cada lunes (muestreo → snapshot → matching → precios → export → tests) y solo commita si todo pasa; requiere los 3 secrets de la API en el repositorio.
* Limitaciones: muestra top = techo de cobertura; `Action↔Adventure` es aproximada; era ±4 arbitraria; mismo título ≠ mismo juego; precio PC en USD sin conversión y sin consolas; `/release_dates` no universal (7/10); puntuaciones y votos no son ventas.

## 5. Aplicación web (estado: funcional)

Web estática (HTML + CSS + JS sin build) en `web/`, generada desde el snapshot versionado. **Funciona abriendo `index.html` con doble clic** (los datos viajan como script `data/datos.js`, sin fetch) y también con cualquier servidor estático:

* **Buscador en un solo paso:** escribes, eliges de la lista desplegable y la comparación aparece al instante (insensible a mayúsculas y acentos; si el juego está en la otra fuente, ofrece cambiarla con un clic). La página carga con un ejemplo real ya comparado (Hollow Knight vs sus competidores) y botones de ejemplos.
* Fuente (IGDB/RAWG), umbral de tier y nº de resultados.
* **Modo estricto** (interruptor “Regla”): menos competidores pero de admisión dura (año obligatorio + ≥2 géneros en común); el encabezado y la metodología lo declaran.
* Filtros de plataforma y género (opciones derivadas de los datos reales) que restringen competidores.
* **Tabla comparativa** ref vs competidores con Δ crítica, Δ usuarios, Δ años (solo intra-fuente y misma escala).
* **Resumen de diferencias** (insights): mediana del grupo, cuántos superan a la referencia, rango del top, caveats explícitos (sin ventas, sin fusionar escalas).
* **“También en la otra fuente”**: enlace con confianza declarada (exacto/cercano) que cambia de fuente y selecciona el mismo juego; las métricas nunca se muestran cruzadas.
* **Precio PC** en la tarjeta de referencia (USD, CheapShark, con su fecha de observación y “sin convertir”) cuando existe para ese título.
* Scoring v1 replicado en JS con los mismos pesos/umbrales y el mismo modo estricto (`web/js/scoring.js`) y explicación por competidor.
* Sección **Evolución temporal**: deltas reales entre snapshots si hay ≥2; si no, estado vacío honesto.

Para ejecutarla en local y desplegarla: `web/README.md`. La web no llama a las APIs en tiempo real: no lleva claves ni consume cuota.

## 6. Instalación y ejecución (Windows, PowerShell, desde la raíz)

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # solo la primera vez; luego rellena tus 3 claves
python -m src.check_connections  # conectividad IGDB+RAWG
python -m src.muestreo           # top: 5 grupos x 2 páginas por fuente (~25 peticiones)
python -m src.muestreo_midtail   # mid-tail + release_dates + detalle RAWG
python -m src.muestreo_longtail  # cola aleatoria acumulativa (tope 500; 0 peticiones si está llena)
python -m src.snapshot           # snapshot versionado (append-only, con hora)
python -m src.matching           # identidad cruzada RAWG↔IGDB -> matching.csv (derivado)
python -m src.precios            # precios PC CheapShark (USD, ~47 peticiones con pausa)
python -m src.competidores       # regla v1 en 3 pilotos (sin API, deduplicado)
python -m src.scoring --slug hollow-knight --source igdb --estricto  # scoring + modo estricto
python -m src.evolucion          # deltas entre los 2 últimos snapshots (si existen)
python -m src.export_web         # regenera web/data/*.json desde el último snapshot
python -m unittest discover tests  # 61 tests (sin API)
jupyter notebook notebooks/02_eda.ipynb

# app web: doble clic en web/index.html, o en local con servidor:
cd web; python -m http.server 8000   # abrir http://localhost:8000
```

`.env` está gitignorado y ninguna salida imprime claves. En GitHub Actions, los mismos pasos corren cada lunes con los secrets del repositorio (`.github/workflows/weekly_snapshot.yml`).

## 7. Estructura del repositorio

```
├── README.md
├── requirements.txt
├── .env.example
├── .github/workflows/       # snapshot-semanal.yml (lunes 06:00 UTC + manual)
├── src/                     # config, datos, check_connections, muestreo (top),
│                            # muestreo_midtail, muestreo_longtail, matching, precios,
│                            # competidores, scoring (con --estricto), snapshot,
│                            # evolucion, export_web
├── tests/                   # 61 tests: scoring (+modo estricto), matching, precios,
│                            # datos, snapshot, evolución, export (sin API)
├── notebooks/               # 01 plan de auditoría, 02 EDA ejecutado
├── web/                     # app estática (index.html, js/, styles/, data/ generada)
├── data/
│   ├── raw/                 # respuestas originales (gitignorado, solo local)
│   ├── processed/           # oleadas top/mid/cola + release_dates + matching + precios
│   └── snapshots/           # fotos deduplicadas y fechadas, append-only (+ .meta.json)
└── docs/                    # 01 validación, 02 decisión, 03 auditoría, 04 diccionario+modelo,
                             # 05 equivalencias, 06 KPIs, 07 metodología, 08 caso de prueba
```

## 8. Estado actual y hoja de ruta

Implementado (no pendiente): cola aleatoria acumulativa con tope (§3), modo estricto de la regla (§4), matching cruzado con confianza declarada (§4), precio PC CheapShark aislado del comparador (§2/§4), snapshots semanales automatizados con tests previos al commit (§4), y ampliación de la muestra con grupo Nintendo propio + Switch 2 vía IGDB (§2).

Trabajo futuro que sí requiere más tiempo (por requisito de honestidad, no por falta de implementación): validación humana del matching (revisión de los casos “cercano” y de ediciones con nombre casi idéntico), conversión a EUR solo si aparece una fuente con tipo de cambio observable, precios de consola con fuente comparable, y ponderación por rareza de género si surge una fuente de catálogo que la sustente.
