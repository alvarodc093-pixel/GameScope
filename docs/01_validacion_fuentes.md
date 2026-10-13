# 01 — Validación de fuentes (GameScope Fase 1)

Fecha de consulta: 2026-10-13.
Estado: investigación documental completada. Prueba de acceso **no ejecutada** (faltan credenciales). Sin datos reales, sin estadísticas inventadas.

Fuentes oficiales consultadas:

* RAWG: https://rawg.io/apidocs y https://rawg.io/tos_api
* IGDB: https://api-docs.igdb.com/ (Getting Started, Endpoints, FAQ / Business FAQ, Rate Limits)
* CheapShark (solo precio PC): https://apidocs.cheapshark.com/ y https://www.cheapshark.com/api
* Steam Store (solo precio PC, no oficial): `store.steampowered.com/api/appdetails` y `store.steampowered.com/api/priceoverview/` — documentación comunitaria, sin SLA.

> Principio de esta fase: primero validamos problema y datos. No hay aplicación todavía.

## 1. Preguntas de negocio -> qué necesita cada fuente

1. ¿Qué juegos son comparables a un título? Necesita búsqueda por nombre, filtros por género/plataforma y algún mecanismo de similitud.
2. ¿Qué plataformas, géneros y fechas comparten? Necesita plataformas, géneros y fecha de lanzamiento con cobertura PC / consola / móvil.
3. ¿Cómo se comparan valoraciones críticas y de usuarios? Necesita **dos métricas separadas**, sin mezclar fuentes.
4. ¿Diferencias de disponibilidad PC / consola / móvil? Necesita cobertura medible por plataforma.
5. ¿Observaciones periódicas? Necesita que el almacenamiento de instantáneas esté permitido.
6. ¿Limitaciones a comunicar? Necesita procedencia, fecha de consulta y huecos conocidos.

## 2. RAWG API

Base: `https://api.rawg.io/api`.
Docs: https://rawg.io/apidocs. Condiciones: https://rawg.io/tos_api.

### Autenticación

* Query param `?key=YOUR_API_KEY` en cada petición. Ejemplo doc oficial:
  `GET https://api.rawg.io/api/games?key=YOUR_API_KEY&dates=2019-09-01,2019-09-30&platforms=18,1,7`
* La key se obtiene con cuenta en `rawg.io/apidocs` (login). Sin key, riesgo de baneo según docs.

### Endpoints relevantes para GameScope

* `GET /games` — lista y búsqueda (`search`, `search_precise`, `search_exact`, `dates`, `platforms`, `genres`, `developers`, `publishers`, `metacritic`, `ordering`).
* `GET /games/{game_pk}` — detalle (incluye `updated`, requisitos sistema, web, metacritic por plataforma según changelog).
* `GET /platforms` — para resolver IDs de plataforma antes de filtrar juegos.
* `GET /genres`, `GET /developers`, `GET /publishers`, `GET /tags`.
* Cobertura declarada en apidocs: 500.000+ juegos, 50 plataformas incluyendo móvil, 2,1M screenshots, 1,1M ratings.

### Campos (documentados, cobertura real pendiente de medir)

Lista declara, entre otros: `id`, `slug`, `name`, `released`, `platforms[]`, `genres[]`, `developers[]`, `publishers[]`, `metacritic`, `rating`, `ratings_count`, `reviews_count`, `added`, `playtime`, `esrb_rating`, `stores[]`, `updated`.

Mapeo a campos pedidos:

| Campo pedido | RAWG | Observación |
|---|---|---|
| ID original | `id` + `slug` | Disponible según docs. Cobertura por medir. |
| Nombre | `name` | Disponible. |
| Plataformas | `platforms[].platform.id/name/slug` | Incluye PC y móvil según marketing. IDs exactos por confirmar en `/platforms`. |
| Géneros | `genres[]` | Disponible. |
| Fecha lanzamiento | `released` (fecha, a nivel juego) | No es por plataforma en lista. El detalle por plataforma es vía Metacritic por plataforma. Riesgo para comparar fechas por plataforma. |
| Desarrollador / distribuidor | `developers[]`, `publishers[]` | Disponible pero depende de contribución. Nulos esperables. |
| Puntuación críticos | `metacritic` | Es Metacritic agregado. Puede ser `null` en muchos juegos. No confundir con `rating`. |
| Valoración usuarios | `rating` | Es rating interno RAWG, no IGDB ni Steam. No mezclar con Metacritic sin justificar. |
| Nº valoraciones | `ratings_count`, `reviews_count`, `added` | Disponibles según docs. Significado distinto: contar votos vs reseñas vs guardados. Documentar en app. |
| Precio / moneda | No en plan Free | `stores` con enlaces “where to buy” es de plan Business. Precio descartado en RAWG Free. |
| Fecha consulta | No la da la API | La genera nuestro código (`observed_at`). |
| Fuente procedencia | No la da la API | La genera nuestro código (`source='rawg'`). |
| ID versión / plataforma | Parcial | `platforms[]` distingue plataforma, pero no hay `game_version` estable como en IGDB. Pendiente de validar. |

