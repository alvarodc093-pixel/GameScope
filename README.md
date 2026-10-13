# GameScope

Comparador de videojuegos frente a sus competidores directos en PC, consolas y móvil, con fuentes verificadas y observaciones fechadas.

## 1. Problema y para quién

Quien sigue el mercado del videojuego (aficionados exigentes, pequeños estudios, tiendas) no tiene una forma rápida de responder: “¿cómo se posiciona este juego frente a sus competidores directos?”. Las notas de prensa y de usuarios viven en sitios distintos, con escalas y coberturas distintas, y nadie las pone lado a lado por plataforma.

GameScope responde a eso: eliges un juego y ves sus competidores (mismo género, mismas plataformas, misma era) con crítica y usuarios separados, cada métrica con su escala y su número de votos.

## 2. Datos: origen y obtención

* **IGDB (principal):** `POST api.igdb.com/v4/games|platforms|release_dates` con OAuth2 de Twitch. Permite almacenar snapshots.
* **RAWG (complemento):** `GET api.rawg.io/api/games|platforms?key=` + detalle `/games/{id}` para desarrollador/editor. Plan Free 20.000 req/mes; raw solo local (no redistribuir).
* Precio descartado del MVP: ninguna fuente lo da comparable para PC+consola+móvil.
* Todo el acceso está en `src/` y usa `.env` (`RAWG_API_KEY`, `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`). Detalle en `docs/01_validacion_fuentes.md` y `docs/02_decision_fuentes.md`.

## 3. Preprocesamiento y EDA: decisiones y hallazgos

* Normalización a esquema común con `observed_at` + `source` (`src/muestreo.py` → `data/processed/muestra_normalizada.csv`, 200 filas top; `src/muestreo_midtail.py` → 160 mid-tail + `release_dates_10.csv`).
* Decisiones: identidad por `(source, source_id)`, nunca por título; métricas lado a lado sin fusionar; géneros con tabla de equivalencias (`docs/05`).
* Hallazgos (`notebooks/02_eda.ipynb`, n=360): medianas al techo por sesgo top (85/100 y 4.11/5); Pearson crítica-usuarios ≈0.69 con n dispares (prensa n≈11 vs usuarios n≈miles); casi todo multiplataforma (filtro por plataforma obligatorio); mediana de año 2014; pocos estudios concentran el top. RAWG-lista no trae dev/editor (se recuperan al 10/10 vía detalle, +1 req/juego).

## 4. Ciencia de datos: enfoque, métricas y limitaciones

* Enfoque actual: scoring heurístico v1 y configurable (`src/scoring.py`, pesos y umbrales ajustables, 7 tests OK): género + plataforma (requisitos duros) + era + estudio si existe, normalizado por máximo aplicable y con explicación por pareja (`docs/07_metodologia.md`, caso real `docs/08_caso_prueba.md`). Subgénero, negocio y audiencia excluidos por falta de fuente.
* Métricas: cobertura crítica/usuarios %, medianas por escala, confianza crítica (n≥5), multiplataforma % (`docs/06_kpis_snapshot.md`).
* Limitaciones: muestra top = techo de cobertura; `Action↔Adventure` es aproximada; era ±4 arbitraria; mismo título ≠ mismo juego; sin precio; `/release_dates` no universal (7/10).

## 5. Aplicación: estado

Pendiente de construir (Streamlit con los snapshots versionados). No hay capturas ni URL todavía: este README se actualizará con uso paso a paso, capturas y enlace al deploy cuando existan.

## 6. Instalación y ejecución (Windows, PowerShell, desde la raíz)

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # solo la primera vez; luego rellena tus 3 claves
python -m src.check_connections  # conectividad IGDB+RAWG
python -m src.muestreo           # muestra top 200 (consume cuota: ~12 peticiones)
python -m src.muestreo_midtail   # mid-tail + release_dates + detalle RAWG
python -m src.competidores       # regla v1 en 3 pilotos (sin API)
python -m src.scoring --slug hollow-knight --source igdb  # scoring v1 + explicación
python -m src.snapshot           # snapshot versionado en data/snapshots/
python -m unittest discover tests  # 7 tests del scoring (sin API)
jupyter notebook notebooks/02_eda.ipynb
```

`.env` está gitignorado y ninguna salida imprime claves.

## 7. Estructura del repositorio

```
├── README.md
├── requirements.txt
├── .env.example
├── src/                  # config, check_connections, muestreo, muestreo_midtail, competidores, snapshot
├── notebooks/            # 01 plan de auditoría, 02 EDA ejecutado
├── data/
│   ├── raw/              # respuestas originales (gitignorado, solo local)
│   ├── processed/        # muestras normalizadas + release_dates (versionado)
│   └── snapshots/        # fotos deduplicadas y fechadas, append-only
└── docs/                 # 01 validación, 02 decisión, 03 auditoría, 04 diccionario+modelo, 05 equivalencias, 06 KPIs
```

## 8. Qué mejoraría con más tiempo

1. Muestra long-tail aleatoria para medir el suelo real de cobertura.
2. Endurecer la regla (≥2 géneros o peso por rareza, penalizar mismo estudio).
3. Matching cruzado RAWG↔IGDB semi-automático con validación manual.
4. Repetir snapshots al calendario (semanal ratings, mensual estáticos) y graficar evolución.
5. Módulo de precio solo-PC (CheapShark, USD) aislado del comparador principal.
6. La aplicación Streamlit desplegada con atribución a ambas fuentes.
