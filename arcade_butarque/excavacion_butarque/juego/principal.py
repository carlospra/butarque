"""
EXCAVACIÓN EN EL ESTANQUE DE TORMENTAS — minijuego del Arcade de Butarque

Entre 2006 y 2007, durante las obras del Estanque de Tormentas de Butarque,
apareció un colmillo de elefante antiguo de casi 4 metros junto a uros, bisontes,
caballos, herramientas de sílex... Ahora te toca excavar a ti.

Cómo se juega:
  - Haz clic en un cuadro de la cuadrícula para excavarlo (gasta 1 golpe de paleta).
  - Si sale tierra, el número dice cuántos cuadros de alrededor esconden hueso.
  - Si sale hueso, sigue excavando alrededor hasta destapar el fósil entero:
    entonces se añade al cuaderno de campo con su ficha.
  - Ganas si recuperas todos los fósiles antes de quedarte sin golpes.
  - R: nueva excavación · ESC: salir · clic en el cuaderno: ver una ficha

Ejecutar desde la carpeta del proyecto:  python main.py
En el navegador: ver README (pygbag).
"""

import asyncio
import random
import sys
from pathlib import Path

import pygame

from datos import cargar_fosiles
from excavacion import Yacimiento

# ---------------------------------------------------------------- configuración
BASE = Path(__file__).resolve().parent.parent
RUTA_DATOS = BASE / "datos" / "fosiles.csv"

ANCHO, ALTO = 1280, 720
FPS = 60
FILAS, COLUMNAS = 9, 14
CASILLA = 52
REJILLA_X, REJILLA_Y = 56, 118
FOSILES_SORTEADOS = 6      # además de los marcados con siempre=1
GOLPES_EXTRA = 15          # golpes de margen sobre el número de casillas con hueso

PANEL_X = REJILLA_X + COLUMNAS * CASILLA + 40
PANEL_W = ANCHO - PANEL_X - 30

FONDO = (43, 38, 32)
PAPEL = (243, 234, 216)
TINTA = (45, 38, 30)
OCRE = (217, 164, 65)
GRIS = (140, 128, 112)
VERDE = (91, 154, 91)
ROJO = (196, 85, 63)
TIERRA = [(112, 84, 58), (104, 78, 54)]
TIERRA_EXCAVADA = (196, 170, 130)
HUESO = (236, 226, 200)
HUESO_OSCURO = (176, 160, 128)
COLOR_PISTA = {1: (52, 92, 140), 2: (46, 112, 64), 3: (160, 64, 44), 4: (110, 52, 130)}


# ---------------------------------------------------------------- utilidades
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


def crear_baldosa_tierra(indice):
    """Una casilla de tierra con algunas piedrecillas (siempre las mismas)."""
    sup = pygame.Surface((CASILLA, CASILLA))
    sup.fill(TIERRA[indice % 2])
    rng = random.Random(indice)
    for _ in range(6):
        x, y = rng.randrange(4, CASILLA - 4), rng.randrange(4, CASILLA - 4)
        pygame.draw.circle(sup, (88, 66, 46), (x, y), rng.choice([1, 2, 2, 3]))
    return sup


def dibujar_hueso(pantalla, rect, color):
    """Un huesito sencillo: una barra con dos bolitas en cada extremo."""
    a = (rect.x + 15, rect.bottom - 15)
    b = (rect.right - 15, rect.y + 15)
    pygame.draw.line(pantalla, color, a, b, 7)
    for (x, y) in (a, b):
        pygame.draw.circle(pantalla, color, (x - 3, y + 1), 5)
        pygame.draw.circle(pantalla, color, (x + 1, y - 3), 5)


