"""
Carga de los hitos de la línea del tiempo.

Los datos viven FUERA del código: en datos/hitos.csv (o directamente en un .xlsx).
Así la Mesa Comunitaria puede añadir o corregir hitos sin tocar Python.

Columnas obligatorias:
    id          -> número único
    anio        -> número entero para ORDENAR (negativo = "hace X años")
    fecha_texto -> lo que se enseña en pantalla ("1957", "2006-2007", "hace ~186.000 años")
    titulo      -> texto corto de la tarjeta
    descripcion -> explicación que aparece al pasar el ratón
    foto        -> nombre del archivo dentro de datos/fotos/ (puede ir vacío)
"""

import csv
from pathlib import Path

COLUMNAS = ["id", "anio", "fecha_texto", "titulo", "descripcion", "foto"]


class Hito:
    """Un acontecimiento de la línea del tiempo."""

    def __init__(self, id, anio, fecha_texto, titulo, descripcion, foto):
        self.id = id
        self.anio = anio
        self.fecha_texto = fecha_texto
        self.titulo = titulo
        self.descripcion = descripcion
        self.foto = foto

    def __repr__(self):
        return f"Hito({self.anio}, {self.titulo!r})"


def _leer_filas_csv(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _leer_filas_xlsx(ruta):
    from openpyxl import load_workbook  # solo se importa si hace falta

    libro = load_workbook(ruta, read_only=True, data_only=True)
    hoja = libro.active
    filas = list(hoja.iter_rows(values_only=True))
    cabecera = [str(c).strip().lower() if c is not None else "" for c in filas[0]]
    return [
        {cabecera[i]: ("" if v is None else str(v)) for i, v in enumerate(fila)}
        for fila in filas[1:]
        if any(v is not None for v in fila)  # saltar filas vacías
    ]


def cargar_hitos(ruta):
    """Devuelve una lista de Hito. Lanza ValueError con mensajes claros si hay errores."""
    ruta = Path(ruta)
    if ruta.suffix.lower() == ".xlsx":
        filas = _leer_filas_xlsx(ruta)
    else:
        filas = _leer_filas_csv(ruta)

    if not filas:
        raise ValueError(f"{ruta.name} no tiene ningún hito")

    faltan = [c for c in COLUMNAS if c not in filas[0]]
    if faltan:
        raise ValueError(f"A {ruta.name} le faltan las columnas: {', '.join(faltan)}")

    hitos = []
    errores = []
    for numero, fila in enumerate(filas, start=2):  # la fila 1 es la cabecera
        try:
            anio = int(float(fila["anio"]))
        except ValueError:
            errores.append(f"fila {numero}: 'anio' debe ser un número y es {fila['anio']!r}")
            continue
        if not fila["titulo"].strip():
            errores.append(f"fila {numero}: el título está vacío")
            continue
        hitos.append(
            Hito(
                id=fila["id"].strip(),
                anio=anio,
                fecha_texto=fila["fecha_texto"].strip() or str(anio),
                titulo=fila["titulo"].strip(),
                descripcion=fila["descripcion"].strip(),
                foto=fila["foto"].strip(),
            )
        )

    if errores:
        raise ValueError("Errores en los datos:\n  " + "\n  ".join(errores))
    return hitos


if __name__ == "__main__":
    # Prueba rápida: python juego/datos.py
    base = Path(__file__).resolve().parent.parent
    for h in sorted(cargar_hitos(base / "datos" / "hitos.csv"), key=lambda h: h.anio):
        print(f"{h.fecha_texto:>20}  {h.titulo}")
