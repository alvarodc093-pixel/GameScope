// Regla de similitud v1 portada de src/scoring.py (mismos pesos y umbrales).
// Script clasico (sin modulos ES): funciona tambien abriendo index.html con doble clic.
(function (global) {
  "use strict";
  const PESOS = { genero: 3.0, plataforma: 2.0, era: 1.0, estudio: 1.0 };
  const UMBRALES = { directo: 0.75, secundario: 0.45, relacionado: 0.25 };
  const ERA_CERCA = 2;
  const ERA_ANCHA = 4;

  // Género RAWG (minúsculas) -> equivalentes IGDB.
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

  const norm = (s) => (s || "").toLowerCase();
  const canonGeneros = (juego) =>
    new Set(juego.genres.map((g) => (juego.source === "igdb" ? INVERSO[norm(g)] ?? norm(g) : norm(g))));

  function puntuar(ref, cand, G = null) {
    const gRef = G ?? canonGeneros(ref);
    const gCand = canonGeneros(cand);
    const pRef = new Set(ref.platforms.map(norm));
    const pCand = new Set(cand.platforms.map(norm));
    if (gRef.size === 0 || gCand.size === 0)
      return { tier: "insuficiente", nota: 0, partes: [], motivo: "género ausente" };
    const gCom = [...gRef].filter((g) => gCand.has(g));
    const pCom = [...pRef].filter((p) => pCand.has(p));
    if (gCom.length === 0) return { tier: "descartado", nota: 0, partes: [], motivo: "sin género común" };
    if (pCom.length === 0) return { tier: "descartado", nota: 0, partes: [], motivo: "sin plataforma común" };

    const partes = [
      { comp: "género", valor: gCom.length >= 2 ? 1.0 : 0.6, peso: PESOS.genero,
        detalle: `${gCom.length} en común: ${gCom.join("|")}` },
      { comp: "plataforma", valor: pCom.length >= 2 ? 1.0 : 0.5, peso: PESOS.plataforma,
        detalle: `${pCom.length} en común` },
    ];
    if (ref.year != null && cand.year != null) {
      const d = Math.abs(ref.year - cand.year);
      partes.push({ comp: "era", valor: d <= ERA_CERCA ? 1.0 : d <= ERA_ANCHA ? 0.5 : 0.0,
        peso: PESOS.era, detalle: `diferencia ${d} años` });
    } else {
      partes.push({ comp: "era", valor: 0.0, peso: PESOS.era, detalle: "fecha ausente: no suma" });
    }
    const dRef = new Set(ref.devs.map(norm));
    const dCand = new Set(cand.devs.map(norm));
    if (dRef.size > 0 && dCand.size > 0) {
      const mismo = [...dRef].some((d) => dCand.has(d));
      partes.push({ comp: "estudio", valor: mismo ? 1.0 : 0.0, peso: PESOS.estudio,
        detalle: mismo ? "mismo estudio" : "distinto estudio" });
    }
    const num = partes.reduce((s, p) => s + p.valor * p.peso, 0);
    const den = partes.reduce((s, p) => s + p.peso, 0);
    const nota = Math.round((num / den) * 1000) / 1000;
    const tier = nota >= UMBRALES.directo ? "directo"
      : nota >= UMBRALES.secundario ? "secundario"
      : nota >= UMBRALES.relacionado ? "relacionado" : "descartado";
    return { tier, nota, partes, motivo: "" };
  }

  global.GS = global.GS || {};
  Object.assign(global.GS, { PESOS, UMBRALES, MAPEO, puntuar, canonGeneros });
})(typeof window !== "undefined" ? window : globalThis);
