# Arcade de Butarque

Tres minijuegos en Python sobre el yacimiento paleontológico de Butarque (Villaverde, Madrid). Se juegan **en el ordenador** y **en el navegador**, a partir del mismo código.

| Juego | Carpeta | En la web |
|---|---|---|
| Ordena la historia | `ordena_la_historia/` | `/ordena/` |
| Excavación en el Estanque de Tormentas | `excavacion_butarque/` | `/excavacion/` |
| Cazadores del Manzanares | `cazadores_manzanares/` | `/cazadores/` |

## Jugar en el ordenador

```bash
cd ordena_la_historia          # o cualquiera de los otros dos
pip install -r requirements.txt
python main.py
```

## Jugar en el navegador: cómo funciona

Un navegador no ejecuta Python. **pygbag** empaqueta el juego en un archivo `.apk` (un zip con el código y los CSV) y genera un `index.html`. Ese HTML descarga CPython y pygame-ce compilados a **WebAssembly** desde `pygame-web.github.io` y, dentro del navegador, ejecuta el mismo `main.py` que en el ordenador.

```
 navegador ──▶ index.html ──▶ intérprete de Python en WebAssembly (pygame-web.github.io, ~25 MB la primera vez)
                   │
                   └──────▶ juego.apk  (main.py + juego/*.py + datos/*.csv, unos pocos KB)
```

### Los cambios que han hecho falta en el código

| Cambio | Por qué |
|---|---|
| `main.py` en la **raíz** de cada juego; el antiguo `juego/main.py` pasa a llamarse `juego/principal.py` | pygbag busca `main.py` en la carpeta que empaqueta |
| El bucle principal es `async def main()` con `await asyncio.sleep(0)` en cada vuelta, y se arranca con `asyncio.run()` | En el navegador solo hay un hilo. Si el bucle no devuelve el control, la página se congela y no se dibuja nada |
| `EN_WEB = sys.platform == "emscripten"` | En la web no se puede "cerrar la ventana": ESC se ignora y los textos que dicen "ESC: salir" desaparecen |
| Errores de datos en pantalla (`pantalla_de_error`) en lugar de `sys.exit` | En el navegador nadie ve la consola |
| Tecla **V** como alternativa a TAB en *Cazadores* | En muchas páginas TAB mueve el foco fuera del juego. En pygbag funciona, pero así hay un plan B |
| `pygbag.ini` en cada juego | Deja fuera de la web `tests/`, `docs/` y `herramientas/` |

Nada más. La lógica, los CSV y las pruebas no han cambiado. pygbag usa **pygame-ce** en lugar de pygame, y los tres juegos se han probado con los dos.

### Construir la web en local

```bash
pip install pygbag==0.9.3
bash construir_web.sh
python -m http.server -d _site 8000          # abrir http://localhost:8000
```

`construir_web.sh` compila los tres juegos y monta en `_site/` el portal (`web/index.html`) con un enlace a cada uno. Para probar un solo juego mientras se programa: `cd excavacion_butarque && pygbag .` y abrir `http://localhost:8000`.

### Publicar

**GitHub Pages (automático).** Se sube este repositorio a GitHub y se activa *Settings → Pages → Source: GitHub Actions*. En cada `git push` a `main`, el workflow `.github/workflows/web.yml` pasa las pruebas, compila y publica en `https://<usuario>.github.io/<repositorio>/`.

**Cualquier servidor web.** `_site/` son ficheros estáticos: basta con copiarlos a un Apache o nginx del centro, a Netlify o a un bucket. No hace falta ninguna configuración especial.

**itch.io.** `pygbag --build --archive .` genera `build/web.zip`, que se sube tal cual como "HTML game".

## Probar el servidor en local con contenedores

Simula en tu máquina lo que después se desplegará en la nube: un servidor web que entrega los juegos y un navegador que los ejecuta.

```bash
docker compose up --build -d        # la primera vez tarda unos minutos
# abrir http://localhost:8080
docker compose logs -f              # ver las peticiones que llegan al servidor
docker compose down                 # parar
```

**Qué hay dentro.** El `Dockerfile` tiene dos etapas:

1. **Construcción** (`python:3.12-slim`): instala pygbag y ejecuta `construir_web.sh`, que empaqueta cada juego en un `.apk` (código + CSV) y genera sus páginas.
2. **Servidor** (`nginx:1.27-alpine`): solo copia el resultado (unos 400 KB) y lo sirve. La imagen final no lleva Python ni pygbag.

```
 navegador ──HTTP──▶ contenedor nginx (:8080)      portal, index.html y .apk de cada juego
     │
     └────HTTPS──▶ pygame-web.github.io/archives/0.9/   intérprete de Python + pygame en WebAssembly
                                                  (~25 MB la primera vez, luego queda en caché)
```

