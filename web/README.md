# GameScope web (Vercel)

Comparador estático: HTML + CSS + JS sin build. Los datos son una foto generada del snapshot (`web/data/games.json`, 229 juegos).

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
python -m src.snapshot    # nuevo snapshot fechado
python -m src.export_web  # reescribe web/data/*.json desde el último snapshot
```

## Modificar

* Diseño: `styles/main.css` (variables en `:root`).
* Regla de similitud: `js/scoring.js` (réplica de `src/scoring.py`; mantén pesos y umbrales sincronizados).
* Textos/secciones: `index.html`.

## Desplegar en Vercel

1. Sube el repo a GitHub.
2. En Vercel: Add New → Project → importa el repo.
3. **Root Directory:** `web` (el resto — `src/`, `data/`, `.env` — queda fuera del deploy).
4. Framework Preset: **Other**. Sin build command ni variables de entorno.
5. Deploy. Cada push a `main` redespliega.

La web no llama a IGDB/RAWG en tiempo real: todo es dato estático versionado, así que no hay claves ni cuotas en producción.
