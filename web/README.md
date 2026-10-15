# GameScope web (Vercel)

Comparador estático: HTML + CSS + JS sin build. Los datos son una foto generada del snapshot (`web/data/games.json`, 229 juegos) más `meta.json` (trazabilidad) y `evolucion.json` (deltas entre snapshots, o bandera honesta si hay menos de 2 fotos).

## Funcionalidades

* Buscador en un solo paso: escribes → eliges de la lista → comparación al instante (insensible a mayúsculas/acentos; avisa si el juego está en la otra fuente). La landing carga con Hollow Knight ya comparado y chips de ejemplos.
* Fuente (IGDB/RAWG), umbral de tier, nº de resultados.
* Filtros de plataforma y género (opciones salen de los datos del snapshot) que restringen la lista de competidores.
* Tabla comparativa ref vs competidores (Δ crítica, Δ usuarios, Δ años; solo intra-fuente y misma escala).
* Resumen de diferencias con mediana del grupo y caveats (no hay ventas ni métricas fusionadas).
* Scoring v1 en `js/scoring.js`: réplica de `src/scoring.py`; mantén pesos y umbrales sincronizados.
* Sección Evolución: deltas reales con ≥2 snapshots; con 1 sola foto, estado vacío honesto.

## Ejecutar en local

```powershell
# desde la carpeta web/
python -m http.server 8000
# abrir http://localhost:8000
```

> Abrir `index.html` como fichero no funciona: los módulos ES y `fetch()` exigen servidor HTTP.

## Regenerar datos

```powershell
# desde la raíz del repo
python -m src.muestreo       # (opcional) nueva captura de muestras; consume cuota
python -m src.snapshot       # snapshot fechado con hora (append-only, no sobrescribe)
python -m src.export_web     # reescribe web/data/*.json desde el último snapshot
```

## Modificar

* Diseño: `styles/main.css` (variables en `:root`).
* Regla de similitud: `js/scoring.js` (réplica de `src/scoring.py`).
* Renderizado (tabla, insights, evolución): `js/ui.js`. Estado y eventos: `js/app.js`.
* Textos/secciones: `index.html`.

## Desplegar en Vercel

1. Sube el repo a GitHub.
2. En Vercel: Add New → Project → importa el repo.
3. **Root Directory:** `web` (el resto — `src/`, `data/`, `.env` — queda fuera del deploy).
4. Framework Preset: **Other**. Sin build command ni variables de entorno.
5. Deploy. Cada push a `main` redespliega.

La web no llama a IGDB/RAWG en tiempo real: todo es dato estático versionado, así que no hay claves ni cuotas en producción.