### Límites y planes (vigentes según apidocs el 2026-10-13)

* Free: hasta 20.000 req/mes, proyectos personales / hobby, no comercial. Datos base 500k juegos.
* Business (~149 $/mes): hasta 50.000 req/mes, uso comercial, enlaces de compra, similares, vídeos, soporte email.
* Enterprise: hasta 1.000.000 req/mes, file API descargable, peticiones custom. Contacto `api@rawg.io`.
* Umbral comercial citado: gratis si <100.000 MAU o <500.000 pageviews/mes; si mayor, pedir términos. Hay redacción distinta entre `/apidocs` y `/tos_api` — tratar como **pendiente de aclaración** por email si el deploy crece.

### Atribución y restricciones (críticas para deploy)

* Atribución obligatoria: crédito a RAWG + hipervínculo activo **en cada página** donde se usen datos o imágenes.
* No redistribución: no revender datos ni ponerlos a disposición de otros negocios. No usar la API para clonar RAWG.
* Aviso legal: RAWG no reclama propiedad de imágenes/datos, retira contenido infractor si se notifica. Prohibido uso difamatorio/obsceno/ofensivo.
* Consecuencia práctica: `data/raw/` con respuestas RAWG **no debe subirse a repo público**. Guardar en local + `.gitignore`, o pedir permiso escrito. Esto limita la auditoría reproducible en GitHub.

## 3. IGDB API (Twitch)

Base: `https://api.igdb.com/v4`.
Docs: https://api-docs.igdb.com/.

### Autenticación

1. Cuenta Twitch + 2FA activado.
2. Registrar app en Twitch Developer Portal, tipo `Confidential`, Redirect `localhost` (no se usa por IGDB pero lo pide el formulario).
3. Generar Client Secret. Guardar `Client-ID` + `Client Secret`.
4. Token OAuth2 client_credentials:

```http
POST https://id.twitch.tv/oauth2/token?client_id=XXX&client_secret=YYY&grant_type=client_credentials
```

Respuesta: `{"access_token":"...","expires_in":~5587808,"token_type":"bearer"}` (~60 días).

Cada consulta:

```http
POST https://api.igdb.com/v4/games
Client-ID: XXX
Authorization: Bearer TOKEN
Body: fields name,genres.name,platforms.name; limit 10;
```

* No funciona directo desde navegador por CORS. Hay que llamar desde backend Python (requests) o proxy. Esto afecta a Streamlit: las llamadas deben ir en servidor, nunca exponer Secret en frontend.

### Endpoints relevantes

* `POST /games` — núcleo. Soporta `fields`, `where`, `sort`, `limit`, `offset`, `search`.
* `POST /platforms`, `/platform_families`, `/platform_versions` — para separar PC / consola / móvil y versiones.
* `POST /genres`, `/themes`, `/game_modes` — para comparables.
* `POST /involved_companies` + `/companies` — distingue developer vs publisher (`developer=true/false`, `publisher=true/false`).
* `POST /release_dates` — fecha por juego+plataforma+región (`date`, `game.platforms`, `human`). Clave para pregunta 2.
* `POST /covers`, `/screenshots`, `/artworks` — `image_id` -> `https://images.igdb.com/igdb/image/upload/t_{size}/{image_id}.jpg`.
* `POST /search` — búsqueda federada (games, characters, collections, platforms, themes).
* `POST /games/count` — conteos para auditoría.

Lenguaje Apicalypse: `fields name,rating; where rating > 75; sort rating desc; limit 10;`. Límite 500 por petición, paginar con `offset`. Selectivo con `fields` (evitar `fields *` salvo exploración).

### Campos (documentados, cobertura real pendiente de medir)

| Campo pedido | IGDB | Observación |
|---|---|---|
| ID original | `games.id` + `checksum` | Estable. `checksum` es hash del objeto. |
| Nombre | `games.name`, `alternative_names` | Disponible. Filtrar ediciones con `version_parent = null` para no duplicar “Collector’s Edition”. |
| Plataformas | `games.platforms[]` -> `/platforms` | Modelo rico. Separar por familia para PC / consola / móvil. |
| Géneros | `games.genres[]` -> `/genres` | Disponible. |
| Fecha lanzamiento | `games.first_release_date` + `/release_dates.date` | Unix timestamp. `first_release_date` es global; `/release_dates` da granularidad por plataforma/región. Convertir a fecha UTC y guardar `observed_at` aparte. |
| Desarrollador / distribuidor | `/involved_companies` (`company`, `developer`, `publisher`) + `/companies.name` | Distinción explícita, mejor que RAWG. Requiere 2 saltos (expand). |
| Puntuación críticos | `games.aggregated_rating` + `aggregated_rating_count` | Agregado prensa externa. No mezclar con `rating`. Muchos nulos esperables fuera del top. |
| Valoración usuarios | `games.rating` + `rating_count`, `total_rating` | Votos miembros IGDB. Distinto universo que Metacritic/Steam. |
| Nº valoraciones | `aggregated_rating_count`, `rating_count` | Disponibles. Documentar denominador en la app. |
| Precio / moneda | No existe | Descartado en IGDB. Ver §4 si se quiere precio solo PC. |
| Fecha consulta | No la da la API | La genera nuestro código. |
| Fuente procedencia | No la da la API | La genera nuestro código (`source='igdb'`). |
| ID versión / plataforma | `game_versions`, `platform_versions`, `release_dates.id` | Disponible. Útil para pregunta 5 (snapshot por plataforma). |

