"""Tests del matching cruzado (puro, sin API).

Se ejecutan con: python -m unittest discover tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.matching import año_a_int, construir, mejor_candidato, normalizar


def fila(**kw):
    base = {"source": "igdb", "source_id": "1", "name": "Hollow Knight",
            "slug": "hollow-knight", "release_date": "2017-02-24"}
    base.update(kw)
    return base


class TestNormalizacion(unittest.TestCase):
    def test_acentos_y_puntuacion(self):
        self.assertEqual(normalizar("Pokémon: Espada!"), "pokemon espada")
        self.assertEqual(normalizar("The Witcher 3: Wild Hunt"), "the witcher 3 wild hunt")

    def test_anio_a_int(self):
        self.assertEqual(año_a_int("2017-02-24"), 2017)
        self.assertEqual(año_a_int("2014"), 2014)
        self.assertIsNone(año_a_int(""))
        self.assertIsNone(año_a_int(None))


class TestCandidato(unittest.TestCase):
    def test_nombre_exacto_enlaza(self):
        m = mejor_candidato(fila(), [fila(source="rawg", source_id="9")])
        self.assertIsNotNone(m)
        self.assertEqual(m["confianza"], "exacto")

    def test_remake_con_anios_lejanos_no_enlaza(self):
        m = mejor_candidato(fila(release_date="1998-03-23"),
                            [fila(source="rawg", source_id="9", release_date="2019-01-25")])
        self.assertIsNone(m)

    def test_anio_ausente_es_probable(self):
        m = mejor_candidato(fila(release_date=""),
                            [fila(source="rawg", source_id="9", release_date="2017-02-24")])
        self.assertIsNotNone(m)
        self.assertEqual(m["confianza"], "probable")

    def test_similitud_cercana_enlaza(self):
        otro = fila(source="rawg", source_id="9",
                    name="The Legend of Zelda: Breath of te Wild")  # typo real
        ref = fila(name="The Legend of Zelda: Breath of the Wild", slug="zelda-botw")
        m = mejor_candidato(ref, [otro])
        self.assertIsNotNone(m)
        self.assertEqual(m["confianza"], "cercano")

    def test_edicion_distinta_no_enlaza(self):
        # Ratio ~0.57: una edición con sufijo largo NO es la misma observación.
        otro = fila(source="rawg", source_id="9", name="Hollow Knight: Definitive Edition")
        self.assertIsNone(mejor_candidato(fila(), [otro]))

    def test_nombre_distinto_no_enlaza(self):
        m = mejor_candidato(fila(), [fila(source="rawg", source_id="9", name="Celeste")])
        self.assertIsNone(m)

    def test_varios_exactos_elige_menor_delta(self):
        cands = [fila(source="rawg", source_id="a", release_date="2019-01-01"),
                 fila(source="rawg", source_id="b", release_date="2017-01-01")]
        m = mejor_candidato(fila(), cands)
        self.assertEqual(m["contraparte"]["source_id"], "b")
        self.assertEqual(m["confianza"], "exacto")


class TestConstruir(unittest.TestCase):
    def test_simetrico_y_sin_fusion(self):
        rows = [
            fila(),
            fila(source="rawg", source_id="9"),
            fila(source="igdb", source_id="2", name="Celeste", slug="celeste",
                 release_date="2018-01-25"),
        ]
        pares = construir(rows)
        claves = {(p["origen"]["source"], p["origen"]["source_id"]) for p in pares}
        self.assertIn(("igdb", "1"), claves)
        self.assertIn(("rawg", "9"), claves)
        # Celeste no tiene contraparte: no aparece.
        self.assertNotIn(("igdb", "2"), claves)
        # Cada enlace apunta a la OTRA fuente (nunca fusiona filas).
        for p in pares:
            self.assertNotEqual(p["origen"]["source"], p["destino"]["source"])


if __name__ == "__main__":
    unittest.main()
