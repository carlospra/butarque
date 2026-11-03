"""
Jugador y animales.

Cada animal es una MÁQUINA DE ESTADOS: en cada momento está en un único estado
y unas condiciones concretas le hacen pasar a otro.

            te detecta                    llega al límite de nervio
   PASTA ─────────────────▶ ALERTA ─────────────────────────────▶ HUYE  (caballo, ciervo...)
     ▲                        │                                └──▶ EMBISTE (uro, bisonte...)
     │      te pierde         │
     └────────────────────────┘
   PASTA ──── te detecta ───▶ PERSIGUE   (lobo)

Todos los movimientos usan dt (segundos desde el fotograma anterior), así el juego
va a la misma velocidad en un ordenador rápido y en una Raspberry Pi.
"""

from pygame.math import Vector2

from config import (ALCANCE_CAZA, ANCHO, ANGULO_VISTA, CALMA, DURACION_AMENAZA, DURACION_EMBESTIDA, ENERGIA,
                    MIEDO_CARRERA, MIEDO_CERCANIA, MIEDO_QUIETO,
                    FACTOR_HIERBA, FACTOR_SIGILO, FRENO_AGUA, INVULNERABLE, OIDO_NORMAL,
                    OIDO_SIGILO, VEL_NORMAL, VEL_SIGILO)


def detectar(pos_animal, mira, vista, pos_jugador, sigilo, en_hierba):
    """
    ¿El animal se da cuenta del jugador?
      - Le OYE si está muy cerca (más cerca aún si va agachado).
      - Le VE si está dentro de su cono de visión: ángulo y distancia.
        Agachado y entre la hierba hay que estar mucho más cerca para que te vea.
    """
    hacia_jugador = pos_jugador - pos_animal
    distancia = hacia_jugador.length()
    oido = OIDO_SIGILO if sigilo else OIDO_NORMAL
    if distancia < oido:
        return True
    alcance = vista
    if sigilo:
        alcance *= FACTOR_SIGILO
    if en_hierba:
        alcance *= FACTOR_HIERBA
    if distancia > alcance:
        return False
    angulo = mira.angle_to(hacia_jugador)
    angulo = (angulo + 180) % 360 - 180      # dejarlo entre -180 y 180
    return abs(angulo) <= ANGULO_VISTA


class Jugador:
    radio = 14

    def __init__(self, pos, silex):
        self.pos = Vector2(pos)
        self.mira = Vector2(1, 0)
        self.energia = ENERGIA
        self.silex = silex
        self.provisiones = 0
        self.sigilo = False
        self.moviendo = False
        self.invulnerable = 0.0

    def actualizar(self, dt, direccion, sigilo, mundo):
        self.sigilo = sigilo
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.moviendo = direccion.length_squared() > 0
        if not self.moviendo:
            return
        direccion = direccion.normalize()
        self.mira = direccion
        velocidad = VEL_SIGILO if sigilo else VEL_NORMAL
        if mundo.en_agua(self.pos):
            velocidad *= FRENO_AGUA
        nueva = self.pos + direccion * velocidad * dt
        # No salir de la pantalla
        nueva.x = max(self.radio, min(nueva.x, ANCHO - self.radio))
        nueva.y = max(mundo.arriba + self.radio, min(nueva.y, mundo.abajo - self.radio))
        self.pos = mundo.empujar_fuera_de_arboles(nueva, self.radio)

    def recibir_golpe(self, origen):
        """Devuelve True si el golpe cuenta (no estaba protegido)."""
        if self.invulnerable > 0:
            return False
        self.energia -= 1
        self.invulnerable = INVULNERABLE
        empujon = self.pos - origen
        if empujon.length_squared() > 0:
            self.pos += empujon.normalize() * 40
        return True


