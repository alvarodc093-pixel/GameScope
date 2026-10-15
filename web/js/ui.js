// Renderizado: tarjetas, metricas con escala+n, tabla comparativa, insights,
// evolucion y estados. Script clasico; todo dato insertado pasa por esc().
(function (global) {
  "use strict";
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const fmt = (v, dec = 1) => {
    if (v == null || Number.isNaN(v)) return "n/d";
    return Number.isInteger(v) ? String(v) : v.toFixed(dec);
  };
  const fmtDelta = (d) => {
    if (d == null || Number.isNaN(d)) return "n/d";
    const s = d > 0 ? "+" : "";
    return `${s}${fmt(d, 2)}`;
  };
  const claseDelta = (d) => (d == null || Number.isNaN(d) || d === 0 ? "neu" : d > 0 ? "pos" : "neg");
  const mediana = (xs) => {
    if (!xs.length) return null;
    const s = [...xs].sort((a, b) => a - b);
    const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  };

  function metricaHTML(etiqueta, m, clase) {
    if (m.score == null)
      return `<div class="metric"><div class="metric-top"><span>${etiqueta}</span><strong>sin dato</strong></div><small>Escala 0–${m.scale}</small></div>`;
    const pct = Math.max(0, Math.min(100, (m.score / m.scale) * 100));
    const n = m.count != null ? ` · n=${m.count}` : " · n no publicado";
    return `<div class="metric"><div class="metric-top"><span>${etiqueta}</span><strong>${m.score} / ${m.scale}${esc(n)}</strong></div><div class="bar ${clase}" role="img" aria-label="${etiqueta}: ${m.score} de ${m.scale}"><span style="width:${pct}%"></span></div></div>`;
  }

  function refCardHTML(j) {
    const img = j.image_url
      ? `<img src="${esc(j.image_url)}" alt="Carátula de ${esc(j.name)}" loading="lazy" onerror="this.remove()">` : "";
    const tags = [...j.genres.slice(0, 4), ...j.platforms.slice(0, 4)]
      .map((t) => `<span class="tag">${esc(t)}</span>`).join("");
    const enlace = j.game_url ? `<a href="${esc(j.game_url)}" target="_blank" rel="noopener">Ficha en ${j.source === "igdb" ? "IGDB" : "RAWG"}</a>` : "";
    const cp = cpHTML(j);
    const precio = j.precio_pc
      ? `<small class="precio-linea">Precio PC mínimo: <strong>${esc(String(j.precio_pc.usd))} USD</strong> · ${esc(j.precio_pc.fuente)} · observado ${esc((j.precio_pc.observed_at || "").slice(0, 10))} (sin convertir)</small>`
      : "";
    return `<article class="card ref-card" aria-label="Juego de referencia">
      <div class="ref-head">${img}<div><h3 style="margin:0">${esc(j.name)}</h3>
      <small style="color:var(--color-muted)">${esc(j.source.toUpperCase())} · ${j.year ?? "año n/d"} · ${esc(j.grupo)}</small></div></div>
      <div class="tags">${tags}</div>
      <div class="metrics">${metricaHTML("Crítica", j.critic, "")}${metricaHTML("Usuarios", j.user, "user")}</div>
      <small style="color:var(--color-muted)">Crítica y usuarios son universos distintos: no se fusionan.</small>
      ${precio}
      <div class="ref-links">${enlace}${cp}</div>
    </article>`;
  }

  // Enlace a la otra fuente (identidad derivada en src/matching.py): cambia de
  // fuente y selecciona el mismo juego. Nunca muestra metricas cruzadas aqui.
  function cpHTML(j) {
    if (!j.contraparte || !j.contraparte.slug) return "";
    const otra = j.contraparte.source === "igdb" ? "IGDB" : "RAWG";
    const conf = j.contraparte.confianza ? ` (${esc(j.contraparte.confianza)})` : "";
    return `<button type="button" class="chip" data-ir-contraparte="${esc(j.contraparte.slug)}"
      data-ir-fuente="${esc(j.contraparte.source)}"
      title="Identidad derivada: mismo juego en la otra fuente. Las métricas se muestran en su propia escala.">↔ También en ${otra}${conf}</button>`;
  }

  function compHTML(j, v) {
    const partes = v.partes.map((p) => `${p.comp}=${p.valor} (${esc(p.detalle)})`).join("; ");
    const porque = partes
      ? `Por qué: ${esc(partes)}`
      : v.motivo ? `Descartado: ${esc(v.motivo)}` : "Sin detalle";
    return `<li class="comp"><div class="comp-head"><span class="score">${v.nota.toFixed(3)}</span>
      <span class="badge ${v.tier}">${v.tier}</span><h3>${esc(j.name)}</h3>${cpHTML(j)}</div>
      <p class="why">${porque} · Crítica ${j.critic.score ?? "n/d"} · Usuarios ${j.user.score ?? "n/d"}</p></li>`;
  }

  // Tabla lado a lado ref vs competidores (misma fuente => misma escala: deltas válidos).
  function tablaComparativaHTML(ref, top) {
    const fila = (j, v, esRef) => {
      const dC = esRef || ref.critic.score == null || j.critic.score == null
        ? null : j.critic.score - ref.critic.score;
      const dU = esRef || ref.user.score == null || j.user.score == null
        ? null : j.user.score - ref.user.score;
      const dY = esRef || ref.year == null || j.year == null ? null : j.year - ref.year;
      const sim = esRef ? "—" : v.nota.toFixed(3);
      return `<tr class="${esRef ? "fila-ref" : ""}">
        <td>${esc(j.name)}${esRef ? ' <span class="badge directo">ref</span>' : ""}</td>
        <td class="num">${sim}</td>
        <td class="num">${fmt(j.critic.score)} / ${j.critic.scale}${j.critic.count != null ? ` <small>n=${j.critic.count}</small>` : ""}</td>
        <td class="num delta ${claseDelta(dC)}">${dC == null ? "—" : `${fmtDelta(dC)} (${fmtDelta((dC / ref.critic.score) * 100)}%)`}</td>
        <td class="num">${fmt(j.user.score)} / ${j.user.scale}${j.user.count != null ? ` <small>n=${j.user.count}</small>` : ""}</td>
        <td class="num delta ${claseDelta(dU)}">${dU == null ? "—" : fmtDelta(dU)}</td>
        <td class="num">${j.year ?? "—"}</td>
        <td class="num delta ${claseDelta(dY)}">${dY == null ? "—" : fmtDelta(dY)}</td>
      </tr>`;
    };
    return `<div class="table-wrap"><table class="data-table tabla-comparativa">
      <caption>Comparación lado a lado (misma fuente y escala; delta = competidor − referencia)</caption>
      <thead><tr><th>Juego</th><th>Similitud</th><th>Crítica</th><th>Δ crítica</th>
      <th>Usuarios</th><th>Δ usuarios</th><th>Año</th><th>Δ años</th></tr></thead>
      <tbody>${fila(ref, null, true)}${top.map(([, j, v]) => fila(j, v, false)).join("")}</tbody>
    </table></div>`;
  }

  // Conclusiones de negocio respaldadas por los datos mostrados (sin inventar ventas).
  function insightsHTML(ref, scored, top) {
    const conCritic = scored.filter(([, j]) => j.critic.score != null);
    const conUser = scored.filter(([, j]) => j.user.score != null);
    const nDirectos = scored.filter(([, , v]) => v.tier === "directo").length;
    const nSec = scored.filter(([, , v]) => v.tier === "secundario").length;

    const lineas = [];
    lineas.push(`Grupo comparable (umbral alcanzado): <strong>${scored.length}</strong> competidores — ${nDirectos} directos y ${nSec} secundarios. La lista muestra los ${top.length} más similares.`);

    if (ref.critic.score != null && conCritic.length >= 3) {
      const med = mediana(conCritic.map(([, j]) => j.critic.score));
      const d = ref.critic.score - med;
      const pct = med ? (d / med) * 100 : null;
      const mayores = conCritic.filter(([, j]) => j.critic.score > ref.critic.score).length;
      lineas.push(`Crítica (misma escala 0–${ref.critic.scale}): la referencia puntúa <strong>${fmt(ref.critic.score)}</strong> frente a una mediana de <strong>${fmt(med)}</strong> del grupo (${fmtDelta(d)}${pct != null ? `, ${fmtDelta(pct)}%` : ""}). ${mayores} de ${conCritic.length} competidores con dato la superan.`);
    } else {
      lineas.push(`Crítica: la referencia ${ref.critic.score == null ? "no tiene dato" : "tiene dato"}, pero el grupo comparable tiene menos de 3 valores: no se calcula mediana (se evitan conclusiones con n bajo).`);
    }
    if (ref.user.score != null && conUser.length >= 3) {
      const med = mediana(conUser.map(([, j]) => j.user.score));
      const d = ref.user.score - med;
      const mayores = conUser.filter(([, j]) => j.user.score > ref.user.score).length;
      lineas.push(`Usuarios (escala propia 0–${ref.user.scale}, n por título): la referencia <strong>${fmt(ref.user.score, 2)}</strong> vs mediana <strong>${fmt(med, 2)}</strong> (${fmtDelta(d)}). ${mayores} de ${conUser.length} competidores la superan.`);
    } else {
      lineas.push(`Usuarios: datos insuficientes en el grupo comparable para comparar con la referencia.`);
    }
    if (top.length) {
      const conDatos = top.filter(([, j]) => j.critic.score != null);
      if (conDatos.length) {
        const mejor = conDatos.reduce((a, b) => (b[1].critic.score > a[1].critic.score ? b : a));
        const peor = conDatos.reduce((a, b) => (b[1].critic.score < a[1].critic.score ? b : a));
        lineas.push(`Rango de crítica del top mostrado: de <strong>${esc(peor[1].name)}</strong> (${fmt(peor[1].critic.score)}) a <strong>${esc(mejor[1].name)}</strong> (${fmt(mejor[1].critic.score)}).`);
      }
    }
    const caveats = [];
    if (ref.critic.count != null && ref.critic.count < 5)
      caveats.push(`La crítica de la referencia tiene n=${ref.critic.count} (<5): valor orientativo.`);
    caveats.push("Las puntuaciones y el volumen de votos NO son ventas ni usuarios activos: no hay fuente de negocio en el dataset.");
    caveats.push("Comparaciones solo dentro de la misma fuente: IGDB y RAWG calculan distinto y sus escalas no se fusionan.");

    return `<div class="card insights" aria-label="Resumen de diferencias">
      <h3>Resumen de diferencias</h3>
      <ul>${lineas.map((l) => `<li>${l}</li>`).join("")}</ul>
      <p class="why">${caveats.map(esc).join(" · ")}</p>
    </div>`;
  }

  function evolucionHTML(evo) {
    if (!evo || !evo.suficientes_observaciones) {
      const msg = (evo && evo.mensaje) ||
        "Todavía no hay suficientes observaciones fechadas para calcular evolución.";
      return `<div class="state" role="status">${esc(msg)}</div>`;
    }
    const filas = evo.cambios.slice(0, 15).map((f) => {
      const c = f.metricas.critic_score, u = f.metricas.user_score;
      return `<tr>
        <td>${esc(f.name)} <small style="color:var(--color-muted)">${esc(f.source)}</small></td>
        <td class="num delta ${claseDelta(c.delta)}">${fmt(c.antes)} → ${fmt(c.ahora)} (${fmtDelta(c.delta)})</td>
        <td class="num delta ${claseDelta(u.delta)}">${fmt(u.antes, 2)} → ${fmt(u.ahora, 2)} (${fmtDelta(u.delta)})</td>
      </tr>`;
    }).join("");
    return `<div class="card">
      <p class="why">Entre <code>${esc(evo.entre.anterior)}</code> y <code>${esc(evo.entre.actual)}</code>:
      ${evo.con_cambio} juego(s) con cambio de métrica · ${evo.altas.length} alta(s) · ${evo.bajas.length} baja(s)
      en el snapshot${evo.cambios.length > 15 ? ` · se muestran 15 de ${evo.cambios.length}` : ""}.</p>
      <div class="table-wrap"><table class="data-table">
        <thead><tr><th>Juego</th><th>Crítica (antes → ahora)</th><th>Usuarios (antes → ahora)</th></tr></thead>
        <tbody>${filas || '<tr><td colspan="3">Sin cambios de métricas entre ambas fotos.</td></tr>'}</tbody>
      </table></div>
      <p class="why">Solo se comparan métricas observadas en ambas fechas (intra-fuente). Un campo ausente queda como n/d: no se rellena con datos actuales.</p>
    </div>`;
  }

  const estadoCarga = `<div class="state" role="status"><div class="spinner" aria-hidden="true"></div>Cargando datos del snapshot…</div>`;
  const estadoError = (msg) =>
    `<div class="state error" role="alert">No se pudieron cargar los datos. ${esc(msg)} Reintenta más tarde.</div>`;
  const estadoVacio = (msg) => `<div class="state" role="status">${esc(msg)}</div>`;

  global.GS = global.GS || {};
  Object.assign(global.GS, {
    esc, refCardHTML, compHTML, tablaComparativaHTML, insightsHTML, evolucionHTML,
    estadoCarga, estadoError, estadoVacio,
  });
})(typeof window !== "undefined" ? window : globalThis);
