"""Tests de src.evolucion con datos SIMULADOS (etiquetados: no salen de APIs reales).

Verifican el cálculo de deltas entre dos oleadas y el guardia de
"suficientes observaciones" (sin 2 snapshots no hay tendencia).
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import datos, evolucion


def fila(source="igdb", source_id="1", name="Juego", critic="80", user="70",
         ccnt="10", ucnt="100", **kw):
    """Fila simulada al estilo de un snapshot (etiqueta: SIMULADA)."""
    base = {"source": source, "source_id": source_id, "slug": "j", "name": name,
            "platform_names": "PC", "genre_names": "Action", "release_date": "2020-01-01",
            "critic_score": critic, "user_score": user, "critic_count": ccnt,
            "user_count": ucnt, "observed_at": ""}
    base.update(kw)
    return base


class TestCalcularDeltas(unittest.TestCase):
    def test_cambio_de_metrica(self):
        ant = [fila(critic="80", user="70")]
        act = [fila(critic="85.5", user="70")]
        res = evolucion.calcular_deltas(ant, act)
        self.assertEqual(res["con_cambio"], 1)
        c = res["cambios"][0]["metricas"]["critic_score"]
        self.assertEqual((c["antes"], c["ahora"], c["delta"]), (80.0, 85.5, 5.5))

    def test_sin_cambio_no_aparece(self):
        res = evolucion.calcular_deltas([fila()], [fila()])
        self.assertEqual(res["con_cambio"], 0)
        self.assertEqual(res["cambios"], [])

    def test_alta_y_baja(self):
        ant = [fila(source_id="1", name="Viejo"), fila(source_id="2", name="SeVa")]
        act = [fila(source_id="1", name="Viejo"), fila(source_id="3", name="Nuevo")]
        res = evolucion.calcular_deltas(ant, act)
        self.assertEqual([a["name"] for a in res["altas"]], ["Nuevo"])
        self.assertEqual([b["name"] for b in res["bajas"]], ["SeVa"])

    def test_campo_ausente_no_inventa_delta(self):
        # Con un solo campo presente no hay delta calculable: no se inventa.
        d = evolucion._delta("", "90")
        self.assertIsNone(d)
        d2 = evolucion._delta("80", "")
        self.assertIsNone(d2)

    def test_no_compara_entre_fuentes(self):
        # Clave (source, source_id): igdb 1 y rawg 1 son juegos distintos.
        ant = [fila(source="igdb", source_id="1", critic="80")]
        act = [fila(source="rawg", source_id="1", critic="90")]
        res = evolucion.calcular_deltas(ant, act)
        self.assertEqual(res["con_cambio"], 0)
        self.assertEqual(len(res["altas"]), 1)
        self.assertEqual(len(res["bajas"]), 1)

    def test_orden_por_delta_de_critica(self):
        ant = [fila(source_id="1", critic="50"), fila(source_id="2", critic="90")]
        act = [fila(source_id="1", critic="90"), fila(source_id="2", critic="91")]
        res = evolucion.calcular_deltas(ant, act)
        self.assertEqual([c["source_id"] for c in res["cambios"]], ["1", "2"])


class TestCompararUltimos(unittest.TestCase):
    def test_un_snapshot_no_alcanza(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            import csv
            rows = datos.dedup_fuente_id([fila()])
            p = d / "snapshot_20260101T000000Z.csv"
            with p.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            self.assertIsNone(evolucion.comparar_ultimos(d))

    def test_dos_snapshots_calculan(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            import csv
            for name, critic in (("snapshot_20260101T000000Z.csv", "80"),
                                 ("snapshot_20260201T000000Z.csv", "88")):
                rows = [fila(critic=critic)]
                with (d / name).open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                    w.writeheader()
                    w.writerows(rows)
            res = evolucion.comparar_ultimos(d)
            self.assertTrue(res["suficientes_observaciones"])
            self.assertEqual(res["con_cambio"], 1)
            self.assertEqual(res["entre"]["anterior"], "snapshot_20260101T000000Z")
            self.assertEqual(res["entre"]["actual"], "snapshot_20260201T000000Z")


if __name__ == "__main__":
    unittest.main()
