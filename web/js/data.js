// Carga de datos estáticos generados por src/export_web.py.
export async function cargarDatos() {
  const [games, meta] = await Promise.all([
    fetch("data/games.json").then((r) => {
      if (!r.ok) throw new Error(`games.json: HTTP ${r.status}`);
      return r.json();
    }),
    fetch("data/meta.json").then((r) => {
      if (!r.ok) throw new Error(`meta.json: HTTP ${r.status}`);
      return r.json();
    }),
  ]);
  return { games, meta };
}
