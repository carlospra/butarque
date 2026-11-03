# Butarque · versión estática en GitHub Pages

Versión de demostración del proyecto intermodular Butarque 2026-27 (IES Villaverde, con la Mesa Comunitaria de Butarque), publicada en GitHub Pages:

**https://carlospra.github.io/butarque/**

| Dirección | Qué es |
|---|---|
| `/` | Portada |
| `/mapa/` | Mapa vivo de Butarque: 21 lugares en 5 capas, línea del tiempo, rutas a pie y la ficha de cada punto |
| `/arcade/` | Arcade de Butarque: Ordena la historia, Excavación en el Estanque de Tormentas y Cazadores del Manzanares |

## Qué es y qué no es

GitHub Pages solo sirve **ficheros estáticos**: no ejecuta Python ni PHP y no tiene base de datos. Por eso esta web **no tiene el servidor de contenidos** (FastAPI + SQLite) que lleva la versión en Docker. El mapa lee sus datos de ficheros JSON (`mapa/datos/`), exportados de la API con el KML del 9 de octubre de 2026.

### Limitaciones respecto a la versión en Docker

| En Docker | Aquí |
|---|---|
| Recuerdos del vecindario: formulario, moderación y publicación | No se pueden enviar recuerdos |
| Panel editorial `/admin` con `ADMIN_TOKEN`: editar puntos, publicar u ocultar, añadir fotos y audios, hoja de QR | No hay panel |
| Reimportación desde Google My Maps | Los datos son los del 9 de octubre. Para actualizarlos hay que regenerar `mapa/datos/` y volver a subirlos |
| API REST (`/api/salud`, `/api/puntos?capa=…`, GeoJSON, `hitos.csv`, `/docs`) | Solo ficheros JSON fijos, sin filtros ni clave |
| Enlace a un punto: `/p/<punto>` | Enlace a un punto: `/mapa/?p=<punto>`. Los QR de una versión no sirven en la otra |

### Lo que funciona igual

- Mapa con las 5 capas, línea del tiempo, fichas con fotos y audioguía, las 3 rutas, «Cerca de mí» (con `?simular=1` para probarlo sin salir a la calle), vista de lista y uso sin conexión.
- El Arcade entero: ya era una web estática.
- Al ir por HTTPS, la geolocalización y el modo sin conexión funcionan en el móvil, cosa que en Docker por `http://IP:8090` no pasa.

### A tener en cuenta

- El repositorio y la web son **públicos**.
- Las fotos se cargan desde Google My Maps: si se borran o cambian allí, dejan de verse.
- Las teselas de OpenStreetMap valen para una demostración, no para una aplicación con mucho tráfico.

## Cómo se publica

Cada `git push` a `main` lanza `.github/workflows/pages.yml`, que:

1. pasa las pruebas del Arcade y compila los juegos con pygbag;
2. junta la portada, `mapa/` y el Arcade compilado;
3. sube el resultado a la rama `gh-pages`, que es la que sirve GitHub Pages.

Configuración del repositorio (una sola vez): *Settings → Pages → Source: Deploy from a branch → `gh-pages` / (root)*.

## Estructura

```
butarque/
├── index.html            portada
├── img/                  imagen de la portada
├── mapa/                 Mapa vivo (versión estática)
│   ├── datos/            capas, puntos y rutas en JSON
│   ├── media/            audioguía de prueba (voz sintética)
│   └── vendor/           Leaflet y generador de códigos QR
├── arcade_butarque/      código de los juegos (se compila en GitHub)
└── .github/workflows/    publicación automática
```
