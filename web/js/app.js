// Estado y cableado del comparador (script clasico: funciona con servidor y
// con doble clic en index.html, sin modulos ES ni fetch).
// Buscador: escribir -> elegir de la lista -> comparación al instante (un solo paso).
(function (global) {
  "use strict";
  const GS = global.GS;
  const $ = (id) => document.getElementById(id);
  const estado = {
    games: [], source: "igdb", tier: "secundario", top: 10, refSlug: null,
    plataforma: "", genero: "", evolucion: null,
  };

  const RANGO = { directo: 3, secundario: 2, relacionado: 1, descartado: 0, insuficiente: -1 };

  // Juego preseleccionado al cargar: la app se explica sola con un ejemplo real.
  const EJEMPLO_INICIAL = { slug: "hollow-knight", source: "igdb" };

  const normalizar = (s) =>
    (s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

  function juegosDeFuente() {
    return estado.games.filter((j) => j.source === estado.source);
  }

  // Busca por nombre (insensible a mayúsculas y acentos), mejor coincidencia primero.
  function buscarJuegos(q, juegos) {
    const lista = juegos || juegosDeFuente();
    const nq = normalizar(q).trim();
    if (nq.length < 2) return [];
    const conPrio = [];
    for (const j of lista) {
      const n = normalizar(j.name);
      let prio = -1;
      if (n === nq) prio = 0;
      else if (n.startsWith(nq)) prio = 1;
      else if (n.includes(nq)) prio = 2;
      else {
        // Palabras sueltas en cualquier orden (solo si la query tiene >1 palabra).
        const palabras = nq.split(/\s+/);
        if (palabras.length > 1 && palabras.every((p) => n.includes(p))) prio = 3;
      }
      if (prio >= 0) conPrio.push([prio, j]);
    }
    conPrio.sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name));
    return conPrio.map(([, j]) => j).slice(0, 10);
  }

  function juegosEnOtraFuente(q) {
    const otra = estado.source === "igdb" ? "rawg" : "igdb";
    const cands = estado.games.filter(
      (j) => j.source === otra && normalizar(j.name).includes(normalizar(q)),
    ).slice(0, 3);
    return { otra, cands };
  }

  function cerrarSugerencias() {
    const panel = $("sugerencias");
    panel.hidden = true;
    panel.innerHTML = "";
    $("buscador").setAttribute("aria-expanded", "false");
  }

  function pintarSugerencias() {
    const panel = $("sugerencias");
    const q = $("buscador").value.trim();
    if (normalizar(q).length < 2) {
      cerrarSugerencias();
      return;
    }
    const cands = buscarJuegos(q);
    let html = "";
    if (cands.length) {
      html = cands.map((j) => `
        <li role="option">
          <button type="button" class="sug-item" data-slug="${GS.esc(j.slug)}">
            <span>${GS.esc(j.name)}</span>
            <small>${j.year ?? "s/f"} · ${GS.esc(j.genres.slice(0, 2).join(" / ") || "s/g")}</small>
          </button>
        </li>`).join("");
    } else {
      const { otra, cands: enOtra } = juegosEnOtraFuente(q);
      html = enOtra.length
        ? `<li class="sug-info">Sin resultados en ${estado.source.toUpperCase()}.
             ¿Lo buscas en ${otra.toUpperCase()}?
             <button type="button" class="btn btn-sm" data-otra-fuente="${otra}">Cambiar fuente</button>
           </li>`
        : `<li class="sug-info">Sin resultados para “${GS.esc(q)}”. Prueba con menos letras.</li>`;
    }
    panel.innerHTML = html;
    panel.hidden = false;
    $("buscador").setAttribute("aria-expanded", "true");
    panel.querySelectorAll("[data-slug]").forEach((b) =>
      b.addEventListener("click", () => seleccionar(b.dataset.slug)));
    const otraBtn = panel.querySelector("[data-otra-fuente]");
    if (otraBtn) otraBtn.addEventListener("click", () => cambiarFuente(otraBtn.dataset.otraFuente, true));
  }

  // Opciones de filtro derivadas de los datos reales de la fuente activa.
  function refrescarFiltros() {
    const plats = new Set(), gens = new Set();
    for (const j of juegosDeFuente()) {
      j.platforms.forEach((p) => plats.add(p));
      j.genres.forEach((g) => gens.add(g));
    }
    const llenar = (id, valores, etiquetaTodas, actual) => {
      const sel = $(id);
      sel.innerHTML = `<option value="">${etiquetaTodas}</option>` +
        [...valores].sort((a, b) => a.localeCompare(b))
          .map((v) => `<option value="${GS.esc(v)}">${GS.esc(v)}</option>`).join("");
      sel.value = [...valores].includes(actual) ? actual : "";
      return sel.value;
    };
    estado.plataforma = llenar("filtro-plataforma", plats, "Todas las plataformas", estado.plataforma);
    estado.genero = llenar("filtro-genero", gens, "Todos los géneros", estado.genero);
  }

  // Selección = comparación inmediata (sin segundo botón).
  function seleccionar(slug) {
    const j = juegosDeFuente().find((x) => x.slug === slug);
    if (!j) return;
    estado.refSlug = slug;
    $("buscador").value = j.name;
    cerrarSugerencias();
    compararActual();
  }

  function cambiarFuente(source, mantenerConsulta) {
    estado.source = source;
    estado.refSlug = null;
    estado.plataforma = "";
    estado.genero = "";
    document.querySelectorAll("#fuente [data-source]").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.source === source)));
    refrescarFiltros();
    if (!mantenerConsulta) $("buscador").value = "";
    const q = $("buscador").value.trim();
    if (normalizar(q).length >= 2) {
      const cands = buscarJuegos(q);
      if (cands.length === 1) { seleccionar(cands[0].slug); return; }
      pintarSugerencias();
      $("resultados").innerHTML = GS.estadoVacio(`Fuente ${source.toUpperCase()}. Elige de la lista.`);
    } else {
      cerrarSugerencias();
      $("resultados").innerHTML = GS.estadoVacio("Fuente cambiada. Escribe el nombre de un juego.");
    }
  }

  // El botón y Enter eligen la mejor coincidencia (o abren la lista).
  function aceptarBusqueda() {
    const q = $("buscador").value.trim();
    if (!q) return;
    const cands = buscarJuegos(q);
    if (cands.length) {
      seleccionar(cands[0].slug);
      return;
    }
    pintarSugerencias();
  }

  // Los filtros restringen COMPETIDORES (el de referencia siempre se puede elegir).
  function pasaFiltros(j) {
    if (estado.plataforma && !j.platforms.includes(estado.plataforma)) return false;
    if (estado.genero && !j.genres.includes(estado.genero)) return false;
    return true;
  }

  function compararActual() {
    const resultados = $("resultados");
    const ref = juegosDeFuente().find((j) => j.slug === estado.refSlug);
    if (!ref) {
      resultados.innerHTML = GS.estadoVacio("Escribe un juego arriba y elige de la lista.");
      return;
    }
    const G = GS.canonGeneros(ref);
    const minNivel = RANGO[estado.tier];
    const scored = [];
    for (const j of juegosDeFuente()) {
      if (j.source_id === ref.source_id) continue;
      if (!pasaFiltros(j)) continue;
      const v = GS.puntuar(ref, j, G);
      if (RANGO[v.tier] >= minNivel) scored.push([v.nota, j, v]);
    }
    scored.sort((a, b) => b[0] - a[0]);
    const top = scored.slice(0, estado.top);
    const filtros = [];
    if (estado.plataforma) filtros.push(`plataforma=${estado.plataforma}`);
    if (estado.genero) filtros.push(`género=${estado.genero}`);
    const encabezado = `<h3>${scored.length} competidores (umbral: ${GS.esc(estado.tier)} o superior${filtros.length ? ` · filtros: ${GS.esc(filtros.join(" · "))}` : ""})</h3>`;
    const lista = top.length === 0
      ? GS.estadoVacio("Sin competidores con estos filtros. Prueba a bajar el umbral o a quitar filtros.")
      : `${encabezado}${GS.tablaComparativaHTML(ref, top)}${GS.insightsHTML(ref, scored, top)}
         <h3>Detalle y por qué</h3><ul class="comp-list">${top.map(([, j, v]) => GS.compHTML(j, v)).join("")}</ul>`;
    resultados.innerHTML = GS.refCardHTML(ref) + lista;
  }

  function pintarEvolucion() {
    const cont = $("evolucion-contenido");
    if (!cont) return;
    cont.innerHTML = GS.evolucionHTML(estado.evolucion);
  }

  function cablearEventos() {
    document.querySelectorAll("#fuente [data-source]").forEach((btn) =>
      btn.addEventListener("click", () => cambiarFuente(btn.dataset.source)));

    document.querySelectorAll("[data-ejemplo-slug]").forEach((btn) =>
      btn.addEventListener("click", () => {
        const { ejemploSlug, ejemploSource } = btn.dataset;
        if (estado.source !== ejemploSource) cambiarFuente(ejemploSource, true);
        seleccionar(ejemploSlug);
      }));

    $("form-comparar").addEventListener("submit", (e) => { e.preventDefault(); aceptarBusqueda(); });

    let temporizador = null;
    $("buscador").addEventListener("input", () => {
      clearTimeout(temporizador);
      temporizador = setTimeout(pintarSugerencias, 150);
    });
    $("buscador").addEventListener("keydown", (e) => {
      if (e.key === "Escape") { cerrarSugerencias(); return; }
      if (e.key === "ArrowDown") {
        const primero = $("sugerencias").querySelector(".sug-item");
        if (primero) { e.preventDefault(); primero.focus(); }
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        aceptarBusqueda();
      }
    });
    // Cerrar la lista al pulsar fuera.
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".search-wrap")) cerrarSugerencias();
    });

    $("tier").addEventListener("change", () => { estado.tier = $("tier").value; compararActual(); });
    $("topn").addEventListener("change", () => { estado.top = Number($("topn").value); compararActual(); });
    $("filtro-plataforma").addEventListener("change", () => {
      estado.plataforma = $("filtro-plataforma").value; compararActual();
    });
    $("filtro-genero").addEventListener("change", () => {
      estado.genero = $("filtro-genero").value; compararActual();
    });
  }

  async function iniciar() {
    const resultados = $("resultados");
    // Eventos cableados ANTES de pintar datos: los controles nunca quedan muertos.
    cablearEventos();
    resultados.innerHTML = GS.estadoCarga;
    let games, meta;
    try {
      ({ games, meta } = await GS.cargarDatos());
    } catch (e) {
      resultados.innerHTML = GS.estadoError(e.message);
      $("meta-linea").textContent = "No se pudieron cargar los datos del snapshot.";
      return;
    }
    estado.games = games;
    estado.evolucion = await GS.cargarEvolucion();
    $("meta-linea").textContent =
      `Snapshot ${meta.snapshot} · ${meta.n} juegos (${meta.por_fuente.igdb} IGDB + ${meta.por_fuente.rawg} RAWG) · scoring v1 · ${meta.n_snapshots} snapshot(s) capturado(s)`;
    refrescarFiltros();
    pintarEvolucion();
    // Demo inicial: comparación real visible sin tocar nada.
    const inicial = estado.games.find(
      (j) => j.slug === EJEMPLO_INICIAL.slug && j.source === EJEMPLO_INICIAL.source);
    if (inicial) seleccionar(inicial.slug);
    else resultados.innerHTML = GS.estadoVacio("Escribe un juego arriba y elige de la lista.");
  }

  // Solo arranca en navegador (en Node se cargan los scripts para test de lógica pura).
  if (typeof document !== "undefined") iniciar();

  Object.assign(GS, { estado, buscarJuegos, seleccionar, compararActual });
})(typeof window !== "undefined" ? window : globalThis);
