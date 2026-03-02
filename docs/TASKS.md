# Lista de Tareas del Proyecto (Backlog)

Esta lista detalla las tareas pendientes para evolucionar el prototipo actual hacia la visión completa descrita en `GAME_DESIGN.md`.

## 1. Expansión del Mundo (World Generation)
- [ ] **Sistema de Generación Procedural**
    - [x] Crear algoritmo para generar "Chunks" o áreas conectadas dinámicamente.
    - [x] Definir biomas (Bosque, Desierto, Mazmorra).
    - [x] Create algoritmo para generar "Chunks" o áreas conectadas dinámicamente.
    - [x] Definir biomas (Bosque, Desierto, Mazmorra).
    - [x] Implementar persistencia de áreas generadas (para que no cambien al volver).
    - [x] Implementar Generación Infinita (Expansión Dinámica). <!-- id: 11 -->
- [x] **Áreas Estáticas y Especiales**
    - [x] Implementar carga de áreas estáticas desde JSON (Pueblos, Casa del Jugador).
    - [x] Crear el "Hub" central o pueblo inicial (Oakfield Hub).
    - [x] Refactorización de tests y organización de archivos.
    - [x] Implementar sistema de Blueprints (Plantillas JSON) para Puntos de Interés Dinámicos generados procedimentalmente con enemigos y botín.
    - [x] Translate blueprint names and descriptions to English.
- [ ] **Expansión de Generación del Mundo (Nuevos features)**
    - [ ] Generación procedural de Pueblos/Villas.
    - [ ] Agregar NPCs (Non-Playable Characters) interactuables/comerciantes.
    - [x] Generación procedural de Mazmorras (Dungeons).
    - [x] Actualizar acción `scout` (radar) para detectar entradas de mazmorras.
    - [x] Actualizar acción `scout` dentro de mazmorras para señalar la salida a la superficie.
    - [x] Jefes de Mazmorra (Bosses) requeridos para desbloquear el paso al siguiente piso.
    - [x] Tipos de Mazmorras (50% farmeables con regeneración / 50% instanciadas hardcore).
    - [x] Objetos de Iluminación (Antorchas, Velas, Lámparas) y oscuridad mecánica.
    - [x] Integración de Trampas en Capa Z < 0.
    - [ ] Generación de cuerpos de agua (ríos, lagos, pozos) en la superficie (Capa Z = 0).
- [x] **Mecánicas de Supervivencia - Hidratación:**
    - [x] Separar consumibles: Comida solo restaura hambre (y regenera HP%), Agua/Bebidas solo restaura sed.
    - [x] Añadir Frascos/Botellas de agua (Water Flask) y acción para rellenarlos en fuentes de agua.

## 2. Sistema de Items e Inventario
- [x] **Entidades de Items**
    - [x] Definición de tipos de items (Weapon, Armor, Consumable, Material).
    - [x] Atributos (Weight, Value, Durability, Effects).
- [x] **Gestión de Inventario**
    - [x] Backend: Listar, Agrupar, Equipar, Desequipar, Soltar.
    - [x] Frontend: Modal de Inventario funcional.
- [x] **Consumibles**
    - [x] Lógica de efectos (HP, Hambre, Sed).
    - [x] Botón de acción "Consume" funcional en el frontend.
    - [x] Refinar visualización de estados en Bio-Metrics (Colores dinámicos).
- [ ] **Mecánicas de Inventario**
    - [x] Implementar comando `take [item]` y `drop [item]`.
    - [x] Implementar comando `inventory` (listar items).
    - [x] Implementar límites de inventario (peso o slots).
- [ ] **Persistencia de Items**
    - [x] Guardar inventario del jugador en base de datos/repositorio.
    - [x] Guardar items tirados en el suelo (en `Location`).

- [x] Combat System
    - [x] Define Enemy Entity <!-- id: 15 -->
    - [x] Update Location/Player for Combat <!-- id: 16 -->
    - [x] Implement Attack Command & Combat Logic <!-- id: 17 -->
    - [x] Update World Gen with Enemies <!-- id: 18 -->

- [x] Event System & Time
    - [x] Implement WorldState Persistence <!-- id: 19 -->
    - [x] Implement Game Loop / Ticks <!-- id: 20 -->
    - [x] Implement Periodic Events (Heal, Respawn) <!-- id: 21 -->

## 4. Persistencia y Base de Datos
- [x] Reestructurar Base de Datos (Normalización)
    - [x] Separar PlayerStats, Inventario y Equipo en tablas dedicadas
    - [x] Normalizar Location (Exits, Items, Enemies, Coords en columnas)
    - [x] Refactorizar SQLGameRepository para el nuevo esquema
    - [x] Optimizar `get_location_by_coordinates`
    - [x] Verificar con tests automatizados (+26 tests) del jugador se guarde tras cada acción crítica.

## 5. Sistema de Eventos y Tiempo
- [x] **Game Loop / Ticks**
    - [x] Implementar paso del tiempo (Día/Noche).
    - [x] Eventos periódicos (Regeneración de vida, respawn de recursos).

## 6. API y Frontend
- [x] **Documentación Frontend**
    - [x] Documentar uso de UI y comandos (USER_MANUAL.md en inglés).
- [x] **Mejorar Respuestas API**
    - [x] Estandarizar respuestas de error.
    - [x] Incluir lista de acciones válidas en cada respuesta (`available_actions`).
- [x] **Autenticación Validación**
    - [x] Prevenir creación de personaje si el nombre ya existe (`/start`).
    - [x] Mostrar mensaje de error si se intenta cargar personaje inexistente (`/login`).

## 7. Multijugador (Largo Plazo)
- [ ] Websockets para chat y eventos en tiempo real.
- [ ] Sistema de Party/Grupos.
