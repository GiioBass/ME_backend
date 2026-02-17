# Mecánicas de Generación de Mundo

Este documento detalla cómo funciona y funcionará la generación procedural del mundo en el juego.

## 1. Conceptos Básicos

### La Celdas (location)
La unidad mínima del mapa es una `Location` (celda).
*   **Representación:** Una "habitación", "pantalla" o "cuadrícula" de juego.
*   **Tamaño Logico:** 1x1 coordenadas.
*   **Contenido:** Tiene descripción, items en el suelo, enemigos y salidas (Norte, Sur, Este, Oeste).

### El Chunk
Un `Chunk` es un conjunto agrupado de celdas que se generan al mismo tiempo.
*   **Tamaño Actual:** 5x5 celdas (25 habitaciones).
*   **Propósito:** Generar terreno en bloques para optimizar y dar coherencia (ej: asegurar que un río cruce varias celdas).

## 2. Coordenadas y Navegación

El mundo usa un sistema de coordenadas cartesiano `(x, y, z)`.
*   **X / Y:** Superficie (Norte/Sur, Este/Oeste).
*   **Z:** Profundidad (0 = Superficie, -1 = Sótano/Mazmorra, +1 = Cielo/Torre).

## 3. Generación Infinita (Futuro Inmediato)

Actualmente solo generamos el Chunk inicial `(0,0)` que cubre desde `x=-2` a `x=2`.

**Algoritmo de Expansión:**
Cuando el jugador se mueva a un borde del mapa generado (ej: `x=3`), el sistema detectará que no existe `Location` ahí.
1.  **Detección:** El jugador intenta ir al Este desde `x=2, y=0`.
2.  **Generación:** El sistema calcula que necesito un nuevo Chunk centrado en `x=5`.
3.  **Persistencia:** Se genera el nuevo terreno y se guarda en la base de datos.
4.  **Conexión:** Se conecta la salida Este de `x=2` con la nueva celda `x=3`.

## 4. Estructuras Especiales (Aldeas, Mazmorras)

### Puntos de Interés (POIs)
El generador tendrá una probabilidad (ej: 5%) al generar un Chunk de que contenga una **Estructura Especial**.

*   **Aldeas:**
    *   No se generan procedurally celda a celda (ruido).
    *   Se "estampan" sobre el mapa usando una plantilla predefinida (Blueprint).
    *   Ejemplo: Una aldea de 3x3 celdas reemplaza el bosque que hubiera ahí.

*   **Mazmorras (Dungeons):**
    *   **Entrada:** Una celda en la superficie (Z=0) contiene una "Entrada a Mazmorra".
    *   **Instancia:** Al entrar, el jugador es teletransportado a `(x=0, y=0, z=-100)` (una zona aislada en profundidad).
    *   **Regeneración:** Como mencionaste en tus ideas, las mazmorras pueden tener un ID único de instancia. Si se reinicia, se borran las celdas de ese Z y se generan nuevas.

## 5. Resumen de Flujo
1.  Jugador: `go north`
2.  Sistema: ¿Existe location en `(x, y+1)`?
    *   **Sí:** Mover jugador.
    *   **No:** Llamar a `WorldGenerator`.
        *   Determinar Bioma (basado en ruido Perlin o aleatorio).
        *   Generar Chunk de 5x5.
        *   Colocar enemigos/items.
        *   Guardar en DB.
        *   Mover jugador.