### Límites y condiciones

* Rate: 4 req/seg por Client-ID, hasta 8 peticiones abiertas. `429 Too Many Requests` si se excede. Implementar throttle + backoff + reintento con jitter. `401` -> refrescar token.
* Sin límite mensual (el antiguo tope 50k se eliminó, queda rate por segundo). Suficiente para auditoría por lotes.
* Gratis para uso **no comercial** bajo Twitch Developer Services Agreement. Comercial requiere partnership (`partner@igdb.com`) con atribución visible a IGDB.com.
* Almacenamiento: **sí permitido, y recomendado**. FAQ oficial dice preferible almacenar y servir desde tu lado para no cargar la API. Los datos conservados se pueden mantener aunque termine el partnership. Esto habilita `data/raw/`, snapshots y deploy.
* No republicar el dataset en bruto a granel. Atribuir donde se requiera y cumplir Twitch DSA.

## 4. Otras fuentes (solo si resuelven carencia)

Carencia común: **precio y moneda**. Ni RAWG Free ni IGDB lo dan de forma utilizable para comparar PC/consola/móvil.

* **CheapShark** (`https://www.cheapshark.com/api`, docs en `apidocs.cheapshark.com`): gratis, sin key, solo juegos digitales **PC** (Steam, GreenManGaming, Fanatical...). Devuelve `salePrice`, `normalPrice`, `isOnSale`, `savings`, `storeID`, `steamAppID`, `metacriticScore`, `steamRatingText/Percent/Count`, `releaseDate`, `lastChange` (timestamps). Precios siempre en USD. Condición: usar enlaces CheapShark al redirigir a ofertas. Útil solo como complemento opcional PC. No resuelve consola/móvil. Mezclar USD-PC con valoraciones multi-plataforma exige justificar comparabilidad.
* **Steam Store API** (`store.steampowered.com/api/appdetails?appids=XXX&filters=price_overview`): no oficial, sin key, con rate limit comunitario (~200 req/5 min). Devuelve `price_overview {currency, initial, final, discount_percent}` por `steamAppID` y país. Sin SLA, puede cambiar sin aviso. Solo PC-Steam. Descartado para MVP salvo que el alcance se limite a PC.
* Descartadas por ahora: scraping Metacritic/OpenCritic (riesgo ToS), MobyGames/GiantBomb (no aportan ventaja clara frente a IGDB+RAWG para las 6 preguntas).

Conclusión precio: para responder a las 6 preguntas sin sesgo, **precio fuera del MVP**. Si se quiere, fase 2 solo-PC con CheapShark, aislado del comparador principal.

## 5. Histórico e instantáneas

* IGDB: permitido cachear. Estrategia válida: tabla `snapshots(game_id, platform_id, observed_at, aggregated_rating, aggregated_rating_count, rating, rating_count, source)` + `checksum` IGDB para detectar cambios. `first_release_date` y `companies` son estables (refresco mensual); ratings son volátiles (refresco semanal/diario según rate). No inventar histórico: solo filas con `observed_at` real.
* RAWG: `updated` en detalle indica última actualización, útil para decidir re-fetch, pero almacenar serie temporal en repo público choca con “no redistribución”. Estrategia si se usa: snapshots solo locales, gitignorados, y publicar solo agregados con atribución + link. Pendiente de confirmación escrita a `api@rawg.io`.
* Campos aptos para serie temporal: ratings y conteos. Campos no aptos: precio (no hay en principales), fechas de lanzamiento pasadas (inmutables).

## 6. Pendiente de validación (no asumir)

1. Obtener `RAWG_API_KEY` y `IGDB_CLIENT_ID/SECRET` y ejecutar `notebooks/01_auditoria_datos.ipynb`.
2. Medir cobertura real: % nulos por campo, duplicados, IDs ausentes, cobertura por plataforma/género, % con `metacritic`/`aggregated_rating` y con `rating`.
3. Confirmar IDs de plataforma RAWG para PC / PlayStation / Xbox / Nintendo / iOS / Android vía `GET /platforms`.
4. Confirmar mapeo familias IGDB para agrupar PC / consola / móvil.
5. Aclarar con `api@rawg.io` si se pueden versionar `data/raw/*.json` en repo privado del bootcamp y qué agregados se pueden publicar con atribución.
6. Definir comparables: ¿por género+plataforma, por `similar_games` (Business RAWG) o por distancia de features en IGDB? Sin datos no decidir.
7. Precio: solo si se acepta alcance PC-only con CheapShark USD.

Sin estos 7 puntos no hay decisión definitiva de campos ni de umbrales.
