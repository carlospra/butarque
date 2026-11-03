"""
El escenario: la llanura de inundación donde el arroyo Butarque desemboca en el Manzanares.

Todo se representa con formas sencillas:
  - río:     todo lo que queda a la derecha de una línea ondulada (borde_rio)
  - arroyo:  una línea quebrada con grosor (lista de puntos)
  - hierba:  círculos donde es más difícil que te vean
  - árboles: círculos que no se pueden atravesar
  - sílex:   puntos en la grava de la orilla del río
"""

import math

from pygame.math import Vector2

from config import ALTO, ANCHO, HUD_ALTO

ANCHO_ARROYO = 13   # medio grosor


def distancia_a_segmento(p, a, b):
    """Distancia del punto p al segmento a-b (geometría básica con vectores)."""
    ab = b - a
    if ab.length_squared() == 0:
        return p.distance_to(a)
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared()))
    return p.distance_to(a + ab * t)


class Mundo:
    def __init__(self, nivel, rng):
        self.rng = rng
        self.fase = rng.uniform(0, 2 * math.pi)
        self.arriba = HUD_ALTO
        self.abajo = ALTO

        # Arroyo Butarque: baja desde la izquierda hasta el río
        y = rng.uniform(self.arriba + 250, self.abajo - 120)
        self.arroyo = []
        pasos = 7
        for i in range(pasos + 1):
            x = i * (ANCHO - 120) / pasos
            if i == pasos:
                x = self.borde_rio(y) + 5
            self.arroyo.append(Vector2(x, y))
            y = max(self.arriba + 200, min(self.abajo - 60, y + rng.uniform(-45, 25)))

        # Hierba alta: manchas hechas de 3 círculos cada una
        self.hierba = []
        for _ in range(nivel.hierba):
            centro = self.punto_libre(margen=90)
            for _ in range(3):
                desvio = Vector2(rng.uniform(-45, 45), rng.uniform(-35, 35))
                self.hierba.append((centro + desvio, rng.uniform(38, 60)))

        # Árboles
        self.arboles = []
        for _ in range(nivel.arboles):
            for _ in range(50):
                p = self.punto_libre(margen=60)
                if all(p.distance_to(c) > r + 40 for c, r in self.arboles) and not self.en_hierba(p):
                    self.arboles.append((p, rng.uniform(18, 26)))
                    break

        # Sílex en la grava de la orilla
        self.silex = []
        for _ in range(nivel.silex_rio):
            y = rng.uniform(self.arriba + 30, self.abajo - 30)
            self.silex.append(Vector2(self.borde_rio(y) - rng.uniform(14, 40), y))

    # --- consultas -------------------------------------------------------------
    def borde_rio(self, y):
        """Coordenada x donde empieza el agua del Manzanares a la altura y."""
        return 1120 + 28 * math.sin(y / 85 + self.fase) + 12 * math.sin(y / 31)

    def en_rio(self, p):
        return p.x > self.borde_rio(p.y)

    def en_arroyo(self, p):
        return any(
            distancia_a_segmento(p, a, b) < ANCHO_ARROYO
            for a, b in zip(self.arroyo, self.arroyo[1:])
        )

    def en_agua(self, p):
        return self.en_rio(p) or self.en_arroyo(p)

    def en_hierba(self, p):
        return any(p.distance_to(c) < r for c, r in self.hierba)

    def dentro(self, p, margen=0):
        return (margen <= p.x <= ANCHO - margen) and (self.arriba + margen <= p.y <= self.abajo - margen)

    def choca_arbol(self, p, radio):
        return any(p.distance_to(c) < r + radio for c, r in self.arboles)

    def empujar_fuera_de_arboles(self, p, radio):
        """Si p se mete en un árbol, lo saca por el borde más cercano."""
        for c, r in self.arboles:
            d = p - c
            minimo = r + radio
            if d.length() < minimo:
                if d.length() == 0:
                    d = Vector2(1, 0)
                p = c + d.normalize() * minimo
        return p

    def punto_libre(self, margen=40, lejos_de=None, distancia=0, intentos=200):
        """Un punto al azar en tierra firme, sin árbol, y opcionalmente lejos de otro punto."""
        for _ in range(intentos):
            p = Vector2(
                self.rng.uniform(margen, ANCHO - margen),
                self.rng.uniform(self.arriba + margen, self.abajo - margen),
            )
            if self.en_rio(p) or p.x > self.borde_rio(p.y) - 60:
                continue
            if hasattr(self, "arboles") and self.choca_arbol(p, 25):
                continue
            if lejos_de is not None and p.distance_to(lejos_de) < distancia:
                continue
            return p
        return Vector2(ANCHO / 2, (self.arriba + self.abajo) / 2)
