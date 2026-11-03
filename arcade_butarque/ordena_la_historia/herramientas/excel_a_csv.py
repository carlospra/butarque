"""
Convierte el Excel de la línea del tiempo de la Mesa Comunitaria al CSV que usa el juego.

Uso (desde la carpeta del proyecto):
    python herramientas/excel_a_csv.py LineadeltiempoButarque_completa.xlsx

Como no sabemos aún cómo se llaman las columnas del Excel original, el primer paso
del reto es mirar el archivo y rellenar el diccionario CORRESPONDENCIA:
    columna del juego  ->  nombre de la columna en el Excel
"""

import csv
import sys
from pathlib import Path

from openpyxl import load_workbook

# >>> EDITAR AQUÍ después de abrir el Excel <<<
CORRESPONDENCIA = {
    "anio": "Año",
    "fecha_texto": "Fecha",
    "titulo": "Hito",
    "descripcion": "Descripción",
    "foto": "Foto",
}

SALIDA = Path(__file__).resolve().parent.parent / "datos" / "hitos.csv"
COLUMNAS = ["id", "anio", "fecha_texto", "titulo", "descripcion", "foto"]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    hoja = load_workbook(sys.argv[1], read_only=True, data_only=True).active
    filas = list(hoja.iter_rows(values_only=True))
    cabecera = [str(c).strip() if c is not None else "" for c in filas[0]]
    print("Columnas encontradas en el Excel:", cabecera)

    faltan = [c for c in CORRESPONDENCIA.values() if c not in cabecera]
    if faltan:
        print("No encuentro estas columnas; revisa CORRESPONDENCIA:", faltan)
        sys.exit(1)

    posicion = {campo: cabecera.index(col) for campo, col in CORRESPONDENCIA.items()}
    salida = []
    for fila in filas[1:]:
        if all(v is None for v in fila):
            continue
        registro = {"id": len(salida) + 1}
        for campo, i in posicion.items():
            valor = fila[i]
            registro[campo] = "" if valor is None else str(valor).strip()
        salida.append(registro)

    with open(SALIDA, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(salida)
    print(f"{len(salida)} hitos guardados en {SALIDA}")


if __name__ == "__main__":
    main()
