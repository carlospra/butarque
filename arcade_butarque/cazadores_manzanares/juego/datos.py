"""
Carga de datos/animales.csv y datos/niveles.csv.

El contenido (qué animales hay, cómo se comportan, cuántos salen en cada nivel)
se cambia en los CSV, sin tocar el código.
"""

import csv
from pathlib import Path

COLUMNAS_ANIMALES = ["id", "nombre", "nombre_cientifico", "tipo", "comportamiento", "tamano",
                     "color", "vista", "nervio", "vel_paseo", "vel_huida", "valor", "dato"]
COLUMNAS_NIVELES = ["nivel", "titulo", "objetivo", "duracion", "hierba", "arboles",
                    "silex_inicial", "silex_rio", "animales", "texto"]
COMPORTAMIENTOS = {"huye", "embiste", "persigue"}


class TipoAnimal:
    def __init__(self, fila):
        self.id = fila["id"].strip()
        self.nombre = fila["nombre"].strip()
        self.nombre_cientifico = fila["nombre_cientifico"].strip()
        self.tipo = fila["tipo"].strip()                    # presa | depredador
        self.comportamiento = fila["comportamiento"].strip()
        self.tamano = int(fila["tamano"])                   # radio en píxeles
        self.color = leer_color(fila["color"])
        self.vista = float(fila["vista"])                   # alcance de la vista en píxeles
        self.nervio = float(fila["nervio"])                 # segundos que tarda en reaccionar
        self.vel_paseo = float(fila["vel_paseo"])           # píxeles por segundo
        self.vel_huida = float(fila["vel_huida"])
        self.valor = int(fila["valor"])                     # provisiones que aporta
        self.dato = fila["dato"].strip()
        if self.comportamiento not in COMPORTAMIENTOS:
            raise ValueError(f"comportamiento {self.comportamiento!r} desconocido")
        if self.tipo not in ("presa", "depredador"):
            raise ValueError(f"tipo {self.tipo!r} debe ser presa o depredador")

    def __repr__(self):
        return f"TipoAnimal({self.id})"


class Nivel:
    def __init__(self, fila, catalogo):
        self.numero = int(fila["nivel"])
        self.titulo = fila["titulo"].strip()
        self.objetivo = int(fila["objetivo"])
        self.duracion = float(fila["duracion"])
        self.hierba = int(fila["hierba"])
        self.arboles = int(fila["arboles"])
        self.silex_inicial = int(fila["silex_inicial"])
        self.silex_rio = int(fila["silex_rio"])
        self.texto = fila["texto"].strip()
        # "caballo:4;ciervo:2" -> [(TipoAnimal caballo, 4), (TipoAnimal ciervo, 2)]
        self.animales = []
        for parte in fila["animales"].split(";"):
            ident, cantidad = parte.split(":")
            if ident.strip() not in catalogo:
                raise ValueError(f"el animal {ident!r} no está en animales.csv")
            self.animales.append((catalogo[ident.strip()], int(cantidad)))


def leer_color(texto):
    texto = texto.strip().lstrip("#")
    if len(texto) != 6:
        raise ValueError(f"color {texto!r} no válido, usa #rrggbb")
    return tuple(int(texto[i:i + 2], 16) for i in (0, 2, 4))


def _leer(ruta, columnas):
    with open(ruta, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        raise ValueError(f"{Path(ruta).name} está vacío")
    faltan = [c for c in columnas if c not in filas[0]]
    if faltan:
        raise ValueError(f"A {Path(ruta).name} le faltan las columnas: {', '.join(faltan)}")
    return filas


def cargar(carpeta):
    """Devuelve (catalogo, niveles). catalogo es un diccionario id -> TipoAnimal."""
    carpeta = Path(carpeta)
    errores, catalogo, niveles = [], {}, []
    for n, fila in enumerate(_leer(carpeta / "animales.csv", COLUMNAS_ANIMALES), start=2):
        try:
            tipo = TipoAnimal(fila)
            catalogo[tipo.id] = tipo
        except (ValueError, TypeError) as e:
            errores.append(f"animales.csv fila {n}: {e}")
    for n, fila in enumerate(_leer(carpeta / "niveles.csv", COLUMNAS_NIVELES), start=2):
        try:
            niveles.append(Nivel(fila, catalogo))
        except (ValueError, TypeError) as e:
            errores.append(f"niveles.csv fila {n}: {e}")
    if errores:
        raise ValueError("Errores en los datos:\n  " + "\n  ".join(errores))
    niveles.sort(key=lambda nv: nv.numero)
    return catalogo, niveles


if __name__ == "__main__":
    cat, niv = cargar(Path(__file__).resolve().parent.parent / "datos")
    for t in cat.values():
        print(f"{t.nombre:20} {t.tipo:11} {t.comportamiento:9} vista={t.vista:.0f}")
    for nv in niv:
        print(f"Nivel {nv.numero}: {nv.titulo} -> {[(t.id, n) for t, n in nv.animales]}")
