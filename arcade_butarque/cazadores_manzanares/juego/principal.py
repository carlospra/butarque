"""
CAZADORES DEL MANZANARES — minijuego del Arcade de Butarque

Hace unos 150.000 años, grupos neandertales usaban la llanura de inundación de Butarque
para cazar, despiezar y aprovechar la carne y el tuétano de sus presas. Eres uno de ellos.

Controles:
  Flechas o WASD   moverse
  SHIFT            acechar (más lento, pero te ven y te oyen desde más cerca)
  ESPACIO          cazar la presa que tienes al lado (gasta 1 sílex)
  TAB o V          mostrar u ocultar los conos de visión de los animales
  ENTER            empezar / continuar      ESC salir (solo en el ordenador)

Ejecutar desde la carpeta del proyecto:  python main.py
En el navegador: ver README (pygbag).
"""

import asyncio
import math
import random
import sys
from collections import Counter
from pathlib import Path

import pygame
from pygame.math import Vector2

from config import (ALTO, ANCHO, ANGULO_VISTA, FACTOR_HIERBA, FACTOR_SIGILO, FPS, HUD_ALTO)
from datos import cargar
from partida import Partida

CARPETA_DATOS = Path(__file__).resolve().parent.parent / "datos"

# Paleta
FONDO = (43, 38, 32)
PAPEL = (243, 234, 216)
TINTA = (45, 38, 30)
OCRE = (217, 164, 65)
GRIS = (140, 128, 112)
VERDE = (91, 154, 91)
ROJO = (196, 85, 63)
LLANURA = (150, 146, 92)
HIERBA = (104, 122, 62)
AGUA = (74, 112, 140)
AGUA_CLARA = (110, 148, 170)
GRAVA = (196, 182, 146)
ARBOL = (54, 80, 48)
PIEL = (200, 156, 116)


def partir_texto(texto, fuente, ancho_max):
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if fuente.size(prueba)[0] <= ancho_max:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def oscurecer(color, f=0.65):
    return tuple(int(c * f) for c in color)


class TextoFlotante:
    def __init__(self, texto, pos, color):
        self.texto, self.pos, self.color, self.vida = texto, Vector2(pos), color, 1.6


