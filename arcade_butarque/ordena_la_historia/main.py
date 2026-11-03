"""
Punto de entrada del juego, igual en el ordenador que en el navegador.

    Ordenador:  python main.py
    Navegador:  pygbag .            (o pygbag --build . para generar la web)

pygbag exige tres cosas, y por eso este archivo es así:
  1. se llama main.py y está en la raíz del proyecto,
  2. el bucle del juego es una función async con "await asyncio.sleep(0)" en cada vuelta,
  3. se arranca con asyncio.run(...).
"""

import asyncio
import sys
from pathlib import Path

try:
    RAIZ = Path(__file__).resolve().parent
except NameError:          # por si el entorno web no define __file__
    RAIZ = Path.cwd()
sys.path.insert(0, str(RAIZ / "juego"))

import principal  # noqa: E402  (tiene que ir después de preparar sys.path)

asyncio.run(principal.main())
