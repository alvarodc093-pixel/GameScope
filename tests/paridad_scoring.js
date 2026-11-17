// Lado JavaScript del test de paridad (tests/test_paridad_js.py).
// Entrada por stdin: {"games": [...], "pares": [[iRef, iCand, estricto], ...]}
// Salida por stdout: {"idf": {...}, "resultados": [{"tier", "nota"}, ...]}
"use strict";
const path = require("path");

require(path.join(__dirname, "..", "web", "js", "scoring.js"));
const GS = globalThis.GS;

let entrada = "";
process.stdin.on("data", (c) => { entrada += c; });
process.stdin.on("end", () => {
  const { games, pares } = JSON.parse(entrada);
  const idf = GS.idfGeneros(games);
  const resultados = pares.map(([i, j, estricto]) => {
    const v = GS.puntuar(games[i], games[j], null, estricto, idf);
    return { tier: v.tier, nota: v.nota };
  });
  process.stdout.write(JSON.stringify({ idf, resultados }));
});
