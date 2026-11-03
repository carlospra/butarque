"""
Una partida = un nivel. Aquí están las REGLAS; principal.py solo dibuja y lee el teclado.

Cada fotograma, principal.py llama a partida.actualizar(dt, direccion, sigilo) y recibe
una lista de EVENTOS ("sílex recogido", "golpe"...) para enseñar mensajes en pantalla.
"""

from pygame.math import Vector2

from config import REAPARICION
from entidades import Animal, Jugador
from mundo import Mundo


class Evento:
    def __init__(self, tipo, pos, texto):
        self.tipo = tipo      # "silex", "caza", "golpe", "sin_silex", "aviso"
        self.pos = Vector2(pos)
        self.texto = texto


class Partida:
    def __init__(self, nivel, rng):
        self.nivel = nivel
        self.rng = rng
        self.mundo = Mundo(nivel, rng)
        inicio = Vector2(60, (self.mundo.arriba + self.mundo.abajo) / 2)
        while self.mundo.en_agua(inicio) or self.mundo.choca_arbol(inicio, 20):
            inicio.y += 30
        self.jugador = Jugador(inicio, nivel.silex_inicial)
        self.silex = list(self.mundo.silex)
        self.animales = []
        for tipo, cantidad in nivel.animales:
            for _ in range(cantidad):
                pos = self.mundo.punto_libre(margen=60, lejos_de=inicio, distancia=320)
                self.animales.append(Animal(tipo, pos, rng))
        self.pendientes = []           # [segundos que faltan, tipo] de animales por reaparecer
        self.tiempo = nivel.duracion
        self.cazados = []              # tipos cazados, para el resumen final

    # --- estado de la partida -------------------------------------------------------
    @property
    def ganada(self):
        return self.jugador.provisiones >= self.nivel.objetivo

    @property
    def perdida(self):
        return not self.ganada and (self.jugador.energia <= 0 or self.tiempo <= 0)

    @property
    def terminada(self):
        return self.ganada or self.perdida

    def motivo_derrota(self):
        if self.jugador.energia <= 0:
            return "Te has quedado sin energía."
        return "Se ha hecho de noche antes de reunir las provisiones."

    # --- acciones -------------------------------------------------------------------
    def actualizar(self, dt, direccion, sigilo):
        if self.terminada:
            return []
        eventos = []
        self.tiempo = max(0.0, self.tiempo - dt)
        j = self.jugador
        j.actualizar(dt, direccion, sigilo, self.mundo)

        # Recoger sílex al pasar por encima
        for s in self.silex[:]:
            if j.pos.distance_to(s) < j.radio + 8:
                self.silex.remove(s)
                j.silex += 1
                eventos.append(Evento("silex", s, "+1 sílex"))

        # Animales
        for animal in self.animales:
            if animal.actualizar(dt, j, self.mundo) == "golpe":
                if j.recibir_golpe(animal.pos):
                    eventos.append(Evento("golpe", j.pos, f"¡{animal.tipo.nombre}! -1 energía"))
        for animal in [a for a in self.animales if a.retirado]:
            self.animales.remove(animal)
            self.pendientes.append([REAPARICION, animal.tipo])

        # Reapariciones: entran por el borde izquierdo, lejos del jugador
        for pendiente in self.pendientes[:]:
            pendiente[0] -= dt
            if pendiente[0] <= 0:
                self.pendientes.remove(pendiente)
                self.animales.append(Animal(pendiente[1], self._entrada(), self.rng))
        return eventos

    def _entrada(self):
        m = self.mundo
        for _ in range(50):
            p = Vector2(30, self.rng.uniform(m.arriba + 40, m.abajo - 40))
            if p.distance_to(self.jugador.pos) > 250 and not m.en_agua(p) and not m.choca_arbol(p, 25):
                return p
        return m.punto_libre(lejos_de=self.jugador.pos, distancia=250)

    def animal_cazable(self):
        """La presa más cercana que se puede cazar ahora mismo, o None."""
        cerca = [a for a in self.animales if a.se_puede_cazar(self.jugador)]
        return min(cerca, key=lambda a: a.pos.distance_to(self.jugador.pos), default=None)

    def cazar(self):
        if self.terminada:
            return []
        animal = self.animal_cazable()
        if animal is None:
            return []
        if self.jugador.silex == 0:
            return [Evento("sin_silex", self.jugador.pos, "Necesitas sílex: búscalo en la orilla del río")]
        self.jugador.silex -= 1
        self.jugador.provisiones += animal.tipo.valor
        self.cazados.append(animal.tipo)
        self.animales.remove(animal)
        self.pendientes.append([REAPARICION, animal.tipo])
        # Los animales cercanos se asustan
        for otro in self.animales:
            if (otro.tipo.tipo == "presa" and otro.estado == "pasta"
                    and otro.pos.distance_to(animal.pos) < 200):
                otro.cambiar("alerta")
                otro.alerta = 0.6
        return [Evento("caza", animal.pos, f"+{animal.tipo.valor} provisiones ({animal.tipo.nombre})")]
