"""
Lógica de la excavación. NO usa pygame: se puede probar y entender por separado.

La cuadrícula es una matriz de filas x columnas. Cada casilla puede:
  - tener un trozo de fósil o no tenerlo  (self.ocupante)
  - estar excavada o no                   (self.excavada)

Al excavar una casilla vacía se muestra una PISTA: cuántas de las 8 casillas
de alrededor esconden un trozo de fósil (como en el buscaminas, pero aquí
lo que buscas es justo lo que hay "debajo").
Si la pista es 0, se excavan solas las de alrededor (excavado en cadena).
"""

import random
from collections import deque


class Fosil:
    """Una pieza concreta enterrada en la cuadrícula."""

    def __init__(self, tipo, celdas):
        self.tipo = tipo
        self.celdas = set(celdas)     # {(fila, col), ...}
        self.encontradas = set()

    def completo(self):
        return self.encontradas == self.celdas


def girar(forma):
    """Gira una forma 90 grados y la vuelve a pegar a la esquina (0, 0)."""
    girada = [(c, -f) for f, c in forma]
    min_f = min(f for f, _ in girada)
    min_c = min(c for _, c in girada)
    return [(f - min_f, c - min_c) for f, c in girada]


class Yacimiento:
    def __init__(self, filas, columnas, tipos, golpes_extra=15, rng=None):
        self.filas = filas
        self.columnas = columnas
        self.rng = rng or random.Random()
        self.ocupante = [[None] * columnas for _ in range(filas)]
        self.excavada = [[False] * columnas for _ in range(filas)]
        self.fosiles = []
        for tipo in tipos:
            self._enterrar(tipo)
        total = sum(len(f.celdas) for f in self.fosiles)
        self.golpes = total + golpes_extra

    # --- preparación ----------------------------------------------------------
    def _enterrar(self, tipo):
        """Coloca el fósil en un sitio libre al azar, con un giro al azar."""
        for _ in range(1000):
            forma = tipo.forma
            for _ in range(self.rng.randrange(4)):
                forma = girar(forma)
            alto = max(f for f, _ in forma) + 1
            ancho = max(c for _, c in forma) + 1
            f0 = self.rng.randrange(self.filas - alto + 1)
            c0 = self.rng.randrange(self.columnas - ancho + 1)
            celdas = [(f0 + f, c0 + c) for f, c in forma]
            if all(self.ocupante[f][c] is None for f, c in celdas):
                fosil = Fosil(tipo, celdas)
                for f, c in celdas:
                    self.ocupante[f][c] = fosil
                self.fosiles.append(fosil)
                return
        raise RuntimeError(f"No cabe {tipo.nombre} en la cuadrícula")

    # --- consultas ----------------------------------------------------------
    def dentro(self, f, c):
        return 0 <= f < self.filas and 0 <= c < self.columnas

    def vecinas(self, f, c):
        for df in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if (df or dc) and self.dentro(f + df, c + dc):
                    yield f + df, c + dc

    def pista(self, f, c):
        """Número de casillas vecinas con fósil."""
        return sum(1 for vf, vc in self.vecinas(f, c) if self.ocupante[vf][vc])

    def ganada(self):
        return all(fosil.completo() for fosil in self.fosiles)

    def terminada(self):
        return self.ganada() or self.golpes <= 0

    # --- acción -------------------------------------------------------------
    def excavar(self, f, c):
        """
        Excava una casilla. Devuelve un diccionario con lo que ha pasado:
            {"tipo": "ignorada" | "tierra" | "fosil", "completado": Fosil o None}
        """
        if self.terminada() or not self.dentro(f, c) or self.excavada[f][c]:
            return {"tipo": "ignorada", "completado": None}

        self.golpes -= 1
        fosil = self.ocupante[f][c]
        if fosil:
            self.excavada[f][c] = True
            fosil.encontradas.add((f, c))
            return {"tipo": "fosil", "completado": fosil if fosil.completo() else None}

        self._excavar_en_cadena(f, c)
        return {"tipo": "tierra", "completado": None}

    def _excavar_en_cadena(self, f, c):
        """Recorrido en anchura: destapa todas las casillas vacías conectadas con pista 0."""
        pendientes = deque([(f, c)])
        while pendientes:
            f, c = pendientes.popleft()
            if self.excavada[f][c] or self.ocupante[f][c]:
                continue
            self.excavada[f][c] = True
            if self.pista(f, c) == 0:
                pendientes.extend(self.vecinas(f, c))
