"""Tests de la selección y emparejamiento de precios PC (sin red).

Se ejecutan con: python -m unittest discover tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.precios import mejor_opcion, seleccionar_pc


def fila(**kw):
    base = {"source": "igdb", "source_id": "1", "name": "Hollow Knight",
            "platform_names": "PC (Microsoft Windows)|Nintendo Switch",
            "user_count": "100", "critic_count": "10"}
    base.update(kw)
    return base


class TestSeleccion(unittest.TestCase):
    def test_solo_pc(self):
        rows = [fila(),
                fila(source_id="2", name="Mario", platform_names="Nintendo Switch")]
        sel = seleccionar_pc(rows)
        self.assertEqual([r["name"] for r in sel], ["Hollow Knight"])

    def test_orden_por_votos_y_tope(self):
        rows = [fila(source_id=str(i), name=f"J{i}",
                     user_count=str(i * 10), platform_names="PC") for i in range(1, 8)]
        sel = seleccionar_pc(rows, n=3)
        self.assertEqual([r["user_count"] for r in sel], ["70", "60", "50"])

    def test_plataforma_rawg_pc(self):
        r = fila(source="rawg", platform_names="PC")
        self.assertEqual([x["name"] for x in seleccionar_pc([r])], ["Hollow Knight"])


class TestOpcion(unittest.TestCase):
    def test_nombre_exacto(self):
        ops = [{"external": "Hollow Knight", "gameID": "1", "cheapest": "14.99"}]
        m = mejor_opcion("Hollow Knight", ops)
        self.assertEqual(m["gameID"], "1")

    def test_edicion_distinta_se_rechaza(self):
        # Ratio ~0.57 < 0.90: una edicion NO es el producto del snapshot.
        ops = [{"external": "Hollow Knight: Definitive Edition", "gameID": "2"}]
        self.assertIsNone(mejor_opcion("Hollow Knight", ops))

    def test_vacio_sin_precio(self):
        self.assertIsNone(mejor_opcion("Hollow Knight", []))

    def test_elegme_el_mejor_ratio(self):
        ops = [{"external": "Hollow Knight - Something", "gameID": "a"},
               {"external": "Hollow Knight", "gameID": "b"}]
        m = mejor_opcion("Hollow Knight", ops)
        self.assertEqual(m["gameID"], "b")


if __name__ == "__main__":
    unittest.main()