# ---------------------------------------------------------------- juego
class Juego:
    def __init__(self, catalogo):
        self.catalogo = catalogo
        self.pantalla = pygame.display.get_surface()
        self.f_titulo = pygame.font.Font(None, 46)
        self.f_normal = pygame.font.Font(None, 26)
        self.f_peq = pygame.font.Font(None, 21)
        self.f_pista = pygame.font.Font(None, 40)
        self.f_ficha = pygame.font.Font(None, 34)
        self.f_italica = pygame.font.Font(None, 24)
        self.f_italica.set_italic(True)
        # 40 baldosas distintas para que la tierra no se vea repetida
        self.baldosas = [crear_baldosa_tierra(i) for i in range(40)]
        self.nueva_excavacion()

    def nueva_excavacion(self):
        fijos = [t for t in self.catalogo if t.siempre]
        resto = [t for t in self.catalogo if not t.siempre]
        tipos = fijos + random.sample(resto, min(FOSILES_SORTEADOS, len(resto)))
        self.yac = Yacimiento(FILAS, COLUMNAS, tipos, golpes_extra=GOLPES_EXTRA)
        self.golpes_iniciales = self.yac.golpes
        self.ficha = None              # fósil cuya ficha se enseña
        self.aviso = "Elige un cuadro para empezar a excavar."
        self.aviso_color = PAPEL
        self.destello = 0              # fotogramas que dura el resaltado de un hallazgo

    # --- coordenadas -----------------------------------------------------------
    def rect_casilla(self, f, c):
        return pygame.Rect(REJILLA_X + c * CASILLA, REJILLA_Y + f * CASILLA, CASILLA, CASILLA)

    def casilla_en(self, pos):
        c = (pos[0] - REJILLA_X) // CASILLA
        f = (pos[1] - REJILLA_Y) // CASILLA
        return (f, c) if self.yac.dentro(f, c) else None

    @staticmethod
    def nombre_cuadro(f, c):
        return f"{chr(ord('A') + c)}{f + 1}"

    def filas_cuaderno(self):
        """Rectángulos de cada línea del cuaderno de campo (para dibujar y para clicar)."""
        return [
            (fosil, pygame.Rect(PANEL_X, 150 + i * 28, PANEL_W, 26))
            for i, fosil in enumerate(self.yac.fosiles)
        ]

    # --- eventos ---------------------------------------------------------------
    def manejar(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for fosil, rect in self.filas_cuaderno():
                if rect.collidepoint(evento.pos) and fosil.completo():
                    self.ficha = fosil
                    return
            casilla = self.casilla_en(evento.pos)
            if casilla:
                self.excavar(*casilla)
        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_r:
            self.nueva_excavacion()

    def excavar(self, f, c):
        resultado = self.yac.excavar(f, c)
        cuadro = self.nombre_cuadro(f, c)
        if resultado["tipo"] == "ignorada":
            return
        if resultado["completado"]:
            fosil = resultado["completado"]
            self.ficha = fosil
            self.destello = 45
            self.aviso, self.aviso_color = f"¡Hallazgo completo en {cuadro}: {fosil.tipo.nombre}!", OCRE
        elif resultado["tipo"] == "fosil":
            self.aviso, self.aviso_color = f"Aparece hueso en {cuadro}. Sigue excavando alrededor.", HUESO
        else:
            n = self.yac.pista(f, c)
            if n:
                self.aviso = f"Tierra en {cuadro}. Hay restos en {n} cuadro(s) de alrededor."
            else:
                self.aviso = f"Tierra en {cuadro}. Nada cerca: se despeja la zona."
            self.aviso_color = PAPEL

        if self.yac.ganada():
            self.aviso = f"¡Excavación completa! Te han sobrado {self.yac.golpes} golpes. R para otra."
            self.aviso_color = VERDE
        elif self.yac.terminada():
            self.aviso = "Te has quedado sin golpes. Mira dónde estaban los restos. R para otra."
            self.aviso_color = ROJO

    # --- dibujo ----------------------------------------------------------------
    def texto(self, cadena, fuente, color, **posicion):
        sup = fuente.render(cadena, True, color)
        self.pantalla.blit(sup, sup.get_rect(**posicion))

    def dibujar(self):
        p = self.pantalla
        p.fill(FONDO)
        self.texto("Excavación en el Estanque de Tormentas", self.f_titulo, OCRE, topleft=(40, 24))
        self.texto(
            "Butarque, 2006-2007. Recupera los fósiles antes de quedarte sin golpes de paleta.",
            self.f_normal, PAPEL, topleft=(42, 64),
        )
        self.dibujar_rejilla()
        self.dibujar_cuaderno()
        self.dibujar_barra_inferior()
        pygame.display.flip()

    def dibujar_rejilla(self):
        p, yac = self.pantalla, self.yac
        # Etiquetas de la cuadrícula arqueológica: letras arriba, números a la izquierda
        for c in range(COLUMNAS):
            self.texto(chr(ord("A") + c), self.f_peq, GRIS,
                       midbottom=(REJILLA_X + c * CASILLA + CASILLA // 2, REJILLA_Y - 4))
        for f in range(FILAS):
            self.texto(str(f + 1), self.f_peq, GRIS,
                       midright=(REJILLA_X - 8, REJILLA_Y + f * CASILLA + CASILLA // 2))

        raton = self.casilla_en(pygame.mouse.get_pos())
        for f in range(FILAS):
            for c in range(COLUMNAS):
                r = self.rect_casilla(f, c)
                fosil = yac.ocupante[f][c]
                if not yac.excavada[f][c]:
                    p.blit(self.baldosas[(f * 7 + c * 3) % len(self.baldosas)], r)
                    if yac.terminada() and fosil:      # al acabar se enseña lo que faltaba
                        dibujar_hueso(p, r, HUESO_OSCURO)
                elif fosil:
                    if fosil.completo():
                        brillo = self.destello > 0 and fosil is self.ficha and self.destello % 10 < 5
                        pygame.draw.rect(p, OCRE if brillo else fosil.tipo.color, r)
                    else:
                        pygame.draw.rect(p, TIERRA_EXCAVADA, r)
                    dibujar_hueso(p, r, HUESO)
                else:
                    pygame.draw.rect(p, TIERRA_EXCAVADA, r)
                    n = yac.pista(f, c)
                    if n:
                        color = COLOR_PISTA.get(n, COLOR_PISTA[4])
                        self.texto(str(n), self.f_pista, color, center=r.center)
                pygame.draw.rect(p, FONDO, r, width=1)

        # Contorno de los fósiles completos, para ver su forma
        for fosil in yac.fosiles:
            if fosil.completo():
                for f, c in fosil.celdas:
                    r = self.rect_casilla(f, c)
                    for (df, dc), a, b in (
                        ((-1, 0), r.topleft, r.topright), ((1, 0), r.bottomleft, r.bottomright),
                        ((0, -1), r.topleft, r.bottomleft), ((0, 1), r.topright, r.bottomright),
                    ):
                        if (f + df, c + dc) not in fosil.celdas:
                            pygame.draw.line(p, PAPEL, a, b, 3)

        if raton and not yac.excavada[raton[0]][raton[1]] and not yac.terminada():
            pygame.draw.rect(p, OCRE, self.rect_casilla(*raton), width=3)

    def dibujar_cuaderno(self):
        p = self.pantalla
        encontrados = sum(1 for f in self.yac.fosiles if f.completo())
        self.texto("Cuaderno de campo", self.f_ficha, OCRE, topleft=(PANEL_X, REJILLA_Y - 6))
        self.texto(f"{encontrados} de {len(self.yac.fosiles)}", self.f_normal, GRIS,
                   topright=(PANEL_X + PANEL_W, REJILLA_Y))

        for fosil, rect in self.filas_cuaderno():
            n = len(fosil.celdas)
            if fosil.completo():
                pygame.draw.rect(p, fosil.tipo.color, (rect.x, rect.y + 4, 16, 16), border_radius=3)
                color = OCRE if fosil is self.ficha else PAPEL
                self.texto(fosil.tipo.nombre, self.f_normal, color, topleft=(rect.x + 26, rect.y + 4))
            else:
                pygame.draw.rect(p, GRIS, (rect.x, rect.y + 4, 16, 16), width=2, border_radius=3)
                pista = f"??? · {n} cuadro{'s' if n > 1 else ''}"
                if fosil.encontradas:
                    pista += f" ({len(fosil.encontradas)} a la vista)"
                self.texto(pista, self.f_normal, GRIS, topleft=(rect.x + 26, rect.y + 4))

        # Ficha del fósil seleccionado
        y0 = 150 + len(self.yac.fosiles) * 28 + 18
        ficha = pygame.Rect(PANEL_X, y0, PANEL_W, REJILLA_Y + FILAS * CASILLA - y0)
        pygame.draw.rect(p, PAPEL, ficha, border_radius=10)
        if not self.ficha:
            for i, linea in enumerate(partir_texto(
                "Cuando destapes un fósil entero, aquí aparecerá su ficha.", self.f_normal, PANEL_W - 32
            )):
                self.texto(linea, self.f_normal, GRIS, topleft=(ficha.x + 16, ficha.y + 16 + i * 22))
            return
        tipo = self.ficha.tipo
        pygame.draw.rect(p, tipo.color, (ficha.x, ficha.y, ficha.w, 10),
                         border_top_left_radius=10, border_top_right_radius=10)
        self.texto(tipo.nombre, self.f_ficha, TINTA, topleft=(ficha.x + 16, ficha.y + 22))
        self.texto(tipo.nombre_cientifico, self.f_italica, TINTA, topleft=(ficha.x + 16, ficha.y + 52))
        y = ficha.y + 84
        for linea in partir_texto(tipo.descripcion, self.f_normal, PANEL_W - 32):
            if y > ficha.bottom - 24:
                break
            self.texto(linea, self.f_normal, TINTA, topleft=(ficha.x + 16, y))
            y += 22

    def dibujar_barra_inferior(self):
        p = self.pantalla
        y = REJILLA_Y + FILAS * CASILLA + 22
        ancho_total = COLUMNAS * CASILLA
        proporcion = self.yac.golpes / self.golpes_iniciales
        color = VERDE if proporcion > 0.4 else OCRE if proporcion > 0.15 else ROJO
        pygame.draw.rect(p, (70, 62, 52), (REJILLA_X, y, ancho_total, 14), border_radius=7)
        pygame.draw.rect(p, color, (REJILLA_X, y, round(ancho_total * proporcion), 14), border_radius=7)
        self.texto(f"Golpes de paleta: {self.yac.golpes}", self.f_normal, PAPEL,
                   topleft=(REJILLA_X, y + 22))
        self.texto("R: nueva excavación" if EN_WEB else "R: nueva excavación · ESC: salir", self.f_peq, GRIS,
                   topright=(REJILLA_X + ancho_total, y + 24))
        self.texto(self.aviso, self.f_normal, self.aviso_color, topleft=(REJILLA_X, y + 52))

    def actualizar(self):
        if self.destello > 0:
            self.destello -= 1



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
        catalogo = cargar_fosiles(RUTA_DATOS)
    except (OSError, ValueError) as error:
        await pantalla_de_error(f"No se ha podido cargar el catálogo de fósiles:\n{error}")

    pygame.init()
    pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Excavación en el Estanque de Tormentas")
    reloj = pygame.time.Clock()
    juego = Juego(catalogo)

    while True:
        for evento in pygame.event.get():
            if quiere_salir(evento):
                pygame.quit()
                return
            juego.manejar(evento)
        juego.actualizar()
        juego.dibujar()
        reloj.tick(FPS)
        await asyncio.sleep(0)   # imprescindible en la web: devuelve el control al navegador
