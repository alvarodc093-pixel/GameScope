"""Paridad del scoring entre src/scoring.py y web/js/scoring.js.

La web puntúa en el navegador con la réplica en JavaScript; si las dos versiones
se separan, la web y la CLI dan competidores distintos. Requiere Node (lo trae
el runner de GitHub Actions); sin Node el test se salta.
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import datos, export_web, scoring

NODE = shutil.which("node")
SCRIPT = ROOT / "tests" / "paridad_scoring.js"


def fila(source, source_id, genres, platforms, fecha="2015-06-01", devs=""):
    return {"source": source, "source_id": source_id, "slug": f"j{source_id}",
            "name": f"Juego {source_id}", "genre_names": genres, "platform_names": platforms,
            "release_date": fecha, "developer_names": devs}


# Casos elegidos para tocar cada rama: géneros mapeados de IGDB, Xbox Series X|S,
# fecha ausente, estudio en una sola parte, sin plataforma común y RAWG sin estudios.
FILAS = [
    fila("igdb", "1", "Platform|Adventure|Indie", "PC (Microsoft Windows)|Nintendo Switch", "2017-02-24", "Team Cherry"),
    fila("igdb", "2", "Platform|Adventure|Indie", "PC (Microsoft Windows)|Nintendo Switch|Xbox Series X|S", "2018-01-25", "Maddy Makes Games"),
    fila("igdb", "3", "Adventure|Visual Novel|Indie", "PC (Microsoft Windows)|Xbox Series X|S", "2016-05-01"),
    fila("igdb", "4", "Adventure|Shooter", "Xbox Series X|S|PlayStation 5", "", "Estudio A"),
    fila("igdb", "5", "Role-playing (RPG)|Adventure", "PlayStation 5|PC (Microsoft Windows)", "2020-11-10", "Estudio A"),
    fila("igdb", "6", "Turn-based strategy (TBS)|Tactical", "PC (Microsoft Windows)", "2012-10-09"),
    fila("igdb", "7", "Adventure", "Android", "2019-03-01"),
    fila("rawg", "10", "Action|Shooter", "PC|PlayStation 4|Xbox One", "2013-03-26"),
    fila("rawg", "11", "Action|Shooter", "PC|Xbox One", "2012-11-13"),
    fila("rawg", "12", "Action|RPG|Adventure", "PC|PlayStation 4", "2015-05-18"),
    fila("rawg", "13", "Action", "PC", ""),
    fila("rawg", "14", "Puzzle|Indie", "iOS|Android", "2014-01-01"),
]


def pares_misma_fuente(rows, refs=None):
    refs = range(len(rows)) if refs is None else refs
    return [[i, j, estricto] for i in refs for j in range(len(rows))
            if i != j and rows[i]["source"] == rows[j]["source"] for estricto in (False, True)]


@unittest.skipUnless(NODE, "Node no está instalado")
class TestParidadJS(unittest.TestCase):
    def comprobar(self, rows, pares):
        for r in rows:
            r["_g"] = datos.generos_canonicos(r["source"], r["genre_names"])
        idf = scoring.idf_generos(rows)
        games = [export_web.juego_desde_fila(r) for r in rows]
        out = subprocess.run([NODE, str(SCRIPT)], input=json.dumps({"games": games, "pares": pares}),
                             capture_output=True, text=True, encoding="utf-8", check=True)
        js = json.loads(out.stdout)
        for src, tabla in idf.items():
            for g, w in tabla.items():
                self.assertAlmostEqual(js["idf"][src][g], w, places=12, msg=f"idf {src}/{g}")
        for (i, j, estricto), r_js in zip(pares, js["resultados"]):
            v = scoring.puntuar(rows[i], rows[j], estricto=estricto, idf=idf)
            caso = f"{rows[i]['name']} vs {rows[j]['name']} (estricto={estricto})"
            self.assertEqual(r_js["tier"], v["tier"], caso)
            self.assertEqual(r_js["nota"], v["nota"], caso)

    def test_casos_sinteticos(self):
        rows = [dict(r) for r in FILAS]
        self.comprobar(rows, pares_misma_fuente(rows))

    def test_ultimo_snapshot(self):
        snap = datos.ultimo_snapshot()
        if snap is None:
            self.skipTest("no hay snapshots")
        rows = datos.dedup_fuente_id(datos.cargar_csv(snap))
        # Cuatro referencias por fuente contra todo el catálogo de su fuente.
        refs = [i for src in ("igdb", "rawg")
                for i in [k for k, r in enumerate(rows) if r["source"] == src][:4]]
        self.comprobar(rows, pares_misma_fuente(rows, refs))


if __name__ == "__main__":
    unittest.main()