class Juego:
    def __init__(self, niveles):
        self.niveles = niveles
        self.pantalla = pygame.display.get_surface()
        self.f_grande = pygame.font.Font(None, 56)
        self.f_titulo = pygame.font.Font(None, 40)
        self.f_normal = pygame.font.Font(None, 27)
        self.f_peq = pygame.font.Font(None, 22)
        self.f_icono = pygame.font.Font(None, 34)
        self.f_italica = pygame.font.Font(None, 25)
        self.f_italica.set_italic(True)
        self.ver_conos = True
        self.indice = 0
        self.preparar_nivel()

    # --- flujo de pantallas ----------------------------------------------------
    def preparar_nivel(self):
        self.partida = Partida(self.niveles[self.indice], random.Random())
        self.fondo = self.dibujar_fondo()
        self.capa_hierba = self.dibujar_capa_hierba()
        self.textos = []
        self.pantalla_actual = "intro"

    def manejar(self, evento):
        if evento.type != pygame.KEYDOWN:
            return
        if evento.key in (pygame.K_TAB, pygame.K_v):
            self.ver_conos = not self.ver_conos
        if self.pantalla_actual == "intro" and evento.key == pygame.K_RETURN:
            self.pantalla_actual = "jugando"
        elif self.pantalla_actual == "jugando" and evento.key == pygame.K_SPACE:
            self.mostrar_eventos(self.partida.cazar())
        elif self.pantalla_actual == "fin" and evento.key == pygame.K_RETURN:
            if self.partida.ganada:
                self.indice = (self.indice + 1) % len(self.niveles)   # tras el último, vuelta a empezar
            self.preparar_nivel()

    def leer_controles(self):
        teclas = pygame.key.get_pressed()
        d = Vector2(
            (teclas[pygame.K_RIGHT] or teclas[pygame.K_d]) - (teclas[pygame.K_LEFT] or teclas[pygame.K_a]),
            (teclas[pygame.K_DOWN] or teclas[pygame.K_s]) - (teclas[pygame.K_UP] or teclas[pygame.K_w]),
        )
        sigilo = teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT]
        return d, bool(sigilo)

    def actualizar(self, dt, direccion=None, sigilo=None):
        if self.pantalla_actual != "jugando":
            return
        if direccion is None:
            direccion, sigilo = self.leer_controles()
        self.mostrar_eventos(self.partida.actualizar(dt, direccion, sigilo))
        for t in self.textos:
            t.vida -= dt
            t.pos.y -= 30 * dt
        self.textos = [t for t in self.textos if t.vida > 0]
        if self.partida.terminada:
            self.pantalla_actual = "fin"

    def mostrar_eventos(self, eventos):
        colores = {"silex": PAPEL, "caza": OCRE, "golpe": ROJO, "sin_silex": ROJO}
        for e in eventos:
            self.textos.append(TextoFlotante(e.texto, e.pos + Vector2(0, -30), colores.get(e.tipo, PAPEL)))

    # --- fondo (se dibuja una vez por nivel) -------------------------------------
    def dibujar_fondo(self):
        m = self.partida.mundo
        sup = pygame.Surface((ANCHO, ALTO))
        sup.fill(LLANURA)
        rng = random.Random(1)
        for _ in range(900):   # textura de la llanura
            x, y = rng.randrange(ANCHO), rng.randrange(HUD_ALTO, ALTO)
            pygame.draw.circle(sup, (138, 136, 84), (x, y), rng.choice([1, 2]))
        for c, r in m.hierba:
            pygame.draw.circle(sup, HIERBA, c, r)
        # Río: polígono desde el borde ondulado hasta el lado derecho
        borde = [(m.borde_rio(y), y) for y in range(HUD_ALTO, ALTO + 10, 10)]
        grava = [(x - 48, y) for x, y in borde]
        pygame.draw.polygon(sup, GRAVA, grava + [(ANCHO, ALTO), (ANCHO, HUD_ALTO)])
        pygame.draw.polygon(sup, AGUA, borde + [(ANCHO, ALTO), (ANCHO, HUD_ALTO)])
        pygame.draw.lines(sup, AGUA_CLARA, False, borde, 4)
        # Arroyo Butarque
        puntos = [(p.x, p.y) for p in m.arroyo]
        pygame.draw.lines(sup, GRAVA, False, puntos, 34)
        pygame.draw.lines(sup, AGUA, False, puntos, 24)
        for p in puntos:
            pygame.draw.circle(sup, AGUA, p, 12)
        for c, r in m.arboles:
            pygame.draw.circle(sup, (40, 60, 36), c + Vector2(3, 4), r)
            pygame.draw.circle(sup, ARBOL, c, r)
            pygame.draw.circle(sup, (72, 104, 62), c - Vector2(r / 4, r / 4), r / 2)
        # Rótulos al final, para que ningún árbol los tape
        etiqueta = self.f_peq.render("arroyo Butarque", True, PAPEL)
        x = 20
        y = min(m.arroyo, key=lambda q: abs(q.x - 90)).y
        sup.blit(etiqueta, (x, y + 18))
        rio = self.f_normal.render("río Manzanares", True, PAPEL)
        rio = pygame.transform.rotate(rio, 90)
        sup.blit(rio, (ANCHO - 60, ALTO // 2 - rio.get_height() // 2))
        return sup

    def dibujar_capa_hierba(self):
        """Capa semitransparente que se pinta ENCIMA de todo: lo que está en la hierba se ve tapado."""
        capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        for c, r in self.partida.mundo.hierba:
            pygame.draw.circle(capa, (*HIERBA, 120), c, r)
        rng = random.Random(2)
        for c, r in self.partida.mundo.hierba:
            for _ in range(int(r / 3)):
                p = c + Vector2(rng.uniform(0, r * 0.9), 0).rotate(rng.uniform(0, 360))
                pygame.draw.line(capa, (78, 96, 44, 200), p, p + Vector2(rng.uniform(-3, 3), -9), 2)
        return capa

    # --- dibujo -------------------------------------------------------------------
    def texto(self, cadena, fuente, color, **pos):
        sup = fuente.render(cadena, True, color)
        self.pantalla.blit(sup, sup.get_rect(**pos))
        return sup.get_rect(**pos)

    def dibujar(self):
        p = self.pantalla
        p.blit(self.fondo, (0, 0))
        partida = self.partida
        j = partida.jugador

        for s in partida.silex:
            pygame.draw.polygon(p, (232, 230, 222), [s + Vector2(0, -7), s + Vector2(6, 5), s + Vector2(-6, 5)])
            pygame.draw.polygon(p, (90, 90, 96), [s + Vector2(0, -7), s + Vector2(6, 5), s + Vector2(-6, 5)], 1)

        if self.ver_conos:
            self.dibujar_conos()
        cazable = partida.animal_cazable()
        for a in partida.animales:
            self.dibujar_animal(a, a is cazable)
        self.dibujar_jugador()
        p.blit(self.capa_hierba, (0, 0))

        if cazable:
            self.texto("ESPACIO: cazar", self.f_peq, OCRE, midbottom=(cazable.pos.x, cazable.pos.y - cazable.radio - 22))
        for t in self.textos:
            self.texto(t.texto, self.f_normal, t.color, center=t.pos)

        self.dibujar_hud()
        if self.pantalla_actual == "intro":
            self.dibujar_intro()
        elif self.pantalla_actual == "fin":
            self.dibujar_fin()
        pygame.display.flip()

    def dibujar_conos(self):
        """Dibuja hasta dónde ve cada animal AHORA MISMO (depende de si acechas o estás en la hierba)."""
        capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        j, m = self.partida.jugador, self.partida.mundo
        factor = (FACTOR_SIGILO if j.sigilo else 1) * (FACTOR_HIERBA if m.en_hierba(j.pos) else 1)
        for a in self.partida.animales:
            if a.estado not in ("pasta", "alerta") or a.calma > 0:
                continue
            alcance = a.tipo.vista * factor
            puntos = [a.pos] + [a.pos + a.mira.rotate(g) * alcance for g in range(-ANGULO_VISTA, ANGULO_VISTA + 1, 10)]
            relleno = (240, 200, 90, 50) if a.estado == "alerta" else (255, 255, 240, 20)
            borde = (240, 200, 90, 150) if a.estado == "alerta" else (255, 255, 240, 70)
            pygame.draw.polygon(capa, relleno, puntos)
            pygame.draw.polygon(capa, borde, puntos, 1)
        self.pantalla.blit(capa, (0, 0))

    def dibujar_animal(self, a, resaltado):
        p = self.pantalla
        color = a.tipo.color
        r = a.radio
        cabeza = a.pos + a.mira * r * 0.95
        pygame.draw.circle(p, oscurecer(color, 0.4), a.pos + Vector2(2, 3), r)          # sombra
        pygame.draw.circle(p, color, a.pos, r)
        pygame.draw.circle(p, oscurecer(color), a.pos, r, 2)
        pygame.draw.circle(p, color, cabeza, r * 0.55)
        pygame.draw.circle(p, oscurecer(color), cabeza, r * 0.55, 2)
        if a.tipo.comportamiento == "embiste":     # cuernos
            lado = a.mira.rotate(90) * r * 0.45
            for s in (1, -1):
                pygame.draw.line(p, (230, 220, 196), cabeza + lado * s, cabeza + lado * s * 1.6 + a.mira * r * 0.35, 3)
        if resaltado:
            pygame.draw.circle(p, OCRE, a.pos, r + 6, 3)
        # Indicador de estado sobre la cabeza
        arriba = (a.pos.x, a.pos.y - r - 4)
        if a.estado == "alerta":
            rect = pygame.Rect(0, 0, 26, 26)
            rect.midbottom = arriba
            pygame.draw.arc(p, OCRE, rect, math.pi / 2, math.pi / 2 + 2 * math.pi * a.alerta, 4)
            self.texto("!", self.f_icono, OCRE, center=rect.center)
        elif a.estado == "huye":
            self.texto("!", self.f_icono, PAPEL, midbottom=arriba)
        elif a.estado == "amenaza":
            temblor = Vector2(math.sin(a.tiempo_estado * 60) * 3, 0)
            self.texto("!!", self.f_icono, ROJO, midbottom=Vector2(arriba) + temblor)
            pygame.draw.circle(p, ROJO, a.pos, r + 6, 2)
        elif a.estado in ("embiste", "persigue"):
            self.texto("!!", self.f_icono, ROJO, midbottom=arriba)

    def dibujar_jugador(self):
        j = self.partida.jugador
        if j.invulnerable > 0 and int(j.invulnerable * 10) % 2 == 0:
            return    # parpadea después de un golpe
        r = j.radio - (3 if j.sigilo else 0)
        p = self.pantalla
        pygame.draw.circle(p, (60, 50, 40), j.pos + Vector2(2, 3), r)
        pygame.draw.circle(p, (110, 78, 50), j.pos, r)                       # piel de abrigo
        pygame.draw.circle(p, PAPEL, j.pos, r + 3, 2)                        # aro para distinguirlo
        pygame.draw.circle(p, PIEL, j.pos + j.mira * 3, r * 0.6)             # cabeza
        punta = j.pos + j.mira * (r + 16)
        pygame.draw.line(p, (120, 90, 60), j.pos - j.mira * 8, punta, 3)     # lanza de madera
        pygame.draw.polygon(p, (232, 230, 222), [punta + j.mira * 7, punta + j.mira.rotate(90) * 4,
                                                  punta + j.mira.rotate(-90) * 4])

    def dibujar_hud(self):
        p, partida, j = self.pantalla, self.partida, self.partida.jugador
        pygame.draw.rect(p, FONDO, (0, 0, ANCHO, HUD_ALTO))
        nivel = partida.nivel
        self.texto(f"Día {nivel.numero}: {nivel.titulo}", self.f_normal, OCRE, midleft=(20, HUD_ALTO // 2))
        x = 470
        self.texto(f"Provisiones {j.provisiones}/{nivel.objetivo}", self.f_normal, PAPEL, midleft=(x, HUD_ALTO // 2))
        self.texto(f"Sílex {j.silex}", self.f_normal, PAPEL if j.silex else ROJO, midleft=(x + 200, HUD_ALTO // 2))
        self.texto("Energía", self.f_normal, PAPEL, midleft=(x + 300, HUD_ALTO // 2))
        for i in range(3):
            color = ROJO if i < j.energia else (80, 70, 60)
            pygame.draw.circle(p, color, (x + 395 + i * 22, HUD_ALTO // 2), 8)
        # El sol recorre la barra: cuando llega al final se hace de noche
        barra = pygame.Rect(ANCHO - 230, HUD_ALTO // 2 - 5, 200, 10)
        pygame.draw.rect(p, (70, 62, 52), barra, border_radius=5)
        avance = 1 - partida.tiempo / nivel.duracion
        pygame.draw.rect(p, OCRE if avance < 0.8 else ROJO, (barra.x, barra.y, barra.w * avance, barra.h), border_radius=5)
        pygame.draw.circle(p, (250, 210, 90), (barra.x + barra.w * avance, barra.centery), 9)
        if self.partida.jugador.sigilo:
            self.texto("acechando", self.f_peq, VERDE, midtop=(j.pos.x, j.pos.y + j.radio + 6))

    def panel(self, alto):
        velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        velo.fill((20, 17, 14, 170))
        self.pantalla.blit(velo, (0, 0))
        rect = pygame.Rect(0, 0, 760, alto)
        rect.center = (ANCHO // 2, ALTO // 2 + 20)
        pygame.draw.rect(self.pantalla, PAPEL, rect, border_radius=14)
        return rect

    def parrafo(self, texto, fuente, color, x, y, ancho):
        for linea in partir_texto(texto, fuente, ancho):
            self.texto(linea, fuente, color, topleft=(x, y))
            y += fuente.get_linesize() + 2
        return y

    def dibujar_intro(self):
        nivel = self.partida.nivel
        r = self.panel(470)
        self.texto(f"Día {nivel.numero} de {len(self.niveles)}", self.f_normal, GRIS, topleft=(r.x + 36, r.y + 30))
        self.texto(nivel.titulo, self.f_grande, TINTA, topleft=(r.x + 36, r.y + 58))
        y = self.parrafo(nivel.texto, self.f_normal, TINTA, r.x + 36, r.y + 120, r.w - 72)
        y = self.parrafo(f"Objetivo: reunir {nivel.objetivo} provisiones antes de que anochezca.",
                         self.f_normal, OCRE, r.x + 36, y + 14, r.w - 72)
        controles = [("Flechas / WASD", "moverse"), ("SHIFT", "acechar: más lento pero más difícil de ver"),
                     ("ESPACIO", "cazar la presa de al lado (gasta 1 sílex)"), ("TAB o V", "ver u ocultar los conos de visión")]
        y += 14
        for tecla, accion in controles:
            self.texto(tecla, self.f_peq, TINTA, topleft=(r.x + 36, y))
            self.texto(accion, self.f_peq, GRIS, topleft=(r.x + 190, y))
            y += 24
        self.texto("Pulsa ENTER para empezar", self.f_normal, OCRE, midbottom=(r.centerx, r.bottom - 22))

    def dibujar_fin(self):
        partida = self.partida
        r = self.panel(400)
        if partida.ganada:
            ultimo = self.indice == len(self.niveles) - 1
            titulo = "¡Tu grupo pasará el invierno!" if ultimo else "¡Provisiones conseguidas!"
            self.texto(titulo, self.f_grande, VERDE, topleft=(r.x + 36, r.y + 30))
            cuenta = Counter(t.nombre for t in partida.cazados)
            resumen = ", ".join(f"{n} × {c}" if c > 1 else n for n, c in cuenta.items())
            y = self.parrafo(f"Has cazado: {resumen}.", self.f_normal, TINTA, r.x + 36, r.y + 100, r.w - 72)
            estrella = max(partida.cazados, key=lambda t: t.valor)
            self.texto("¿Sabías que...?", self.f_titulo, OCRE, topleft=(r.x + 36, y + 16))
            self.texto(estrella.nombre_cientifico, self.f_italica, GRIS, topleft=(r.x + 36, y + 52))
            self.parrafo(estrella.dato, self.f_normal, TINTA, r.x + 36, y + 80, r.w - 72)
            siguiente = "ENTER para volver a empezar" if ultimo else "ENTER para el día siguiente"
        else:
            self.texto("La partida ha terminado", self.f_grande, ROJO, topleft=(r.x + 36, r.y + 30))
            y = self.parrafo(partida.motivo_derrota(), self.f_normal, TINTA, r.x + 36, r.y + 100, r.w - 72)
            self.parrafo(f"Has reunido {partida.jugador.provisiones} de {partida.nivel.objetivo} provisiones. "
                         "Consejo: acércate a las presas por detrás y por la hierba alta, acechando con SHIFT.",
                         self.f_normal, TINTA, r.x + 36, y + 12, r.w - 72)
            siguiente = "ENTER para intentarlo de nuevo"
        self.texto(siguiente, self.f_normal, OCRE, midbottom=(r.centerx, r.bottom - 22))



# ---------------------------------------------------------------- web / escritorio
# pygbag ejecuta el juego en el navegador con Python compilado a WebAssembly.
# Allí sys.platform vale "emscripten". No existe "cerrar la ventana", así que
# ESC y el aviso de salida se ignoran, y los errores se enseñan en pantalla
# porque nadie ve la consola.
EN_WEB = sys.platform == "emscripten"


def quiere_salir(evento):
    if EN_WEB:
        return False
    return evento.type == pygame.QUIT or (
        evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE
    )


async def pantalla_de_error(texto):
    print(texto)
    if not EN_WEB:
        sys.exit(1)
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    fuente = pygame.font.Font(None, 28)
    while True:
        pantalla.fill((43, 38, 32))
        for i, linea in enumerate(texto.splitlines()):
            pantalla.blit(fuente.render(linea, True, (243, 234, 216)), (40, 40 + i * 32))
        pygame.display.flip()
        pygame.event.pump()
        await asyncio.sleep(0)

async def main():
    try:
        _, niveles = cargar(CARPETA_DATOS)
    except (OSError, ValueError) as error:
        await pantalla_de_error(f"No se han podido cargar los datos:\n{error}")

    pygame.init()
    pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Cazadores del Manzanares")
    reloj = pygame.time.Clock()
    juego = Juego(niveles)
    while True:
        dt = min(reloj.tick(FPS) / 1000, 0.05)   # segundos; se limita por si el PC se atasca
        for evento in pygame.event.get():
            if quiere_salir(evento):
                pygame.quit()
                return
            juego.manejar(evento)
        juego.actualizar(dt)
        juego.dibujar()
        await asyncio.sleep(0)   # imprescindible en la web: devuelve el control al navegador
