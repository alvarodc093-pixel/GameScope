// Renderizado: tarjetas, métricas con escala+n, lista de competidores y estados.
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function metricaHTML(etiqueta, m, clase) {
  if (m.score == null)
    return `<div class="metric"><div class="metric-top"><span>${etiqueta}</span><strong>sin dato</strong></div><small>Escala 0–${m.scale}</small></div>`;
  const pct = Math.max(0, Math.min(100, (m.score / m.scale) * 100));
  const n = m.count != null ? ` · n=${m.count}` : " · n no publicado";
  return `<div class="metric"><div class="metric-top"><span>${etiqueta}</span><strong>${m.score} / ${m.scale}${esc(n)}</strong></div><div class="bar ${clase}" role="img" aria-label="${etiqueta}: ${m.score} de ${m.scale}"><span style="width:${pct}%"></span></div></div>`;
}

export function refCardHTML(j) {
  const img = j.image_url
    ? `<img src="${esc(j.image_url)}" alt="Carátula de ${esc(j.name)}" loading="lazy" onerror="this.remove()">` : "";
  const tags = [...j.genres.slice(0, 4), ...j.platforms.slice(0, 4)]
    .map((t) => `<span class="tag">${esc(t)}</span>`).join("");
  const enlace = j.game_url ? `<a href="${esc(j.game_url)}" target="_blank" rel="noopener">Ficha en ${j.source === "igdb" ? "IGDB" : "RAWG"}</a>` : "";
  return `<article class="card ref-card" aria-label="Juego de referencia">
    <div class="ref-head">${img}<div><h3 style="margin:0">${esc(j.name)}</h3>
    <small style="color:var(--color-muted)">${j.source.toUpperCase()} · ${j.year ?? "año n/d"} · ${esc(j.grupo)}</small></div></div>
    <div class="tags">${tags}</div>
    <div class="metrics">${metricaHTML("Crítica", j.critic, "")}${metricaHTML("Usuarios", j.user, "user")}</div>
    <small style="color:var(--color-muted)">Crítica y usuarios son universos distintos: no se fusionan.</small>
    <div>${enlace}</div>
  </article>`;
}

export function compHTML(j, v) {
  const partes = v.partes.map((p) => `${p.comp}=${p.valor} (${esc(p.detalle)})`).join("; ");
  return `<li class="comp"><div class="comp-head"><span class="score">${v.nota.toFixed(3)}</span>
    <span class="badge ${v.tier}">${v.tier}</span><h3>${esc(j.name)}</h3></div>
    <p class="why">Por qué: ${esc(partes)} · Crítica ${j.critic.score ?? "n/d"} · Usuarios ${j.user.score ?? "n/d"}</p></li>`;
}

export const estadoCarga = `<div class="state" role="status"><div class="spinner" aria-hidden="true"></div>Cargando datos del snapshot…</div>`;
export const estadoError = (msg) =>
  `<div class="state error" role="alert">No se pudieron cargar los datos. ${esc(msg)} Reintenta más tarde.</div>`;
export const estadoVacio = (msg) => `<div class="state" role="status">${esc(msg)}</div>`;
