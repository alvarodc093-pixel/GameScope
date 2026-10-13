// Estado y cableado del comparador.
import { cargarDatos } from "./data.js";
import { puntuar, canonGeneros } from "./scoring.js";
import { refCardHTML, compHTML, estadoCarga, estadoError, estadoVacio } from "./ui.js";

const $ = (id) => document.getElementById(id);
const estado = { games: [], source: "igdb", tier: "secundario", top: 10, refSlug: null };

const RANGO = { directo: 3, secundario: 2, relacionado: 1, descartado: 0, insuficiente: -1 };

function juegosDeFuente() {
  return estado.games.filter((j) => j.source === estado.source);
}

function refrescarLista() {
  $("juego-lista").innerHTML = juegosDeFuente()
    .map((j) => `<option value="${j.name}">`).join("");
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
    cand.map((j) => `<li class="comp"><div class="comp-head"><h3>${j.name}</h3>
      <small style="color:var(--color-muted)">${j.year ?? "?"} · ${j.genres.slice(0, 2).join(" / ")}</small>
      <button type="button" class="btn" data-slug="${j.slug}">Comparar</button></div></li>`).join("") + "</ul>";
  resultados.querySelectorAll("[data-slug]").forEach((b) =>
    b.addEventListener("click", () => seleccionar(b.dataset.slug)));
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
    const v = puntuar(ref, j, G);
    if (RANGO[v.tier] >= minNivel) scored.push([v.nota, j, v]);
  }
  scored.sort((a, b) => b[0] - a[0]);
  const top = scored.slice(0, estado.top);
  resultados.innerHTML = refCardHTML(ref) +
    (top.length === 0
      ? estadoVacio("Sin competidores en este nivel. Prueba con un umbral más bajo.")
      : `<h3>${top.length} competidores (umbral: ${estado.tier} o superior)</h3><ul class="comp-list">${top.map(([, j, v]) => compHTML(j, v)).join("")}</ul>`);
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
      `Snapshot ${meta.snapshot} · ${meta.n} juegos (${meta.por_fuente.igdb} IGDB + ${meta.por_fuente.rawg} RAWG) · scoring v1`;
  } catch (e) {
    resultados.innerHTML = estadoError(e.message);
    return;
  }
  refrescarLista();
  resultados.innerHTML = estadoVacio("Busca un juego y pulsa Comparar.");
  document.querySelectorAll("#fuente [data-source]").forEach((btn) => {
    btn.addEventListener("click", () => {
      estado.source = btn.dataset.source;
      estado.refSlug = null;
      $("buscador").value = "";
      document.querySelectorAll("#fuente [data-source]").forEach((b) =>
        b.setAttribute("aria-pressed", String(b === btn)));
      refrescarLista();
      resultados.innerHTML = estadoVacio("Fuente cambiada. Busca un juego y pulsa Comparar.");
    });
  });
  $("form-comparar").addEventListener("submit", (e) => { e.preventDefault(); buscar(); });
  $("tier").addEventListener("change", () => { estado.tier = $("tier").value; compararActual(); });
  $("topn").addEventListener("change", () => { estado.top = Number($("topn").value); compararActual(); });
}

iniciar();
export { buscar, seleccionar, compararActual, estado };
