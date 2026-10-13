# 02 — Comparación y decisión de fuentes (GameScope Fase 1)

Fecha: 2026-10-13.
Base: `docs/01_validacion_fuentes.md`. Sin ejecuciones todavía: los “resultados medidos” son 0 y van separados de los criterios propuestos.

> Nota posterior (Fase 2): decisión confirmada con datos en `docs/03_auditoria_exploratoria.md` y `docs/05_equivalencias_competidores.md`.

## 1. Comparativa resumida (documental, no medida)

| Dimensión | RAWG | IGDB (Twitch) | CheapShark / Steam (solo precio PC) |
|---|---|---|---|
| Acceso MVP | Simple: `GET + ?key=`. Ideal bootcamp. | Medio: OAuth Twitch + POST Apicalypse + paginación + CORS solo backend. | Simple (sin key), pero solo PC. |
| Cobertura PC/consola/móvil | Declara 500k+ juegos, 50 plataformas incl. móvil. Por verificar IDs. | Modelo `platforms/families/versions + release_dates` muy expresivo. Por mapear familias. | Solo PC digital. No cubre consola/móvil. |
| Críticos vs usuarios | `metacritic` vs `rating` (interno RAWG). Riesgo de confundir universos. | `aggregated_rating(+count)` vs `rating(+count)` bien separados. Mejor para pregunta 3. | Añade `metacriticScore` + `steamRating*`, tercer universo. No mezclar. |
| Dev / Publisher | `developers[]`, `publishers[]` planos. | `involved_companies{developer,publisher}` explícito. Mejor. | No aplica. |
| Fecha lanzamiento | `released` global. Poco granular por plataforma. | `first_release_date` + `/release_dates` por plataforma/región. Mejor para pregunta 2. | `releaseDate` solo PC. |
| Precio / moneda | No en Free (solo links “where to buy” en Business). | No existe. | Sí, pero USD y PC-only. Sesgo si se mezcla. |
| Rate / cuota | 20k req/mes Free. Suficiente si se pagina con `page_size` y throttle. | 4 req/s, 8 abiertas, sin tope mensual. Mejor para auditoría incremental. | Límites bajos / no oficiales. |
| Almacenar snapshots | Restringido: “no redistribution”. Raw en repo público = riesgo. | Permitido y recomendado. Habilita `data/raw/` + serie temporal. | Permitido con atribución/enlaces, pero solo PC. |
| Deploy bootcamp | Exige backlink en cada página + no clonar. Viable en Streamlit si se cumple. | Exige no exponer Secret + atribución si comercial. Viable en Streamlit con backend. | Exige usar sus links de deals. |
| Riesgo principal | Legal (redistribución) + nulos en `metacritic`. | Técnico (OAuth, CORS, Apicalypse) + nulos fuera del top. | Alcance (PC-only, USD) + sin SLA. |

## 2. Criterios de aceptación (propuestos, pendientes de medir)

Separados de resultados. Se miden en `notebooks/01_auditoria_datos.ipynb` con muestra PC + consola + móvil (mínimo 30 por grupo, `page_size>=20`).

* **C1 Cobertura multiplataforma:** >=95% registros con plataforma válida; >=30 juegos por grupo PC / consola / móvil; `platforms` mapeado a familias sin ambigüedad.
* **C2 Calidad base:** IDs únicos sin nulos; 0 duplicados por `(source, source_id, platform_id)`; % nulos reportado por campo (no se elimina nada sin justificar).
* **C3 Completitud fechas:** >=90% con fecha válida (`released` o `release_dates.date`). Si RAWG <90% por ser global, penaliza frente a IGDB.
* **C4 Comparabilidad valoraciones:** % con críticos y % con usuarios por separado; nunca promediar fuentes distintas. Umbral orientativo: >=40% con al menos una métrica y >=20% con ambas para que el comparador tenga sentido. Si no se alcanza, reducir alcance a top/populares y comunicarlo.
* **C5 Estabilidad acceso:** 0 `401` no recuperados, `429` con backoff OK, <5% errores `5xx` con reintento, paginación completa sin pérdidas.
* **C6 Compatibilidad deploy:** permite cachear snapshots + atribuir en Streamlit/Vercel sin exponer secretos. Si exige exponer Secret en frontend o prohíbe cachear, no apta como principal.
* **C7 Precio (opcional):** solo se acepta si cubre las 3 familias con misma moneda o se aísla a módulo PC-USD con disclaimer. Si no, precio fuera del MVP.

