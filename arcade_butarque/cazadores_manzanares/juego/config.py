"""Valores compartidos por todos los módulos. Cambiar aquí para ajustar el juego."""

ANCHO, ALTO = 1280, 720
HUD_ALTO = 52                 # barra superior de información
FPS = 60

# Jugador
VEL_NORMAL = 190              # píxeles por segundo
VEL_SIGILO = 85               # con SHIFT pulsado
FRENO_AGUA = 0.5              # en el agua se va a la mitad
ENERGIA = 3
INVULNERABLE = 1.5            # segundos sin recibir daño después de un golpe
ALCANCE_CAZA = 18             # distancia extra entre bordes para poder cazar

# Detección
ANGULO_VISTA = 60             # grados a cada lado de hacia dónde mira el animal
OIDO_NORMAL = 130             # a esta distancia te oyen aunque no te vean
OIDO_SIGILO = 45
FACTOR_SIGILO = 0.55          # agachado te ven desde más cerca
FACTOR_HIERBA = 0.5           # en la hierba alta, aún más cerca

# Animales
REAPARICION = 6.0             # segundos hasta que entra otro animal del mismo tipo
DURACION_AMENAZA = 0.6         # aviso antes de embestir: el animal rasca el suelo
DURACION_EMBESTIDA = 1.1
CALMA = 2.5                   # segundos sin hacer caso tras embestir o dejar de perseguir
# Velocidad a la que se llena la alerta de un animal (multiplica a 1/nervio)
MIEDO_CARRERA = 3.0           # si le ves correr hacia ti
MIEDO_QUIETO = 0.35           # si te quedas inmóvil aunque te mire
MIEDO_CERCANIA = 2.0          # extra cuanto más cerca estás (hasta x3 pegado a él)
