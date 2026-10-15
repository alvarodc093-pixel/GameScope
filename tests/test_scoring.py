"""Tests del scoring v1 (stdlib unittest, sin API).

Se ejecutan con: python -m unittest discover tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scoring import puntuar


def juego(**kw):
    base = {"source": "igdb", "genre_names": "Adventure|Shooter",
            "platform_names": "PC (Microsoft Windows)|PlayStation 4",
            "release_date": "2013-05-01", "developer_names": "Estudio A"}
    base.update(kw)
    return base


class TestScoring(unittest.TestCase):
    def test_sin_genero_comun_descarta(self):
        ref, cand = juego(), juego(genre_names="Puzzle")
        v = puntuar(ref, cand)
        self.assertEqual(v["tier"], "descartado")

    def test_genero_solo_no_basta_sin_plataforma(self):
        ref, cand = juego(), juego(platform_names="Nintendo Switch")
        v = puntuar(ref, cand)
        self.assertEqual(v["tier"], "descartado")

    def test_ausente_no_infla(self):
        ref = juego(release_date="")
        v_sin = puntuar(ref, juego())
        v_lejos = puntuar(juego(release_date="2013-05-01"), juego(release_date="1990-01-01"))
        self.assertEqual(v_sin["partes"]["era"][0], 0.0)
        self.assertLessEqual(v_sin["nota"], 1.0)
        self.assertEqual(v_lejos["partes"]["era"][0], 0.0)

    def test_estudio_na_no_penaliza_rawg(self):
        ref = juego(source="rawg", genre_names="Action",
                    platform_names="PC", developer_names="")
        cand = juego(source="rawg", genre_names="Action",
                     platform_names="PC", developer_names="")
        v = puntuar(ref, cand)
        self.assertNotIn("estudio", v["partes"])
        self.assertGreater(v["nota"], 0)

    def test_pesos_configurables_cambian_tier(self):
        ref, cand = juego(), juego(genre_names="Adventure")  # 1 género, 2 plats, era ok
        base = puntuar(ref, cand)
        alto = puntuar(ref, cand, pesos={"genero": 10.0})
        self.assertNotEqual(base["nota"], alto["nota"])

    def test_determinista(self):
        ref, cand = juego(), juego()
        self.assertEqual(puntuar(ref, cand)["nota"], puntuar(ref, cand)["nota"])

    def test_insuficiente_con_genero_ausente(self):
        v = puntuar(juego(genre_names=""), juego())
        self.assertEqual(v["tier"], "insuficiente")


class TestModoEstricto(unittest.TestCase):
    def test_v1_admite_fecha_ausente_estricto_no(self):
        ref = juego(release_date="")
        v1 = puntuar(ref, juego())
        self.assertNotEqual(v1["tier"], "insuficiente")
        ve = puntuar(ref, juego(), estricto=True)
        self.assertEqual(ve["tier"], "insuficiente")
        self.assertIn("fecha ausente", ve["motivo"])

    def test_estricto_un_solo_genero_comun_descarta(self):
        ref, cand = juego(), juego(genre_names="Adventure")  # 1 en común
        self.assertNotEqual(puntuar(ref, cand)["tier"], "descartado")
        ve = puntuar(ref, cand, estricto=True)
        self.assertEqual(ve["tier"], "descartado")
        self.assertIn("mínimo 2", ve["motivo"])

    def test_estricto_pareja_admitida_puntua_igual(self):
        ref, cand = juego(), juego(genre_names="Adventure|Shooter")  # 2 en común
        v1 = puntuar(ref, cand)
        ve = puntuar(ref, cand, estricto=True)
        self.assertEqual(v1["nota"], ve["nota"])
        self.assertEqual(v1["tier"], ve["tier"])

    def test_estricto_no_cambia_pesos_ni_umbrales(self):
        from src.scoring import PESOS, UMBRALES
        ref, cand = juego(), juego(genre_names="Adventure|Shooter")
        ve = puntuar(ref, cand, estricto=True)
        self.assertEqual(ve["nota"], puntuar(ref, cand)["nota"])
        self.assertEqual(sorted(UMBRALES), ["directo", "relacionado", "secundario"])
        self.assertEqual(PESOS["genero"], 3.0)


if __name__ == "__main__":
    unittest.main()