Resultados medidos a día de hoy: **ninguno** (faltan credenciales). No hay % ni conteos. Ver §5.

## 3. Decisión final (razonada, reversible tras prueba)

* **Fuente principal: IGDB.**
  Motivo: mejor separación críticos/usuarios, mejor granularidad por plataforma (`release_dates`), distinción developer/publisher, y sobre todo **permite almacenar snapshots y servirlos** — imprescindible para preguntas 5 y 6 y para `data/raw/` + deploy. El coste (OAuth + Apicalypse + backend por CORS) es asumible y formativo para BI.
* **Fuente secundaria: RAWG (validación cruzada, no base).**
  Motivo: simplicidad y cobertura declarada amplia. Útil para contrastar `metacritic` y completar huecos donde IGDB tenga nulos, siempre que se respeten atribución con hyperlink y no-redistribución (raw local gitignorado). No usar como principal por restricción de almacenamiento y por fecha solo global.
* **Precio: descartado del MVP.**
  Ni IGDB ni RAWG Free lo resuelven para PC+consola+móvil. CheapShark/Steam solo dan PC-USD sin SLA y romperían la comparabilidad. Posible módulo PC-only en fase 2, aislado y con disclaimer de moneda/tienda/fecha.

Campos utilizables (si la prueba los confirma):

* IGDB: `id`, `name`, `platforms`, `genres`, `first_release_date` + `release_dates.date/human`, `involved_companies.company + developer/publisher`, `aggregated_rating(+count)`, `rating(+count)`, `cover/image_id`, `checksum`, más `observed_at`, `source` generados por nosotros.
* RAWG (secundaria): `id/slug`, `name`, `platforms`, `genres`, `released`, `developers/publishers`, `metacritic`, `rating`, `ratings_count/reviews_count`, `updated`, más `observed_at`, `source`.

Campos a descartar en MVP:

* `precio/moneda` (sin fuente comparable trilateral), `stores/where-to-buy` Free (no disponible), promedios que mezclen Metacritic+RAWG+IGDB+Steam, `similar_games` RAWG Free (es de Business), imágenes en bruto sin atribución.

## 4. Limitaciones conocidas (para comunicar en la app)

1. Cobertura sesgada al top: juegos nicho/móvil indie tendrán más nulos en valoraciones.
2. Universos distintos: prensa vs usuarios IGDB vs Metacritic vs RAWG vs Steam no son intercambiables.
3. Fechas: RAWG global vs IGDB por región/plataforma; convertir timestamps a UTC y mostrar región.
4. Ediciones: filtrar `version_parent = null` en IGDB o se duplican comparables.
5. Atribución obligatoria en ambas; RAWG exige hyperlink por página.
6. Sin precio comparable trilateral en MVP.
7. Todo lo anterior es documental hasta ejecutar la auditoría.

## 5. Riesgos pendientes

* Sin `RAWG_API_KEY` ni `IGDB_CLIENT_ID/SECRET` no hay auditoría (C1–C7 sin medir).
* RAWG puede denegar versionar raw en repo del bootcamp aunque sea privado.
* IGDB puede fallar por token caducado, CORS si se llama desde frontend, o `429` sin throttle.
* Mapeo PC/consola/móvil puede requerir curaduría manual de familias.
* Si C4 no se cumple, hay que recortar alcance a “comparador top con disclaimer”, no forzar métricas.

## 6. Viabilidad y próximo paso

* Viabilidad: **alta condicional**. El caso de uso (comparador con críticos vs usuarios por plataforma + snapshots) es viable **si** IGDB confirma C1–C6 en la muestra. RAWG queda como red de seguridad.
* Próximo paso recomendado (en orden):
  1. Crear credenciales (ver `.env.example`) y ejecutar `notebooks/01_auditoria_datos.ipynb` con 3 consultas (PC, consola, móvil).
  2. Medir C1–C6 y decidir si se mantiene IGDB-principal o se invierte a RAWG-principal.
  3. Solo entonces diseñar EDA, KPIs y app. No desarrollar app ahora.

> Si la prueba muestra <20% con ambas valoraciones o <90% fechas, se recorta alcance antes de escribir más código.
