// Estado y cableado del comparador.
import { cargarDatos } from "./data.js";
import { puntuar, canonGeneros } from "./scoring.js";
import {
  refCardHTML, compHTML, tablaComparativaHTML, insightsHTML, evolucionHTML,
  estadoCarga, estadoError, estadoVacio, esc,
} from "./ui.js";

const $ = (id) => document.getElementById(id);
const estado = {
  games: [], source: "igdb", tier: "secundario", top: 10, refSlug: null,
  plataforma: "", genero: "", evolucion: null,
};

const RANGO = { directo: 3, secundario: 2, relacionado: 1, descartado: 0, insuficiente: -1 };

function juegosDeFuente() {
  return estado.games.filter((j) => j.source === estado.source);
}

function refrescarLista() {
  $("juego-lista").innerHTML = juegosDeFuente()
    .map((j) => `<option value="${esc(j.name)}">`).join("");
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
        .map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join("");
    sel.value = [...valores].includes(actual) ? actual : "";
    return sel.value;
  };
  estado.plataforma = llenar("filtro-plataforma", plats, "Todas las plataformas", estado.plataforma);
  estado.genero = llenar("filtro-genero", gens, "Todos los géneros", estado.genero);
}

function seleccionar(slug) {
  estado.refSlug = slug;
  const j = juegosDeFuente().find((x) => x.slug === slug);
  if (j) $("buscador").value = j.name;
  compararActual();
}

function buscar() {
  const q = $("buscador").value.trim().toLowerCase();
  const resultados = $("resultados");
  if (!q) {
    resultados.innerHTML = estadoVacio("Escribe al menos 3 letras del juego.");
    return;
  }
  const exactos = juegosDeFuente().filter((j) => j.name.toLowerCase() === q);
  if (exactos.length === 1) {
    seleccionar(exactos[0].slug);
    return;
  }
  const cand = juegosDeFuente().filter((j) => j.name.toLowerCase().includes(q)).slice(0, 12);
  if (cand.length === 0) {
    resultados.innerHTML = estadoVacio(`Sin resultados para "${$("buscador").value.trim()}". Prueba con otro nombre o cambia de fuente (IGDB/RAWG).`);
    return;
  }
  resultados.innerHTML = `<h3>${cand.length} coincidencias: elige una</h3><ul class="comp-list">` +
    cand.map((j) => `<li class="comp"><div class="comp-head"><h3>${esc(j.name)}</h3>
      <small style="color:var(--color-muted)">${j.year ?? "?"} · ${esc(j.genres.slice(0, 2).join(" / "))}</small>
      <button type="button" class="btn" data-slug="${esc(j.slug)}">Comparar</button></div></li>`).join("") + "</ul>";
  resultados.querySelectorAll("[data-slug]").forEach((b) =>
    b.addEventListener("click", () => seleccionar(b.dataset.slug)));
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
    resultados.innerHTML = estadoVacio("Selecciona primero un juego de referencia.");
    return;
  }
  const G = canonGeneros(ref);
  const minNivel = RANGO[estado.tier];
  const scored = [];
  for (const j of juegosDeFuente()) {
    if (j.source_id === ref.source_id) continue;
    if (!pasaFiltros(j)) continue;
    const v = puntuar(ref, j, G);
    if (RANGO[v.tier] >= minNivel) scored.push([v.nota, j, v]);
  }
  scored.sort((a, b) => b[0] - a[0]);
  const top = scored.slice(0, estado.top);
  const filtros = [];
  if (estado.plataforma) filtros.push(`plataforma=${estado.plataforma}`);
  if (estado.genero) filtros.push(`género=${estado.genero}`);
  const encabezado = `<h3>${scored.length} competidores (umbral: ${esc(estado.tier)} o superior${filtros.length ? ` · filtros: ${esc(filtros.join(" · "))}` : ""})</h3>`;
  const lista = top.length === 0
    ? estadoVacio("Sin competidores con estos filtros. Prueba a bajar el umbral o a quitar filtros.")
    : `${encabezado}${tablaComparativaHTML(ref, top)}${insightsHTML(ref, scored, top)}
       <h3>Detalle y por qué</h3><ul class="comp-list">${top.map(([, j, v]) => compHTML(j, v)).join("")}</ul>`;
  resultados.innerHTML = refCardHTML(ref) + lista;
}

function pintarEvolucion() {
  const cont = $("evolucion-contenido");
  if (!cont) return;
  cont.innerHTML = evolucionHTML(estado.evolucion);
}

async function cargarEvolucion() {
  try {
    const r = await fetch("data/evolucion.json");
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    estado.evolucion = await r.json();
  } catch {
    estado.evolucion = {
      suficientes_observaciones: false,
      mensaje: "No se pudo cargar evolucion.json. Regenera los datos con: python -m src.export_web.",
    };
  }
  pintarEvolucion();
}

async function iniciar() {
  const resultados = $("resultados");
  if (window.location.protocol === "file:") {
    resultados.innerHTML = estadoError("La web está abierta como fichero. Sirve la carpeta web/ con un servidor local: python -m http.server desde web/ y abre http://localhost:8000.");
    return;
  }
  resultados.innerHTML = estadoCarga;
  try {
    const { games, meta } = await cargarDatos();
    estado.games = games;
    $("meta-linea").textContent =
      `Snapshot ${meta.snapshot} · ${meta.n} juegos (${meta.por_fuente.igdb} IGDB + ${meta.por_fuente.rawg} RAWG) · scoring v1 · ${meta.n_snapshots} snapshot(s) capturado(s)`;
  } catch (e) {
    resultados.innerHTML = estadoError(e.message);
    return;
  }
  refrescarLista();
  refrescarFiltros();
  cargarEvolucion();
  resultados.innerHTML = estadoVacio("Busca un juego y pulsa Comparar.");
  document.querySelectorAll("#fuente [data-source]").forEach((btn) => {
    btn.addEventListener("click", () => {
      estado.source = btn.dataset.source;
      estado.refSlug = null;
      estado.plataforma = "";
      estado.genero = "";
      $("buscador").value = "";
      document.querySelectorAll("#fuente [data-source]").forEach((b) =>
        b.setAttribute("aria-pressed", String(b === btn)));
      refrescarLista();
      refrescarFiltros();
      resultados.innerHTML = estadoVacio("Fuente cambiada. Busca un juego y pulsa Comparar.");
    });
  });
  $("form-comparar").addEventListener("submit", (e) => { e.preventDefault(); buscar(); });
  let temporizador = null;
  $("buscador").addEventListener("input", () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => {
      if ($("buscador").value.trim().length >= 2) buscar();
    }, 300);
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

iniciar();
export { buscar, seleccionar, compararActual, estado };
