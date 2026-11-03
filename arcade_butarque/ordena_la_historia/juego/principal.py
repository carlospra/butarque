"""
ORDENA LA HISTORIA DE BUTARQUE — prueba de concepto
Versión digital del puzle de madera de la línea del tiempo (Mesa Comunitaria Habitar Butarque).

Cómo se juega:
  - Arrastra las tarjetas de la mesa a los huecos de la línea del tiempo,
    de la más antigua (izquierda) a la más reciente (derecha).
  - Pulsa "Comprobar" (o la tecla ENTER).
  - Las tarjetas bien colocadas se marcan en verde y las mal colocadas en rojo.
    Puedes moverlas y volver a comprobar.
  - "Otra ronda" (o la tecla R) reparte tarjetas nuevas. ESC para salir (solo en el ordenador).

Ejecutar desde la carpeta del proyecto:  python main.py
En el navegador: ver README (pygbag).
"""

import asyncio
import random
import sys
from pathlib import Path

import pygame

from datos import cargar_hitos

# ---------------------------------------------------------------- configuración
BASE = Path(__file__).resolve().parent.parent
RUTA_DATOS = BASE / "datos" / "hitos.csv"   # también vale un .xlsx con las mismas columnas
CARPETA_FOTOS = BASE / "datos" / "fotos"

ANCHO, ALTO = 1280, 720
FPS = 60
TARJETAS_POR_RONDA = 5

CARTA_W, CARTA_H = 190, 220
FOTO_H = 120
SEPARACION = 20
FILA_LINEA_Y = 110   # fila de huecos (línea del tiempo)
FILA_MESA_Y = 425    # fila donde se reparten las tarjetas

# Paleta "terraza del Manzanares": tierra, ocre, arcilla
FONDO = (43, 38, 32)
FONDO_LINEA = (58, 51, 43)
PAPEL = (243, 234, 216)
TINTA = (45, 38, 30)
OCRE = (217, 164, 65)
VERDE = (91, 154, 91)
ROJO = (196, 85, 63)
GRIS = (140, 128, 112)
BLANCO = (250, 247, 240)


# ---------------------------------------------------------------- utilidades
def partir_texto(texto, fuente, ancho_max):
    """Divide un texto en líneas que caben en ancho_max píxeles."""
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


