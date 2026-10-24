# GameScope web (Vercel)

Comparador estático: HTML + CSS + JS **sin build y sin servidor obligatorio**. Los datos son una foto generada del snapshot (`web/data/games.json` — 1.131 juegos en la última exportación, 2026-10-24) más `meta.json` y `evolucion.json`; la app los carga desde `web/data/datos.js` (mismos datos como script global), por lo que **funciona abriendo `index.html` con doble clic** y también con cualquier servidor estático.

## Funcionalidades

* Buscador en un solo paso: escribes → eliges de la lista → comparación al instante (insensible a mayúsculas/acentos; avisa si el juego está en la otra fuente). La landing carga con Hollow Knight ya comparado y chips de ejemplos.
* Fuente (IGDB/RAWG), umbral de tier, nº de resultados.
* **Modo estricto** (interruptor “Regla”): admisión dura — año obligatorio en ambas partes y ≥2 géneros en común; el encabezado lo declara. Sincronizado con `src/scoring.py --estricto` (mismos pesos, mismos motivos de descarte).
* **“También en la otra fuente”**: enlace de contraparte con confianza declarada (exacto/cercano, de `src/matching.py`) que cambia de fuente y selecciona el mismo juego; las métricas nunca se cruzan entre fuentes.
* **Precio PC** en la tarjeta de referencia: USD de CheapShark con su `observed_at` y la moneda explícita (no convertido); solo si hay oferta equivalente.
* Filtros de plataforma y género (opciones salen de los datos del snapshot) que restringen la lista de competidores.
* Tabla comparativa ref vs competidores (Δ crítica, Δ usuarios, Δ años; solo intra-fuente y misma escala).
* Resumen de diferencias con mediana del grupo y caveats (no hay ventas ni métricas fusionadas).
* Scoring v1 en `js/scoring.js`: réplica de `src/scoring.py` (incluido modo estricto); mantén pesos y umbrales sincronizados.
* Sección Evolución: deltas reales con ≥2 snapshots; con una sola foto, la app lo indica en lugar de inventar una tendencia.

## Ejecutar en local

```powershell
# Opción 1: doble clic en web/index.html (ya funciona: los datos viajan como script)
# Opción 2: servidor local (recomendado para probar como en producción)
# desde la carpeta web/
python -m http.server 8000
# abrir http://localhost:8000
```

> Nota: los módulos ES y `fetch()` de JSON están bloqueados en `file://`; por eso la app usa scripts clásicos y `data/datos.js` en lugar de `fetch` a JSON.

## Regenerar datos

```powershell
# desde la raíz del repo
python -m src.muestreo           # (opcional) nueva captura top; consume cuota
python -m src.muestreo_midtail   # (opcional) mid-tail
python -m src.muestreo_longtail  # (opcional) cola acumulativa; 0 peticiones si está al tope
python -m src.snapshot           # snapshot fechado con hora (append-only, no sobrescribe)
python -m src.matching           # identidad RAWG↔IGDB (requiere snapshot reciente)
python -m src.precios            # (opcional) precios PC CheapShark; consume cuota
python -m src.export_web         # reescribe web/data/*.json y datos.js desde el último snapshot
```

Los contraprecios (`contraparte`) y precios (`precio_pc`) se adjuntan al export; no inventan filas: si un juego no tiene precio o contraparte, simplemente no lleva ese bloque.

## Modificar

* Diseño: `styles/main.css` (variables en `:root`).
* Regla de similitud: `js/scoring.js` (réplica de `src/scoring.py`).
* Renderizado (tabla, insights, evolución): `js/ui.js`. Estado y eventos: `js/app.js`.
* Textos/secciones: `index.html`.
* Los JS son scripts clásicos con namespace `window.GS` (sin import/export): el orden de carga en `index.html` importa (scoring → ui → data → app).

## Desplegar en Vercel

1. Sube el repo a GitHub.
2. En Vercel: Add New → Project → importa el repo.
3. **Root Directory:** `web` (el resto — `src/`, `data/`, `.env` — queda fuera del deploy).
4. Framework Preset: **Other**. Sin build command ni variables de entorno.
5. Deploy. Cada push a `main` redespliega.

La web no llama a IGDB/RAWG en tiempo real: todo es dato estático versionado, así que no hay claves ni cuotas en producción.
