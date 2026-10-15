"""Tests de src.datos (helpers compartidos). Datos simulados, sin API ni ficheros reales."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import datos


def fila(source="rawg", source_id="1", platforms="PC|PlayStation 4", **kw):
    base = {"source": source, "source_id": source_id, "platform_names": platforms,
            "name": "Juego", "slug": "juego"}
    base.update(kw)
    return base


class TestPresente(unittest.TestCase):
    def test_vacio_y_none_literal_no_presente(self):
        self.assertFalse(datos.presente(""))
        self.assertFalse(datos.presente(None))
        self.assertFalse(datos.presente("None"))
        self.assertFalse(datos.presente("  "))
        self.assertTrue(datos.presente("85"))
        self.assertTrue(datos.presente(0))

class TestNumero(unittest.TestCase):
    def test_parsea_y_tolera_basura(self):
        self.assertEqual(datos.numero("85.5"), 85.5)
        self.assertIsNone(datos.numero(""))
        self.assertIsNone(datos.numero("None"))
        self.assertIsNone(datos.numero("n/a"))
        self.assertEqual(datos.entero("85.0"), 85)
        self.assertIsNone(datos.entero(None))

class TestYear(unittest.TestCase):
    def test_extrae_anio(self):
        self.assertEqual(datos.year_de("2017-02-24"), 2017)
        self.assertIsNone(datos.year_de(""))
        self.assertIsNone(datos.year_de(None))
        self.assertIsNone(datos.year_de("ab cd"))

class TestConjuntoYGeneros(unittest.TestCase):
    def test_conjunto_minusculas(self):
        self.assertEqual(datos.conjunto_de("PC | PS4||"), {"pc", "ps4"})

    def test_generos_igdb_se_canonizan_a_vocabulario_rawg(self):
        # IGDB "Role-playing (RPG)" -> "rpg" (vocabulario canónico).
        self.assertEqual(datos.generos_canonicos("igdb", "Role-playing (RPG)|Indie"),
                         {"rpg", "indie"})

    def test_generos_rawg_se_dejan(self):
        self.assertEqual(datos.generos_canonicos("rawg", "Action|Indie"), {"action", "indie"})

class TestDedup(unittest.TestCase):
    def test_conserva_fila_con_mas_plataformas(self):
        # Simulado: el mismo juego en dos grupos de muestreo (multiplataforma).
        a = fila(platforms="PC")
        b = fila(platforms="PC|PlayStation 4|Xbox One")
        out = datos.dedup_fuente_id([a, b])
        self.assertEqual(len(out), 1)
        self.assertEqual(datos.n_plataformas(out[0]), 3)

    def test_ids_distintos_no_se_mezclan(self):
        out = datos.dedup_fuente_id([fila(source_id="1"), fila(source_id="2")])
        self.assertEqual(len(out), 2)

    def test_fuente_forma_parte_de_la_clave(self):
        out = datos.dedup_fuente_id([fila(source="rawg", source_id="1"),
                                     fila(source="igdb", source_id="1")])
        self.assertEqual(len(out), 2)

    def test_orden_estable_por_fuente_e_id(self):
        out = datos.dedup_fuente_id([fila(source="rawg", source_id="9"),
                                     fila(source="igdb", source_id="3")])
        self.assertEqual([r["source"] for r in out], ["igdb", "rawg"])

class TestSnapshots(unittest.TestCase):
    def test_orden_cronologico_con_y_sin_hora(self):
        files = [Path("snapshot_20261013.csv"), Path("snapshot_20261015T120000Z.csv"),
                 Path("snapshot_20261014.csv")]
        out = datos.snapshots(files)
        self.assertEqual([p.stem for p in out],
                         ["snapshot_20261013", "snapshot_20261014", "snapshot_20261015T120000Z"])

    def test_vacio_devuelve_none(self):
        self.assertIsNone(datos.ultimo_snapshot(Path("ruta/que/no/existe")))


if __name__ == "__main__":
    unittest.main()
