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

## 4. Áreas Estáticas (Carga desde JSON)

Para lugares fijos que no deben ser generados aleatoriamente (como el Hub inicial "Oakfield Hub", pueblos importantes o casas de jugadores), el sistema utiliza archivos JSON.

### Cómo funciona (`StaticAreaLoader`)
1.  **Definición:** Las áreas estáticas se definen en `app/data/static_areas.json`.
2.  **Estructura del JSON:**
    ```json
    {
      "id": "loc_0_0_0",
      "name": "Oakfield Hub",
      "description": "Una descripción detallada del lugar.",
      "coordinates": { "x": 0, "y": 0, "z": 0 },
      "interactables": ["forge", "wagon"],
      "exits": {}
    }
    ```
3.  **Sobrescritura Genérica:** Cuando el `GameService` genera un nuevo "Chunk" (usando el `WorldGenerator`), el `StaticAreaLoader` escanea el chunk recién generado. Si encuentra que las coordenadas del chunk coinciden con las de una locación en el JSON (ej. `x=0, y=0, z=0`), sobrescribe el nombre, descripción y otros atributos con los datos del JSON, convirtiendo esa celda procedural en una fija.

Este enfoque permite mantener el mapa coherente: los alrededores siguen siendo generados dinámicamente, pero los puntos clave que diseñes en el JSON siempre estarán exactamente donde dictan sus coordenadas.

## 5. Estructuras Especiales (Puntos de Interés Dinámicos y Blueprints)

### Puntos de Interés (POIs) - *Blueprints*
El generador tiene una probabilidad (por defecto 5%) al poblar una celda de que esta se convierta en una **Estructura Especial** (Punto de Interés dinámico).

Para ello, utilizamos el sistema de **Blueprints (Plantillas JSON)**:
1.  **Definición (`app/data/blueprints.json`):** Los posibles POIs se detallan en un JSON independiente (ej: "Campamento de Bandidos", "Santuario Místico"). Cada uno define su nombre, biomas permitidos, y listas de enemigos e ítems garantizados.
2.  **Carga (`BlueprintLoader`):** Esta clase lee el JSON y expone las plantillas disponibles.
3.  **Generación Dinámica (`WorldGenerator`):** Si toca generar un POI, el generador rola un Blueprint válido para el bioma actual. Si sale premiado, la celda asimila el nombre y descripción del Blueprint y además **se le instancian inmediatamente** los ítems y enemigos definidos en él.
4.  **Persistencia:** Como todo esto ocurre justo en la generación procedural de la celda antes de guardarla en base de datos, el Punto de Interés (con sus enemigos y botines *custom*) se vuelve 100% persistente por defecto.

*   **Mazmorras (Dungeons):**
    *   **Entrada:** Una celda en la superficie (Z=0) contiene una "Entrada a Mazmorra".
    *   **Instancia:** Al entrar, el jugador es teletransportado a `(x=0, y=0, z=-100)` (una zona aislada en profundidad).
    *   **Regeneración:** Como mencionaste en tus ideas, las mazmorras pueden tener un ID único de instancia. Si se reinicia, se borran las celdas de ese Z y se generan nuevas.

## 6. Resumen de Flujo
1.  Jugador: `go north`
2.  Sistema: ¿Existe location en `(x, y+1)`?
    *   **Sí:** Mover jugador.
    *   **No:** Llamar a `WorldGenerator`.
        *   Determinar Bioma (basado en ruido Perlin o aleatorio).
        *   Generar Chunk de 5x5 alrededor o adyacente.
        *   `StaticAreaLoader` inyecta locaciones del JSON si coinciden las coordenadas.
        *   Colocar enemigos/items en celdas no-estáticas.
        *   Guardar todo en DB.
        *   Mover jugador.
