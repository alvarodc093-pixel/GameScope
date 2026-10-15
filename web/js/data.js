// Carga de datos: lee window.GS_DATOS (generado por src/export_web.py como
// data/datos.js). Un script clasico funciona tambien en file:// (doble clic);
// fetch() de JSON no, por eso los datos viajan como script y no como JSON.
(function (global) {
  "use strict";
  function cargarDatos() {
    const d = global.GS_DATOS;
    if (!d || !Array.isArray(d.games) || !d.meta) {
      return Promise.reject(new Error(
        "Falta web/data/datos.js. Regenera los datos: python -m src.export_web (requiere un snapshot previo: python -m src.snapshot).",
      ));
    }
    return Promise.resolve({ games: d.games, meta: d.meta });
  }
  function cargarEvolucion() {
    const d = global.GS_DATOS;
    if (!d || !d.evolucion) return Promise.resolve(null);
    return Promise.resolve(d.evolucion);
  }
  global.GS = global.GS || {};
  Object.assign(global.GS, { cargarDatos, cargarEvolucion });
})(typeof window !== "undefined" ? window : globalThis);
