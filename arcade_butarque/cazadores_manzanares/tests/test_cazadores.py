"""
Pruebas de la lógica. Ejecutar desde la carpeta del proyecto:
    python -m unittest discover tests
"""

import random
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "juego"))

from pygame.math import Vector2  # noqa: E402

from config import ENERGIA, OIDO_NORMAL  # noqa: E402
from datos import cargar  # noqa: E402
from entidades import Animal, detectar  # noqa: E402
from mundo import distancia_a_segmento  # noqa: E402
from partida import Partida  # noqa: E402

CATALOGO, NIVELES = cargar(RAIZ / "datos")
DERECHA = Vector2(1, 0)


class TestDeteccion(unittest.TestCase):
    def test_ve_delante(self):
        self.assertTrue(detectar(Vector2(0, 0), DERECHA, 240, Vector2(200, 0), False, False))

    def test_no_ve_detras(self):
        self.assertFalse(detectar(Vector2(0, 0), DERECHA, 240, Vector2(-200, 0), False, False))

    def test_oye_detras_si_estas_muy_cerca(self):
        self.assertTrue(detectar(Vector2(0, 0), DERECHA, 240, Vector2(-(OIDO_NORMAL - 10), 0), False, False))

    def test_acechando_no_te_oye_detras(self):
        self.assertFalse(detectar(Vector2(0, 0), DERECHA, 240, Vector2(-(OIDO_NORMAL - 10), 0), True, False))

    def test_sigilo_y_hierba_reducen_el_alcance(self):
        lejos = Vector2(180, 0)
        self.assertTrue(detectar(Vector2(0, 0), DERECHA, 240, lejos, False, False))
        self.assertFalse(detectar(Vector2(0, 0), DERECHA, 240, lejos, True, False))
        self.assertFalse(detectar(Vector2(0, 0), DERECHA, 240, Vector2(80, 0), True, True))

    def test_borde_del_cono(self):
        dentro = Vector2(100, 0).rotate(55)
        fuera = Vector2(200, 0).rotate(70)
        self.assertTrue(detectar(Vector2(0, 0), DERECHA, 240, dentro, False, False))
        self.assertFalse(detectar(Vector2(0, 0), DERECHA, 240, fuera, False, False))


class TestGeometria(unittest.TestCase):
    def test_distancia_a_segmento(self):
        a, b = Vector2(0, 0), Vector2(10, 0)
        self.assertAlmostEqual(distancia_a_segmento(Vector2(5, 3), a, b), 3)
        self.assertAlmostEqual(distancia_a_segmento(Vector2(13, 4), a, b), 5)


def partida_vacia(numero=1, semilla=0):
    """Una partida sin animales, para colocar a mano los que haga falta."""
    p = Partida(NIVELES[numero - 1], random.Random(semilla))
    p.animales = []
    return p


def colocar(partida, tipo_id, desplazamiento, mira):
    """Pone un animal relativo al jugador, mirando en la dirección indicada."""
    a = Animal(CATALOGO[tipo_id], partida.jugador.pos + desplazamiento, random.Random(1))
    a.mira = Vector2(mira).normalize()
    a.pausa = 99           # que no se mueva mientras pasta
    partida.animales.append(a)
    return a


