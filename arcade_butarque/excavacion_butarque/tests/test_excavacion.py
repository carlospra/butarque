"""
Pruebas de la lógica de la excavación. Ejecutar desde la carpeta del proyecto:
    python -m unittest discover tests
"""

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "juego"))

from datos import TipoFosil, cargar_fosiles, leer_forma  # noqa: E402
from excavacion import Yacimiento, girar  # noqa: E402


def tipo(nombre, forma):
    return TipoFosil("0", nombre, "", leer_forma(forma), (0, 0, 0), False, "")


class TestFormas(unittest.TestCase):
    def test_leer_forma(self):
        self.assertEqual(leer_forma("X.X/XXX"), [(0, 0), (0, 2), (1, 0), (1, 1), (1, 2)])

    def test_forma_invalida(self):
        with self.assertRaises(ValueError):
            leer_forma("XO")

    def test_cuatro_giros_vuelven_al_origen(self):
        forma = leer_forma("XXX/.X.")
        girada = forma
        for _ in range(4):
            girada = girar(girada)
        self.assertEqual(sorted(girada), sorted(forma))

    def test_colmillo_girado_es_vertical(self):
        self.assertEqual(sorted(girar(leer_forma("XXXX"))), [(0, 0), (1, 0), (2, 0), (3, 0)])


class TestYacimiento(unittest.TestCase):
    def setUp(self):
        self.tipos = [tipo("colmillo", "XXXX"), tipo("uro", "X.X/XXX"), tipo("silex", "X")]
        self.yac = Yacimiento(9, 14, self.tipos, golpes_extra=10, rng=random.Random(1))

    def test_fosiles_no_se_solapan(self):
        celdas = [c for f in self.yac.fosiles for c in f.celdas]
        self.assertEqual(len(celdas), len(set(celdas)))
        self.assertEqual(len(celdas), 4 + 5 + 1)

    def test_golpes_iniciales(self):
        self.assertEqual(self.yac.golpes, 10 + 10)

    def test_pista_cuenta_vecinas(self):
        for f in range(9):
            for c in range(14):
                esperado = sum(
                    1 for vf, vc in self.yac.vecinas(f, c) if self.yac.ocupante[vf][vc]
                )
                self.assertEqual(self.yac.pista(f, c), esperado)

    def test_excavar_dos_veces_no_gasta(self):
        f, c = next(iter(self.yac.fosiles[0].celdas))
        self.yac.excavar(f, c)
        golpes = self.yac.golpes
        self.assertEqual(self.yac.excavar(f, c)["tipo"], "ignorada")
        self.assertEqual(self.yac.golpes, golpes)

    def test_excavado_en_cadena_no_destapa_fosiles(self):
        for f in range(9):
            for c in range(14):
                if not self.yac.ocupante[f][c] and self.yac.pista(f, c) == 0:
                    self.yac.excavar(f, c)
                    break
            else:
                continue
            break
        destapadas = sum(sum(fila) for fila in self.yac.excavada)
        self.assertGreater(destapadas, 1)
        for fosil in self.yac.fosiles:
            self.assertEqual(fosil.encontradas, set())

    def test_ganar_destapando_todos_los_fosiles(self):
        completados = []
        for fosil in self.yac.fosiles:
            for f, c in fosil.celdas:
                r = self.yac.excavar(f, c)
                if r["completado"]:
                    completados.append(r["completado"])
        self.assertTrue(self.yac.ganada())
        self.assertEqual(len(completados), 3)
        self.assertEqual(self.yac.golpes, 10)

    def test_perder_al_agotar_golpes(self):
        self.yac.golpes = 1   # último golpe...
        f, c = next((f, c) for f in range(9) for c in range(14) if not self.yac.ocupante[f][c])
        self.yac.excavar(f, c)  # ...y se gasta en tierra
        self.assertTrue(self.yac.terminada())
        self.assertFalse(self.yac.ganada())
        # Con la partida terminada ya no se puede excavar
        fosil_f, fosil_c = next(iter(self.yac.fosiles[0].celdas))
        self.assertEqual(self.yac.excavar(fosil_f, fosil_c)["tipo"], "ignorada")


class TestCatalogo(unittest.TestCase):
    def test_catalogo_real_carga_y_cabe(self):
        base = Path(__file__).resolve().parent.parent
        catalogo = cargar_fosiles(base / "datos" / "fosiles.csv")
        self.assertTrue(any(t.siempre for t in catalogo))
        for semilla in range(200):  # muchas partidas: todo tiene que caber siempre
            Yacimiento(9, 14, catalogo, rng=random.Random(semilla))


if __name__ == "__main__":
    unittest.main()
