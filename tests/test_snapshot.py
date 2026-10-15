"""Tests de src.snapshot con datos simulados en directorios temporales (sin tocar data/)."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import snapshot


def fila(source="rawg", source_id="1", plats="PC|PS4", critic="80", **kw):
    base = {
        "source": source, "source_id": source_id, "slug": "j", "name": "Juego",
        "grupo": "PC", "platform_names": plats, "genre_names": "Action",
        "release_date": "2020-01-01", "developer_names": "", "publisher_names": "",
        "critic_score": critic, "critic_count": "", "user_score": "4.1",
        "user_count": "100", "popularity_extra": "", "game_url": "", "image_url": "",
        "price": "", "observed_at": "2026-10-15T00:00:00+00:00",
    }
    base.update(kw)
    return base


class TestDedupConNplat(unittest.TestCase):
    def test_anade_columna_y_deduplica(self):
        rows = [fila(plats="PC"), fila(plats="PC|PS4|Xbox")]
        out = snapshot.dedup_con_nplat(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["n_plataformas"], 3)

class TestEscribirSnapshot(unittest.TestCase):
    def test_no_sobrescribe_e_incluye_meta(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            uniq = snapshot.dedup_con_nplat([fila()])
            f1, m1 = snapshot.escribir_snapshot(uniq, d)
            f2, m2 = snapshot.escribir_snapshot(uniq, d)
            self.assertNotEqual(f1, f2)  # dos ejecuciones = dos fotos (append-only)
            self.assertTrue(f1.exists() and f2.exists())
            meta = json.loads(m1.read_text(encoding="utf-8"))
            self.assertTrue(meta["append_only"])
            self.assertEqual(meta["n"], 1)
            self.assertEqual(meta["por_fuente"]["rawg"]["con_critica"], 1)

    def test_csv_legible_con_columnas(self):
        with tempfile.TemporaryDirectory() as td:
            uniq = snapshot.dedup_con_nplat([fila()])
            f, _ = snapshot.escribir_snapshot(uniq, Path(td))
            with f.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 1)
            self.assertIn("n_plataformas", rows[0])
            self.assertIn("observed_at", rows[0])

class TestMain(unittest.TestCase):
    def test_main_con_muestras_simuladas(self):
        with tempfile.TemporaryDirectory() as td:
            proc, snapdir = Path(td) / "proc", Path(td) / "snap"
            proc.mkdir()
            with (proc / "muestra_normalizada.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(fila().keys()))
                w.writeheader()
                w.writerows([fila(), fila(plats="PC|PS4")])
            rc = snapshot.main(proc_dir=proc, snap_dir=snapdir)
            self.assertEqual(rc, 0)
            self.assertEqual(len(list(snapdir.glob("snapshot_*.csv"))), 1)

    def test_main_sin_muestras_devuelve_1(self):
        with tempfile.TemporaryDirectory() as td:
            rc = snapshot.main(proc_dir=Path(td), snap_dir=Path(td) / "snap")
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
