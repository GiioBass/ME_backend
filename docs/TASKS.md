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
- [ ] **Áreas Estáticas**
    - [ ] Implementar carga de áreas desde archivos JSON/YAML (Pueblos, Casa del Jugador).
    - [ ] Crear el "Hub" central o pueblo inicial.

## 2. Sistema de Items e Inventario
- [ ] **Entidades de Items**
    - [ ] Definir tipos de items: `Weapon`, `Armor`, `Consumable`, `Material`.
    - [ ] Atributos: Peso, valor, durabilidad, efectos.
- [ ] **Mecánicas de Inventario**
    - [ ] Implementar comando `take [item]` y `drop [item]`.
    - [ ] Implementar comando `inventory` (listar items).
    - [ ] Implementar límites de inventario (peso o slots).
- [ ] **Persistencia de Items**
    - [ ] Guardar inventario del jugador en base de datos/repositorio.
    - [ ] Guardar items tirados en el suelo (en `Location`).

## 3. Sistema de Combate y Stats
- [ ] **Atributos del Jugador**
    - [ ] Refinar Stats: Fuerza, Agilidad, Inteligencia.
    - [ ] Implementar cálculo de HP/MP basado en stats y nivel.
- [ ] **Enemigos (Mobs)**
    - [ ] Crear entidad `Enemy`.
    - [ ] Spawne de enemigos en localizaciones peligrosas.
- [ ] **Ciclo de Combate**
    - [ ] Implementar comandos `attack [enemy]`.
    - [ ] Sistema de turnos simple (Tu atacas -> Enemigo ataca).
    - [ ] Fórmula de daño (Ataque vs Defensa).
    - [ ] Loot al derrotar enemigos (XP y objetos).

## 4. Persistencia y Base de Datos
- [x] **Migración a Base de Datos Real**
    - [x] Reemplazar `InMemoryGameRepository` con SQLite (Implementado).
    - [x] Usar SQLModel para ORM (Implementado).
    - [ ] Migrar a PostgreSQL o MySQL para producción (Futuro).
- [ ] **Guardado y Carga**
    - [ ] Asegurar que el estado del jugador se guarde tras cada acción crítica.

## 5. Sistema de Eventos y Tiempo
- [ ] **Game Loop / Ticks**
    - [ ] Implementar paso del tiempo (Día/Noche).
    - [ ] Eventos periódicos (Regeneración de vida, respawn de recursos).

## 6. API y Frontend (Futuro)
- [ ] **Mejorar Respuestas API**
    - [ ] Estandarizar respuestas de error.
    - [ ] Incluir lista de acciones válidas en cada respuesta (`available_actions`).
- [ ] **Autenticación**
    - [ ] Login/Registro de usuarios (JWT).

## 7. Multijugador (Largo Plazo)
- [ ] Websockets para chat y eventos en tiempo real.
- [ ] Sistema de Party/Grupos.