def cargar_foto(nombre, ancho, alto, fuente):
    """Carga una foto y la recorta para llenar el hueco. Si no existe, dibuja un sustituto."""
    ruta = CARPETA_FOTOS / nombre if nombre else None
    if ruta and ruta.exists():
        imagen = pygame.image.load(str(ruta)).convert()
        escala = max(ancho / imagen.get_width(), alto / imagen.get_height())
        nueva = (round(imagen.get_width() * escala), round(imagen.get_height() * escala))
        imagen = pygame.transform.smoothscale(imagen, nueva)
        recorte = pygame.Rect(0, 0, ancho, alto)
        recorte.center = imagen.get_rect().center
        return imagen.subsurface(recorte).copy()

    # Sustituto: un rectángulo de color con el nombre del archivo que falta
    sustituto = pygame.Surface((ancho, alto))
    sustituto.fill((120, 104, 84))
    pygame.draw.line(sustituto, (140, 124, 102), (0, 0), (ancho, alto), 2)
    pygame.draw.line(sustituto, (140, 124, 102), (0, alto), (ancho, 0), 2)
    for i, linea in enumerate(["sin foto", nombre or ""]):
        txt = fuente.render(linea, True, PAPEL)
        sustituto.blit(txt, txt.get_rect(center=(ancho // 2, alto // 2 - 10 + i * 20)))
    return sustituto


# ---------------------------------------------------------------- tarjeta
class Tarjeta:
    def __init__(self, hito, foto):
        self.hito = hito
        self.foto = foto
        self.rect = pygame.Rect(0, 0, CARTA_W, CARTA_H)
        self.x, self.y = 0.0, 0.0     # posición real (para animar)
        self.destino = (0.0, 0.0)     # adónde se está moviendo
        self.casa = (0, 0)            # su sitio en la mesa
        self.hueco = None             # índice del hueco en la línea, o None si está en la mesa
        self.estado = None            # None, "bien" o "mal" después de comprobar

    def mover_a(self, x, y, al_instante=False):
        self.destino = (x, y)
        if al_instante:
            self.x, self.y = x, y
            self.rect.topleft = (round(x), round(y))

    def actualizar(self):
        # Se acerca un 25 % a su destino en cada fotograma: movimiento suave
        dx, dy = self.destino
        self.x += (dx - self.x) * 0.25
        self.y += (dy - self.y) * 0.25
        self.rect.topleft = (round(self.x), round(self.y))

    def dibujar(self, pantalla, fuente, levantada=False):
        r = self.rect
        if levantada:  # sombra cuando la arrastramos
            pygame.draw.rect(pantalla, (20, 17, 14), r.move(6, 8), border_radius=10)
        pygame.draw.rect(pantalla, PAPEL, r, border_radius=10)
        pantalla.blit(self.foto, (r.x + 6, r.y + 6))
        y = r.y + FOTO_H + 14
        for linea in partir_texto(self.hito.titulo, fuente, CARTA_W - 16)[:4]:
            txt = fuente.render(linea, True, TINTA)
            pantalla.blit(txt, (r.x + 8, y))
            y += fuente.get_linesize()
        if self.estado:
            color = VERDE if self.estado == "bien" else ROJO
            pygame.draw.rect(pantalla, color, r, width=5, border_radius=10)


# ---------------------------------------------------------------- juego
class Juego:
    def __init__(self, hitos):
        self.hitos = hitos
        self.pantalla = pygame.display.get_surface()
        self.f_titulo = pygame.font.Font(None, 46)
        self.f_normal = pygame.font.Font(None, 26)
        self.f_carta = pygame.font.Font(None, 23)
        self.f_peq = pygame.font.Font(None, 20)

        n = min(TARJETAS_POR_RONDA, len(hitos))
        total = n * CARTA_W + (n - 1) * SEPARACION
        x0 = (ANCHO - total) // 2
        self.columnas = [x0 + i * (CARTA_W + SEPARACION) for i in range(n)]
        self.huecos = [pygame.Rect(x, FILA_LINEA_Y, CARTA_W, CARTA_H) for x in self.columnas]
        self.boton = pygame.Rect(ANCHO - 230, ALTO - 66, 200, 48)
        self.nueva_ronda()

    # --- lógica -------------------------------------------------------------
    def nueva_ronda(self):
        elegidos = random.sample(self.hitos, len(self.huecos))
        self.tarjetas = [
            Tarjeta(h, cargar_foto(h.foto, CARTA_W - 12, FOTO_H, self.f_peq)) for h in elegidos
        ]
        for tarjeta, x in zip(self.tarjetas, self.columnas):
            tarjeta.casa = (x, FILA_MESA_Y)
            tarjeta.x, tarjeta.y = x, ALTO + 50          # empieza fuera de pantalla...
            tarjeta.mover_a(x, FILA_MESA_Y)              # ...y sube a la mesa
        self.orden_correcto = sorted(h.anio for h in elegidos)
        self.arrastrada = None
        self.comprobado = False
        self.intentos = 0

    def tarjeta_en_hueco(self, indice):
        for t in self.tarjetas:
            if t.hueco == indice:
                return t
        return None

    def colocar(self, tarjeta, indice):
        """Pone la tarjeta en el hueco. Si estaba ocupado, intercambia las dos."""
        otra = self.tarjeta_en_hueco(indice)
        if otra and otra is not tarjeta:
            otra.hueco = tarjeta.hueco
            if otra.hueco is None:
                otra.mover_a(*otra.casa)
            else:
                otra.mover_a(self.columnas[otra.hueco], FILA_LINEA_Y)
        tarjeta.hueco = indice
        tarjeta.mover_a(self.columnas[indice], FILA_LINEA_Y)

    def devolver_a_mesa(self, tarjeta):
        tarjeta.hueco = None
        tarjeta.mover_a(*tarjeta.casa)

    def todas_colocadas(self):
        return all(t.hueco is not None for t in self.tarjetas)

    def comprobar(self):
        """Una tarjeta está bien si su año es el que toca en ese hueco (los empates valen)."""
        self.intentos += 1
        for t in self.tarjetas:
            t.estado = "bien" if t.hito.anio == self.orden_correcto[t.hueco] else "mal"
        self.comprobado = True

    def aciertos(self):
        return sum(1 for t in self.tarjetas if t.estado == "bien")

    def olvidar_comprobacion(self):
        for t in self.tarjetas:
            t.estado = None
        self.comprobado = False

    # --- eventos ------------------------------------------------------------
    def tarjeta_bajo(self, pos):
        for t in reversed(self.tarjetas):   # la que está dibujada encima primero
            if t.rect.collidepoint(pos):
                return t
        return None

    def manejar(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.boton.collidepoint(evento.pos):
                self.pulsar_boton()
                return
            t = self.tarjeta_bajo(evento.pos)
            if t:
                self.arrastrada = t
                self.desfase = (t.x - evento.pos[0], t.y - evento.pos[1])
                self.tarjetas.remove(t)
                self.tarjetas.append(t)       # pasa a dibujarse la última (encima)

        elif evento.type == pygame.MOUSEMOTION and self.arrastrada:
            x = evento.pos[0] + self.desfase[0]
            y = evento.pos[1] + self.desfase[1]
            self.arrastrada.mover_a(x, y, al_instante=True)

        elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1 and self.arrastrada:
            t = self.arrastrada
            self.arrastrada = None
            if self.comprobado:
                self.olvidar_comprobacion()   # si mueves algo, hay que volver a comprobar
            destino = next(
                (i for i, h in enumerate(self.huecos) if h.collidepoint(t.rect.center)), None
            )
            if destino is not None:
                self.colocar(t, destino)
            elif t.hueco is not None:
                self.colocar(t, t.hueco)      # vuelve a su hueco
            else:
                self.devolver_a_mesa(t)

        elif evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_RETURN:
                self.pulsar_boton()
            elif evento.key == pygame.K_r:
                self.nueva_ronda()

    def pulsar_boton(self):
        if self.comprobado and self.aciertos() == len(self.tarjetas):
            self.nueva_ronda()
        elif self.todas_colocadas() and not self.comprobado:
            self.comprobar()

    # --- dibujo -------------------------------------------------------------
    def texto(self, cadena, fuente, color, **posicion):
        sup = fuente.render(cadena, True, color)
        self.pantalla.blit(sup, sup.get_rect(**posicion))

    def dibujar(self):
        p = self.pantalla
        p.fill(FONDO)

        self.texto("Ordena la historia de Butarque", self.f_titulo, OCRE, topleft=(40, 24))
        self.texto(
            "Arrastra cada tarjeta a la línea del tiempo, de la más antigua a la más reciente.",
            self.f_normal, PAPEL, topleft=(42, 64),
        )

        # Línea del tiempo con sus huecos
        franja = pygame.Rect(0, FILA_LINEA_Y - 14, ANCHO, CARTA_H + 80)
        pygame.draw.rect(p, FONDO_LINEA, franja)
        y_flecha = FILA_LINEA_Y + CARTA_H + 22
        pygame.draw.line(p, OCRE, (self.columnas[0], y_flecha), (self.columnas[-1] + CARTA_W, y_flecha), 3)
        fin = self.columnas[-1] + CARTA_W
        pygame.draw.polygon(p, OCRE, [(fin + 14, y_flecha), (fin, y_flecha - 8), (fin, y_flecha + 8)])
        self.texto("más antiguo", self.f_peq, GRIS, topright=(self.columnas[0] - 10, y_flecha - 7))
        self.texto("más reciente", self.f_peq, GRIS, topleft=(fin + 18, y_flecha - 7))

        for i, hueco in enumerate(self.huecos):
            pygame.draw.rect(p, GRIS, hueco, width=2, border_radius=10)
            self.texto(str(i + 1), self.f_titulo, GRIS, center=hueco.center)
            t = self.tarjeta_en_hueco(i)
            if self.comprobado and t:
                color = VERDE if t.estado == "bien" else ROJO
                self.texto(t.hito.fecha_texto, self.f_normal, color, midtop=(hueco.centerx, y_flecha + 12))

        self.texto("Mesa", self.f_normal, GRIS, topleft=(40, FILA_MESA_Y - 30))

        # Tarjetas (la arrastrada se dibuja la última)
        for t in self.tarjetas:
            t.dibujar(p, self.f_carta, levantada=(t is self.arrastrada))

        self.dibujar_barra_inferior()
        pygame.display.flip()

    def dibujar_barra_inferior(self):
        p = self.pantalla
        # Descripción de la tarjeta que hay bajo el ratón
        t = self.tarjeta_bajo(pygame.mouse.get_pos())
        if t and not self.arrastrada:
            lineas = partir_texto(f"{t.hito.titulo}: {t.hito.descripcion}", self.f_peq, ANCHO - 320)
            for i, linea in enumerate(lineas[:3]):
                self.texto(linea, self.f_peq, PAPEL, topleft=(40, ALTO - 70 + i * 18))
        elif self.comprobado:
            n, total = self.aciertos(), len(self.tarjetas)
            if n == total:
                msg = f"¡Perfecto! {total} de {total} en {self.intentos} intento(s)."
            else:
                msg = f"{n} de {total} bien colocadas. Mueve las rojas y vuelve a comprobar."
            self.texto(msg, self.f_normal, OCRE, topleft=(40, ALTO - 56))

        # Botón
        if self.comprobado and self.aciertos() == len(self.tarjetas):
            etiqueta, activo = "Otra ronda", True
        else:
            etiqueta, activo = "Comprobar", self.todas_colocadas() and not self.comprobado
        pygame.draw.rect(p, OCRE if activo else GRIS, self.boton, border_radius=8)
        self.texto(etiqueta, self.f_normal, TINTA if activo else FONDO, center=self.boton.center)

    def actualizar(self):
        for t in self.tarjetas:
            if t is not self.arrastrada:
                t.actualizar()
            else:
                t.rect.topleft = (round(t.x), round(t.y))



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
        hitos = cargar_hitos(RUTA_DATOS)
    except (OSError, ValueError) as error:
        await pantalla_de_error(f"No se han podido cargar los hitos:\n{error}")
    if len(hitos) < TARJETAS_POR_RONDA:
        await pantalla_de_error(f"Hacen falta al menos {TARJETAS_POR_RONDA} hitos y solo hay {len(hitos)}.")

    pygame.init()
    pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Ordena la historia de Butarque")
    reloj = pygame.time.Clock()
    juego = Juego(hitos)

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
