"""
Carga del catálogo de fósiles desde datos/fosiles.csv.

Columnas:
    id                -> número único
    nombre            -> nombre común ("Uro")
    nombre_cientifico -> nombre científico ("Bos primigenius")
    forma             -> dibujo del fósil en casillas: filas separadas por "/",
                         X = hay hueso, . = vacío.   Ej.: "XX/XX" es un cuadrado 2x2
    color             -> color en formato #rrggbb para cuando se completa
    siempre           -> 1 si aparece en todas las excavaciones, 0 si se sortea
    descripcion       -> texto de la ficha
"""

import csv
from pathlib import Path

COLUMNAS = ["id", "nombre", "nombre_cientifico", "forma", "color", "siempre", "descripcion"]


class TipoFosil:
    """Un tipo de fósil del catálogo (no una pieza concreta enterrada)."""

    def __init__(self, id, nombre, nombre_cientifico, forma, color, siempre, descripcion):
        self.id = id
        self.nombre = nombre
        self.nombre_cientifico = nombre_cientifico
        self.forma = forma            # lista de (fila, columna) ocupadas
        self.color = color            # tupla (r, g, b)
        self.siempre = siempre
        self.descripcion = descripcion

    def __repr__(self):
        return f"TipoFosil({self.nombre!r}, {len(self.forma)} casillas)"


def leer_forma(texto):
    """'X.X/XXX' -> [(0,0), (0,2), (1,0), (1,1), (1,2)]"""
    celdas = []
    for f, fila in enumerate(texto.strip().split("/")):
        for c, caracter in enumerate(fila):
            if caracter not in "X.":
                raise ValueError(f"carácter {caracter!r} no válido (solo X y .)")
            if caracter == "X":
                celdas.append((f, c))
    if not celdas:
        raise ValueError("la forma no tiene ninguna X")
    return celdas


def leer_color(texto):
    """'#d9a441' -> (217, 164, 65)"""
    texto = texto.strip().lstrip("#")
    if len(texto) != 6:
        raise ValueError(f"color {texto!r} no válido, usa #rrggbb")
    return tuple(int(texto[i:i + 2], 16) for i in (0, 2, 4))


def cargar_fosiles(ruta):
    ruta = Path(ruta)
    with open(ruta, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        raise ValueError(f"{ruta.name} está vacío")
    faltan = [c for c in COLUMNAS if c not in filas[0]]
    if faltan:
        raise ValueError(f"A {ruta.name} le faltan las columnas: {', '.join(faltan)}")

    fosiles, errores = [], []
    for numero, fila in enumerate(filas, start=2):
        try:
            fosiles.append(
                TipoFosil(
                    id=fila["id"].strip(),
                    nombre=fila["nombre"].strip(),
                    nombre_cientifico=fila["nombre_cientifico"].strip(),
                    forma=leer_forma(fila["forma"]),
                    color=leer_color(fila["color"]),
                    siempre=fila["siempre"].strip() == "1",
                    descripcion=fila["descripcion"].strip(),
                )
            )
        except ValueError as e:
            errores.append(f"fila {numero}: {e}")
    if errores:
        raise ValueError("Errores en los datos:\n  " + "\n  ".join(errores))
    return fosiles


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent
    for t in cargar_fosiles(base / "datos" / "fosiles.csv"):
        print(f"{len(t.forma)} casillas  {t.nombre} ({t.nombre_cientifico})")
