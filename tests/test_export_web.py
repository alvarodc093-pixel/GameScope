"""Tests de src.export_web con datos simulados en tmp (sin tocar web/data real)."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import export_web


def fila(source="igdb", source_id="1", **kw):
    base = {
        "source": source, "source_id": source_id, "slug": "hollow-knight",
        "name": "Hollow Knight", "grupo": "PC", "oleada": "top",
        "platform_names": "PC|Nintendo Switch", "genre_names": "Indie|Adventure",
        "release_date": "2017-02-24", "developer_names": "Team Cherry",
        "publisher_names": "Team Cherry", "critic_score": "90", "critic_count": "20",
        "user_score": "89", "user_count": "5000", "game_url": "https://example.com",
        "image_url": "https://example.com/i.png", "observed_at": "2026-10-13T18:00:00+00:00",
    }
    base.update(kw)
    return base


def escribir_snapshot(d: Path, nombre: str, rows: list[dict]) -> Path:
    p = d / nombre
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return p


class TestJuegoDesdeFila(unittest.TestCase):
    def test_modelo_json_escala_y_listas(self):
        g = export_web.juego_desde_fila(fila())
        self.assertEqual(g["critic"]["scale"], 100)  # igdb
        self.assertEqual(g["user"]["scale"], 100)
        self.assertEqual(g["platforms"], ["PC", "Nintendo Switch"])
        self.assertEqual(g["year"], 2017)
        self.assertEqual(g["user"]["count"], 5000)

    def test_rawg_escala_usuarios_5(self):
        g = export_web.juego_desde_fila(fila(source="rawg", user_score="4.2", critic_score=""))
        self.assertEqual(g["user"]["scale"], 5)
        self.assertEqual(g["user"]["score"], 4.2)
        self.assertIsNone(g["critic"]["score"])

    def test_nulos_y_none_literal(self):
        g = export_web.juego_desde_fila(fila(critic_score="", user_score="None"))
        self.assertIsNone(g["critic"]["score"])
        self.assertIsNone(g["user"]["score"])

    def test_construir_ordena(self):
        rows = [fila(source="rawg", name="B"), fila(source="igdb", name="a"), fila(source="igdb", name="C")]
        out = export_web.construir_juegos(rows)
        self.assertEqual([(g["source"], g["name"]) for g in out],
                         [("igdb", "a"), ("igdb", "C"), ("rawg", "B")])


class TestEvolucionPara(unittest.TestCase):
    def test_un_snapshot_bandera_honesta(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            escribir_snapshot(d, "snapshot_20260101T000000Z.csv", [fila()])
            evo = export_web.evolucion_para(d)
            self.assertFalse(evo["suficientes_observaciones"])
            self.assertEqual(evo["n_snapshots"], 1)
            self.assertIn("snapshot", evo["mensaje"])

    def test_dos_snapshots_con_cambio(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            escribir_snapshot(d, "snapshot_20260101T000000Z.csv", [fila(critic_score="80")])
            escribir_snapshot(d, "snapshot_20260201T000000Z.csv", [fila(critic_score="84")])
            evo = export_web.evolucion_para(d)
            self.assertTrue(evo["suficientes_observaciones"])
            self.assertEqual(evo["con_cambio"], 1)


class TestMain(unittest.TestCase):
    def test_main_escribe_tres_ficheros(self):
        with tempfile.TemporaryDirectory() as td:
            snapdir = Path(td) / "snaps"
            webdata = Path(td) / "webdata"
            snapdir.mkdir()
            escribir_snapshot(snapdir, "snapshot_20260101T000000Z.csv",
                              [fila(), fila(source="rawg", user_score="4.5")])
            rc = export_web.main(snap_dir=snapdir, web_data=webdata)
            self.assertEqual(rc, 0)
            games = json.loads((webdata / "games.json").read_text(encoding="utf-8"))
            meta = json.loads((webdata / "meta.json").read_text(encoding="utf-8"))
            evo = json.loads((webdata / "evolucion.json").read_text(encoding="utf-8"))
            self.assertEqual(len(games), 2)
            self.assertEqual(meta["n"], 2)
            self.assertEqual(meta["por_fuente"]["igdb"], 1)
            self.assertFalse(evo["suficientes_observaciones"])
            self.assertTrue(meta["generated_at"])
            self.assertEqual(meta["observed_at_min"], "2026-10-13T18:00:00+00:00")

    def test_main_sin_snapshots_devuelve_1(self):
        with tempfile.TemporaryDirectory() as td:
            rc = export_web.main(snap_dir=Path(td), web_data=Path(td) / "w")
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