**El servidor no ejecuta Python.** Python se ejecuta dentro del navegador de cada jugador. El servidor solo entrega ficheros, igual que lo hará S3 + CloudFront o un nginx en EC2. Se puede comprobar en las herramientas de desarrollo del navegador (pestaña *Red*): los `.apk` vienen de `localhost`, y `main.wasm` y `main.data` vienen de `pygame-web.github.io`.

**Detalles de la configuración** (`docker/nginx.conf`):

| Directiva | Para qué |
|---|---|
| `map $http_host $redirigir_a` | Si se entra por `localhost:PUERTO`, redirige a `127.0.0.1:PUERTO`. Con `localhost` y puerto, el intérprete de pygbag activa su modo de desarrollo y busca pygame en `http://localhost:8000/archives/`, que no existe. Con un dominio real esta regla no se activa nunca. |
| `absolute_redirect off` | Las redirecciones (`/ordena` → `/ordena/`) conservan el puerto 8080 publicado por Docker. |
| `map $uri $control_cache` | `.html` y `.apk` con `no-cache`: al recargar se ve siempre la última versión del juego. Imágenes y estilos se guardan una semana. |
| `gzip on` | Las páginas viajan un 60 % más ligeras. Los `.apk` ya son zip y no se recomprimen. |
| Cabeceras `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options` y `server_tokens off` | Endurecimiento básico. Además, no se anuncia la versión de nginx. |
| `location = /salud` | Comprobación de salud que usa el `HEALTHCHECK` de Docker y que, en AWS, usaría el balanceador. |

**Modo desarrollo.** Para no reconstruir la imagen en cada cambio: `bash construir_web.sh` (con pygbag instalado en local) y después `docker compose --profile desarrollo up arcade-dev`. Esto sirve la carpeta `_site/` en `http://localhost:8081`.

**Problemas habituales**

- *El puerto 8080 está ocupado:* cambia `"8080:80"` en `compose.yaml` (por ejemplo, `"8090:80"`).
- *El juego se queda cargando:* el navegador necesita acceso a `pygame-web.github.io`, y la construcción de la imagen también (pygbag descarga su plantilla). Si la red del centro lo filtra, hay que pedir que se autorice ese dominio.
- *Un cambio en un juego no aparece:* `docker compose up --build -d` reconstruye la imagen.
- *El juego carga y la pantalla se queda vacía (en la consola: `PyMain: BrowserFS not found`):* la página usa el intérprete de la ruta por defecto de pygbag 0.9.3 (`pygame-web.github.io/cdn/0.9.3/`), donde falta `browserfs.min.js`. `construir_web.sh` usa la misma versión publicada en `pygame-web.github.io/archives/0.9/`, que está completa. Se elige con la variable `PYGBAG_CDN`.

**Del contenedor a la nube (línea de ASIR).** Hay dos caminos con este mismo trabajo: subir esta imagen a un registro (ECR) y ejecutarla en EC2 o ECS, o publicar solo la carpeta `_site/` en S3 con CloudFront delante. La configuración de nginx documenta lo que habrá que replicar en cualquiera de los dos: cachés, compresión, cabeceras y comprobación de salud.

## Limitaciones de la versión web

- **Necesita internet:** el intérprete se descarga de `pygame-web.github.io`. Si la red del centro bloquea ese dominio, los juegos no cargarán. Para la maquinita de la Raspberry Pi, mejor la versión de escritorio.
- **La primera carga tarda** unos segundos (unos 25 MB); después queda en la caché del navegador.
- **Móvil:** *Ordena* y *Excavación* funcionan con el dedo, aunque en *Ordena* no se ven las descripciones al pasar el ratón. *Cazadores* necesita teclado. Añadir controles táctiles es una buena ampliación para los alumnos.
- **Fotos:** sirven en PNG o JPG. No hay que usar MP3 ni WAV si se añade sonido: en la web solo vale OGG.

## Estructura

```
arcade_butarque/
├── ordena_la_historia/        ┐
├── excavacion_butarque/       ├ cada juego: main.py, pygbag.ini, juego/, datos/, tests/, docs/
├── cazadores_manzanares/      ┘
├── web/index.html             ← portal del arcade
├── construir_web.sh           ← compila todo en _site/
├── Dockerfile                 ← imagen: construcción con pygbag + servidor nginx
├── compose.yaml               ← arranque local (puerto 8080) y modo desarrollo (8081)
├── docker/nginx.conf          ← configuración del servidor web
└── .github/workflows/web.yml  ← publicación automática en GitHub Pages
```