class Animal:
    def __init__(self, tipo, pos, rng):
        self.tipo = tipo
        self.pos = Vector2(pos)
        self.rng = rng
        self.mira = Vector2(1, 0).rotate(rng.uniform(0, 360))
        self.estado = "pasta"
        self.tiempo_estado = 0.0
        self.alerta = 0.0          # de 0 a 1: cuando llega a 1, reacciona
        self.calma = 0.0           # mientras sea > 0 no hace caso al jugador
        self.objetivo = None       # adónde camina mientras pasta
        self.pausa = rng.uniform(0.5, 2.5)
        self.carga = Vector2()     # dirección de la embestida
        self.retirado = False      # True cuando sale del mapa y hay que quitarlo

    @property
    def radio(self):
        return self.tipo.tamano

    def cambiar(self, estado):
        self.estado = estado
        self.tiempo_estado = 0.0

    def ve_al_jugador(self, jugador, mundo):
        return detectar(self.pos, self.mira, self.tipo.vista, jugador.pos,
                        jugador.sigilo, mundo.en_hierba(jugador.pos))

    def toca(self, jugador, extra=0):
        return self.pos.distance_to(jugador.pos) < self.radio + jugador.radio + extra

    def se_puede_cazar(self, jugador):
        return (self.tipo.tipo == "presa" and self.estado in ("pasta", "alerta")
                and self.calma == 0 and self.toca(jugador, ALCANCE_CAZA))

    def ritmo_de_miedo(self, jugador, distancia):
        """Cuánto sube la alerta por segundo. Al llegar a 1, el animal reacciona."""
        ritmo = 1 / self.tipo.nervio
        if not jugador.moviendo:
            ritmo *= MIEDO_QUIETO           # quieto: duda
        elif not jugador.sigilo:
            ritmo *= MIEDO_CARRERA          # corriendo: se asusta enseguida
        cercania = max(0.0, 1 - distancia / self.tipo.vista)
        return ritmo * (1 + MIEDO_CERCANIA * cercania)

    # --- movimiento ------------------------------------------------------------
    def _avanzar(self, direccion, velocidad, dt, mundo, puede_salir=False):
        """Avanza esquivando el río: prueba la dirección y, si no puede, gira."""
        for giro in (0, 35, -35, 70, -70, 110, -110):
            d = direccion.rotate(giro)
            nueva = self.pos + d * velocidad * dt
            if mundo.en_rio(nueva) or mundo.choca_arbol(nueva, self.radio):
                continue
            if not puede_salir and not mundo.dentro(nueva, self.radio):
                continue
            self.pos = nueva
            self.mira = d
            return True
        return False

    def _pasear(self, dt, mundo):
        if self.pausa > 0:
            self.pausa -= dt
            self.mira = self.mira.rotate(self.rng.uniform(-60, 60) * dt)   # mira alrededor
            return
        if self.objetivo is None:
            self.objetivo = self.pos + Vector2(self.rng.uniform(60, 160), 0).rotate(self.rng.uniform(0, 360))
        hacia = self.objetivo - self.pos
        if hacia.length() < 5 or not self._avanzar(hacia.normalize(), self.tipo.vel_paseo, dt, mundo):
            self.objetivo = None
            self.pausa = self.rng.uniform(1.0, 3.5)

    # --- máquina de estados ----------------------------------------------------
    def actualizar(self, dt, jugador, mundo):
        """Devuelve "golpe" si este fotograma el animal ha golpeado al jugador."""
        self.tiempo_estado += dt
        self.calma = max(0.0, self.calma - dt)
        hacia_jugador = jugador.pos - self.pos
        lejos = hacia_jugador.length()
        direccion_jugador = hacia_jugador.normalize() if lejos > 0 else Vector2(1, 0)

        if self.estado == "pasta":
            self._pasear(dt, mundo)
            if self.calma == 0 and self.ve_al_jugador(jugador, mundo):
                self.cambiar("persigue" if self.tipo.comportamiento == "persigue" else "alerta")

        elif self.estado == "alerta":
            # Se queda quieto y gira la cabeza hacia el jugador
            girada = self.mira.lerp(direccion_jugador, min(1.0, 4 * dt))
            if girada.length_squared() > 0:
                self.mira = girada.normalize()
            if self.ve_al_jugador(jugador, mundo):
                self.alerta += dt * self.ritmo_de_miedo(jugador, lejos)
            else:
                self.alerta -= dt * 0.5
            if self.alerta >= 1:
                self.alerta = 0
                if self.tipo.comportamiento == "embiste":
                    self.cambiar("amenaza")
                else:
                    self.cambiar("huye")
            elif self.alerta <= 0:
                self.alerta = 0
                self.cambiar("pasta")

        elif self.estado == "huye":
            self._avanzar(-direccion_jugador, self.tipo.vel_huida, dt, mundo, puede_salir=True)
            if not mundo.dentro(self.pos, -self.radio):
                self.retirado = True                         # ha salido del mapa
            elif self.tiempo_estado > 4 and lejos > 350:
                self.calma = CALMA
                self.cambiar("pasta")

        elif self.estado == "amenaza":
            # Quieto, mirando al jugador: da tiempo a apartarse
            self.mira = direccion_jugador
            if self.tiempo_estado > DURACION_AMENAZA:
                self.carga = direccion_jugador        # apunta AHORA y ya no corrige
                self.cambiar("embiste")

        elif self.estado == "embiste":
            self._avanzar(self.carga, self.tipo.vel_huida, dt, mundo)
            if self.toca(jugador):
                self.calma = CALMA
                self.cambiar("pasta")
                return "golpe"
            if self.tiempo_estado > DURACION_EMBESTIDA:
                self.calma = CALMA
                self.cambiar("pasta")

        elif self.estado == "persigue":
            self._avanzar(direccion_jugador, self.tipo.vel_huida, dt, mundo)
            if self.toca(jugador):
                self.cambiar("huye")                         # muerde y se aleja
                return "golpe"
            if self.tiempo_estado > 6 or lejos > 420:
                self.calma = CALMA
                self.cambiar("pasta")
        return None
