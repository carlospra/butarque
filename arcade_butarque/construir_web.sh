#!/usr/bin/env bash
# Construye la versión web de los tres juegos y el portal del arcade en la carpeta _site/
#
#   pip install pygbag==0.9.3
#   bash construir_web.sh
#   python -m http.server -d _site 8000      ->  abrir http://localhost:8000
#
# GitHub Actions ejecuta este mismo script en cada push (ver .github/workflows/web.yml).
# Si pygbag no puede descargar su plantilla (red del centro con filtros), se le puede pasar
# una plantilla local:  PYGBAG_OPCIONES="--template ruta/default.tmpl" bash construir_web.sh

set -euo pipefail
cd "$(dirname "$0")"

# Origen del intérprete de Python en WebAssembly que descargará el navegador.
# NO se usa el CDN por defecto de pygbag 0.9.3 (https://pygame-web.github.io/cdn/0.9.3/):
# en esa ruta falta browserfs.min.js, el juego no se monta y la pantalla se queda vacía
# ("PyMain: BrowserFS not found" en la consola). La misma versión publicada en
# archives/0.9/ está completa. Se puede cambiar con:  PYGBAG_CDN=... bash construir_web.sh
PYGBAG_CDN="${PYGBAG_CDN:-https://pygame-web.github.io/archives/0.9/}"

# carpeta del juego -> ruta en la web
declare -A RUTAS=(
  [ordena_la_historia]=ordena
  [excavacion_butarque]=excavacion
  [cazadores_manzanares]=cazadores
)
declare -A TITULOS=(
  [ordena_la_historia]="Ordena la historia de Butarque"
  [excavacion_butarque]="Excavación en el Estanque de Tormentas"
  [cazadores_manzanares]="Cazadores del Manzanares"
)

rm -rf _site
mkdir -p _site/img
cp web/index.html _site/

for juego in ordena_la_historia excavacion_butarque cazadores_manzanares; do
  echo "==> Construyendo $juego"
  rm -rf "$juego/build"
  (
    cd "$juego"
    # --ume_block 0: arranca sin esperar un clic (los juegos no tienen sonido)
    python -m pygbag --build --ume_block 0 --width 1280 --height 720 \
      --cdn "$PYGBAG_CDN" --title "${TITULOS[$juego]}" ${PYGBAG_OPCIONES:-} .
  )
  mkdir -p "_site/${RUTAS[$juego]}"
  cp -r "$juego/build/web/." "_site/${RUTAS[$juego]}/"
  cp "$juego/docs/captura.png" "_site/img/${RUTAS[$juego]}.png"
done

echo
echo "Web lista en _site/. Para probarla:  python -m http.server -d _site 8000"