class TestMaquinaDeEstados(unittest.TestCase):
    def avanzar(self, partida, segundos, sigilo=False):
        for _ in range(int(segundos * 60)):
            partida.actualizar(1 / 60, Vector2(), sigilo)

    def test_presa_que_te_ve_se_pone_alerta_y_huye(self):
        p = partida_vacia()
        caballo = colocar(p, "caballo", Vector2(200, 0), (-1, 0))   # mirando al jugador
        self.avanzar(p, 0.1)
        self.assertEqual(caballo.estado, "alerta")
        self.avanzar(p, 4)        # aunque estés quieto, si te sigue viendo acaba huyendo
        self.assertEqual(caballo.estado, "huye")

    def test_correr_asusta_mas_que_acechar_y_acechar_mas_que_quedarse_quieto(self):
        p = partida_vacia()
        caballo = colocar(p, "caballo", Vector2(150, 0), (-1, 0))
        j = p.jugador
        j.moviendo, j.sigilo = True, False
        corriendo = caballo.ritmo_de_miedo(j, 150)
        j.moviendo, j.sigilo = True, True
        acechando = caballo.ritmo_de_miedo(j, 150)
        j.moviendo = False
        quieto = caballo.ritmo_de_miedo(j, 150)
        self.assertGreater(corriendo, acechando)
        self.assertGreater(acechando, quieto)

    def test_cuanto_mas_cerca_mas_miedo(self):
        p = partida_vacia()
        caballo = colocar(p, "caballo", Vector2(150, 0), (-1, 0))
        self.assertGreater(caballo.ritmo_de_miedo(p.jugador, 50), caballo.ritmo_de_miedo(p.jugador, 200))

    def test_presa_de_espaldas_no_se_entera(self):
        p = partida_vacia()
        caballo = colocar(p, "caballo", Vector2(200, 0), (1, 0))    # mirando hacia otro lado
        self.avanzar(p, 2)
        self.assertEqual(caballo.estado, "pasta")

    def test_uro_avisa_antes_de_embestir_y_golpea(self):
        p = partida_vacia(2)
        uro = colocar(p, "uro", Vector2(150, 0), (-1, 0))
        estados = []
        for _ in range(8 * 60):
            p.actualizar(1 / 60, Vector2(), False)
            if not estados or estados[-1] != uro.estado:
                estados.append(uro.estado)
            if p.jugador.energia < ENERGIA:
                break
        self.assertEqual(p.jugador.energia, ENERGIA - 1)
        self.assertEqual(estados[:4], ["alerta", "amenaza", "embiste", "pasta"])

    def test_se_puede_esquivar_la_embestida(self):
        p = partida_vacia(2)
        uro = colocar(p, "uro", Vector2(200, 0), (-1, 0))
        while uro.estado != "embiste":
            p.actualizar(1 / 60, Vector2(), False)
        for _ in range(90):                       # apartarse de lado durante la carga
            p.actualizar(1 / 60, Vector2(0, -1), False)
        self.assertEqual(p.jugador.energia, ENERGIA)

    def test_lobo_persigue_al_verte(self):
        p = partida_vacia(2)
        lobo = colocar(p, "lobo", Vector2(200, 0), (-1, 0))
        self.avanzar(p, 0.1)
        self.assertEqual(lobo.estado, "persigue")


class TestReglas(unittest.TestCase):
    def test_cazar_gasta_silex_y_da_provisiones(self):
        p = partida_vacia()
        p.jugador.silex = 1
        colocar(p, "caballo", Vector2(30, 0), (1, 0))
        eventos = p.cazar()
        self.assertEqual(eventos[0].tipo, "caza")
        self.assertEqual(p.jugador.provisiones, CATALOGO["caballo"].valor)
        self.assertEqual(p.jugador.silex, 0)
        self.assertEqual(p.animales, [])
        self.assertEqual(len(p.pendientes), 1)       # reaparecerá otro

    def test_sin_silex_no_se_caza(self):
        p = partida_vacia()
        p.jugador.silex = 0
        colocar(p, "caballo", Vector2(30, 0), (1, 0))
        self.assertEqual(p.cazar()[0].tipo, "sin_silex")
        self.assertEqual(p.jugador.provisiones, 0)

    def test_lobo_no_se_caza(self):
        p = partida_vacia(2)
        colocar(p, "lobo", Vector2(30, 0), (1, 0))
        self.assertEqual(p.cazar(), [])

    def test_ganar_y_perder(self):
        p = partida_vacia()
        p.jugador.provisiones = p.nivel.objetivo
        self.assertTrue(p.ganada)
        p = partida_vacia()
        p.tiempo = 0.01
        p.actualizar(0.1, Vector2(), False)
        self.assertTrue(p.perdida)


class TestSimulacion(unittest.TestCase):
    def test_todos_los_niveles_aguantan_3_minutos_de_juego_aleatorio(self):
        for nivel in NIVELES:
            for semilla in range(3):
                rng = random.Random(semilla)
                p = Partida(nivel, rng)
                p.jugador.energia = 999          # que no acabe por golpes
                p.tiempo = 999
                direccion = Vector2()
                for paso in range(180 * 30):     # 3 minutos a 30 fps
                    if paso % 30 == 0:
                        direccion = Vector2(rng.uniform(-1, 1), rng.uniform(-1, 1))
                    p.actualizar(1 / 30, direccion, rng.random() < 0.5)
                    if paso % 15 == 0:
                        p.cazar()
                    for a in p.animales:          # ningún animal en el río ni fuera del mundo
                        self.assertFalse(p.mundo.en_rio(a.pos) and a.estado != "huye")
                self.assertGreater(len(p.animales) + len(p.pendientes), 0)


if __name__ == "__main__":
    unittest.main()
