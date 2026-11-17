// Scoring de competidores v2: réplica de src/scoring.py (mismos pesos, umbrales,
// rareza de géneros y modo estricto). tests/test_paridad_js.py comprueba que
// ambas versiones dan la misma nota y el mismo tier.
// Script clasico (sin modulos ES): funciona tambien abriendo index.html con doble clic.
(function (global) {
  "use strict";
  const PESOS = { genero: 3.0, plataforma: 2.0, era: 1.0, estudio: 1.0 };
  const UMBRALES = { directo: 0.75, secundario: 0.60, relacionado: 0.40 };
  const ERA_CERCA = 2;
  const ERA_ANCHA = 4;

  // Género RAWG (minúsculas) -> equivalentes IGDB (src/datos.py: MAPEO).
  const MAPEO = {
    action: ["adventure"], adventure: ["adventure"], shooter: ["shooter"],
    "rpg": ["role-playing (rpg)"], indie: ["indie"], platformer: ["platform"],
    puzzle: ["puzzle"], racing: ["racing"], sports: ["sport"],
    simulation: ["simulator"],
    strategy: ["strategy", "turn-based strategy (tbs)", "tactical", "real time strategy (rts)"],
    arcade: ["arcade"], fighting: ["fighting"], family: ["family"],
    "massively multiplayer": [], casual: [],
  };
  const INVERSO = {};
  for (const [k, vs] of Object.entries(MAPEO)) {
    for (const v of vs) INVERSO[v] ??= k;
  }

  const norm = (s) => (s || "").trim().toLowerCase();
  const redondear3 = (x) => Math.round(x * 1000) / 1000;
  const canonGeneros = (juego) =>
    new Set(juego.genres.map((g) => (juego.source === "igdb" ? INVERSO[norm(g)] ?? norm(g) : norm(g))));

  // Rareza de cada género por fuente: log(N / juegos con ese género).
  function idfGeneros(juegos) {
    const out = {};
    for (const src of new Set(juegos.map((j) => j.source))) {
      const sub = juegos.filter((j) => j.source === src);
      const df = new Map();
      for (const j of sub) for (const g of canonGeneros(j)) df.set(g, (df.get(g) || 0) + 1);
      out[src] = {};
      for (const [g, n] of df) out[src][g] = Math.log(sub.length / n);
    }
    return out;
  }

  // Jaccard ponderado por rareza; un género fuera de la tabla pesa 1.
  function similitudGenero(gRef, gCand, pesosG) {
    const peso = (g) => (pesosG && g in pesosG ? pesosG[g] : 1.0);
    const union = new Set([...gRef, ...gCand]);
    let den = 0, num = 0;
    for (const g of union) {
      den += peso(g);
      if (gRef.has(g) && gCand.has(g)) num += peso(g);
    }
    return den ? num / den : 0.0;
  }

  const veredicto = (tier, motivo) => ({ tier, nota: 0, partes: [], motivo });

  function puntuar(ref, cand, G = null, estricto = false, idf = null) {
    const gRef = G ?? canonGeneros(ref);
    const gCand = canonGeneros(cand);
    if (gRef.size === 0 || gCand.size === 0) return veredicto("insuficiente", "género ausente en una parte");
    const gCom = [...gRef].filter((g) => gCand.has(g)).sort();
    const pCand = new Set(cand.platforms.map(norm));
    const pCom = [...new Set(ref.platforms.map(norm))].filter((p) => pCand.has(p));
    if (gCom.length === 0) return veredicto("descartado", "sin género común");
    if (pCom.length === 0) return veredicto("descartado", "sin plataforma común");
    if (estricto) {
      if (ref.year == null || cand.year == null) return veredicto("insuficiente", "fecha ausente en modo estricto");
      if (gCom.length < 2) return veredicto("descartado", "solo 1 género en común (mínimo 2 en estricto)");
    }

    const partes = [
      { comp: "género", valor: redondear3(similitudGenero(gRef, gCand, idf && idf[ref.source])),
        peso: PESOS.genero, detalle: `${gCom.length} en común: ${gCom.join("|")}` },
      { comp: "plataforma", valor: pCom.length >= 2 ? 1.0 : 0.5, peso: PESOS.plataforma,
        detalle: `${pCom.length} en común` },
    ];
    if (ref.year != null && cand.year != null) {
      const d = Math.abs(ref.year - cand.year);
      partes.push({ comp: "era", valor: d <= ERA_CERCA ? 1.0 : d <= ERA_ANCHA ? 0.5 : 0.0,
        peso: PESOS.era, detalle: `diferencia ${d} años` });
    } else {
      partes.push({ comp: "era", valor: 0.0, peso: PESOS.era, detalle: "fecha ausente" });
    }
    const dRef = new Set(ref.devs.map(norm).filter(Boolean));
    const dCand = new Set(cand.devs.map(norm).filter(Boolean));
    if (dRef.size > 0 && dCand.size > 0) {
      const mismo = [...dRef].some((d) => dCand.has(d));
      partes.push({ comp: "estudio", valor: mismo ? 1.0 : 0.0, peso: PESOS.estudio,
        detalle: mismo ? "mismo estudio" : "distinto estudio" });
    }
    const num = partes.reduce((s, p) => s + p.valor * p.peso, 0);
    const den = partes.reduce((s, p) => s + p.peso, 0);
    const nota = redondear3(num / den);
    const tier = nota >= UMBRALES.directo ? "directo"
      : nota >= UMBRALES.secundario ? "secundario"
      : nota >= UMBRALES.relacionado ? "relacionado" : "descartado";
    return { tier, nota, partes, motivo: "" };
  }

  // Nota descendente; en empate, más votos de usuarios y luego nombre (como en Python).
  function compararCompetidores([notaA, a], [notaB, b]) {
    return notaB - notaA
      || ((b.user && b.user.count) || 0) - ((a.user && a.user.count) || 0)
      || (a.name || "").toLowerCase().localeCompare((b.name || "").toLowerCase());
  }

  global.GS = global.GS || {};
  Object.assign(global.GS, {
    PESOS, UMBRALES, MAPEO, puntuar, canonGeneros, idfGeneros, similitudGenero, compararCompetidores,
  });
})(typeof window !== "undefined" ? window : globalThis);
