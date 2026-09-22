# Estado de Progreso y Arquitectura - Mystic Explorers Backend

Este documento resume las 3 fases de saneamiento, modularización e implementación completadas en el backend de **Mystic Explorers**.

---

## 1. Mapeo de Arquitectura ("MVC" Hexagonal)

El backend implementa **Arquitectura Hexagonal (Puertos y Adaptadores)** orientada a API REST:

| Capa MVC Conceptual | Implementación en Mystic Explorers | Archivos Clave |
| :--- | :--- | :--- |
| **Model (M)** | **Entidades de Dominio** (Pydantic) y **Persistencia Relacional** (SQLModel + SQLite). | `app/core/domain/` (`player.py`, `npc.py`, `quest.py`, `skill.py`, `recipe.py`, `location.py`, `item.py`, `enemy.py`) y `app/adapters/driven/persistence/sql_models.py` |
| **View (V)** | **Serializadores y DTOs JSON** de respuesta REST consumidos por el Frontend React/Vite. | `app/adapters/driving/api/routes.py` (`GameResponse`, `serialize_player`, `serialize_inventory`, `available_actions`) |
| **Controller (C)** | **Adaptadores de Entrada HTTP** (FastAPI) y **Casos de Uso Especializados**. | `app/adapters/driving/api/routes.py` y `app/core/use_cases/services/` coordinados por `GameService` |

---

## 2. Fases Ejecutadas

### Fase 1: Limpieza, Organización y Estabilización
- [x] Eliminación de scripts temporales huérfanos (`fix_locations.py`, `fix_routes.py`, `fix_routes2.py`, `test_radar.py`, `start copy.sh`).
- [x] Limpieza de bases de datos residuales obsoletas (`game.db`, `test_drink.db`).
- [x] Unificación de carpetas de datos: todos los esquemas JSON (`blueprints.json`, `static_areas.json`, etc.) ahora residen de manera unificada en `data/`.
- [x] Eliminación de declaraciones duplicadas de `ItemRequest` y `execute_game_action` en `routes.py`.
- [x] Configuración automática de `pytest.ini` (`pythonpath = .`).

### Fase 2: Modularización y Refactorización de Arquitectura
El archivo monolítico `game_service.py` (>1,250 líneas) fue descompuesto en servicios especializados dentro de `app/core/use_cases/services/`:
- **`BaseGameService`**: Lógica común de tiempo, supervivencia y combate de apoyo.
- **`MovementService`**: Movimiento, scout/radar, cuadrantes dinámicos, campamentos y viaje rápido.
- **`CombatService`**: Turnos de combate, armadura, IA de contraataque y drop de botín.
- **`InventoryService`**: Recolección, soltado, equipamiento, límites de peso y cofres de campamento.
- **`SurvivalService`**: Alimentación, hidratación en fuentes, recarga de frascos y descanso.
- **`CraftingService`**: Validación de estaciones de trabajo e ingredientes.
- **`GameService`**: Fachada principal y registro de comandos limpios.

### Fase 3: Implementación de Características Clave

#### 1. Sistema de NPCs, Diálogos y Comercio (`DIALOGUES.md`)
- Entidades de dominio: `NPC`, `DialogueNode`, `DialogueChoice`, `ShopItem`.
- NPCs configurados en Oakfield Hub: **Village Elder**, **Merchant Silas**, **Farmer Ted**.
- Árboles de diálogo con opciones interactivas, cheques condicionales y comandos de salida (`leave`, `exit`, `bye`).
- Catálogo de tienda con compra y venta de items (`buy [item]`, `sell [item]`, `shop`).
- Endpoints REST: `/action/talk`, `/action/dialogue`, `/action/dialogue/end`, `/action/buy`, `/action/sell`.
- Integración Frontend: Modal interactivo de diálogos con soporte de cierre reactivo instantáneo (`DialogueModal`).

#### 2. Sistema de Misiones / Quests (`QUESTS.md`)
- Entidades de dominio: `Quest`, `QuestObjective`, `QuestReward`.
- Misiones principales (*The Awakening*, *The First Darkness*) y secundarias (*The Worried Farmer*).
- Seguimiento automático de objetivos en tiempo real durante combate, recolección y crafteo.
- Entrega de recompensas (XP, Oro, Items) mediante `turnin [quest_id]`.
- Endpoints REST: `/action/quests`, `/action/quest/turnin`.

#### 3. Estaciones de Trabajo para Crafteo (`CRAFTING.md`)
- Campo `required_station` en recetas (`workbench`, `furnace`, `anvil`, `alchemy_table`).
- Validación de interactables requeridos en la ubicación antes de permitir el crafteo.
- Recetas añadidas: Stone Pickaxe, Iron Sword, Health Potion, Mana Potion, Bandages, Torches.
- Endpoint REST: `/action/craft`.

#### 4. Clases y Habilidades de Combate (`SKILLS.md`)
- Clases disponibles: **Fighter** (Luchador), **Marksman** (Tirador), **Mage** (Mago).
- Habilidades activas: *Heavy Strike*, *War Cry*, *Aimed Shot*, *Fireball*, *Mana Shield*.
- Consumo de Maná (MP) / Energía y escalado de daño según estadísticas (Fuerza / Inteligencia).
- Endpoints REST: `/action/class`, `/action/skill`, `/action/skills`.

---

## 3. Estado de Pruebas Automatizadas

Todos los tests unitarios e integrados pasan exitosamente (**33/33 passed**):

```bash
$ pytest
============================== test session starts ===============================
collected 33 items

tests/test_camp_storage.py .                                               [  3%]
tests/test_combat.py ..                                                    [  9%]
tests/test_events.py ..                                                    [ 15%]
tests/test_fast_travel.py ..                                               [ 21%]
tests/test_game_flow.py .                                                  [ 24%]
tests/test_hydration.py ...                                                [ 33%]
tests/test_infinite_gen.py ..                                              [ 39%]
tests/test_inventory.py .                                                  [ 42%]
tests/test_inventory_limits.py .                                           [ 45%]
tests/test_item_system.py ..                                               [ 51%]
tests/test_npcs_and_dialogues.py ..                                        [ 57%]
tests/test_periodic.py .                                                   [ 60%]
tests/test_persistence.py ..                                               [ 66%]
tests/test_quest_system.py .                                               [ 69%]
tests/test_skills_and_classes.py ..                                        [ 75%]
tests/test_survival.py ..                                                  [ 81%]
tests/test_time_system.py ..                                               [ 87%]
tests/test_workstation_crafting.py .                                       [ 90%]
tests/test_world_gen.py .                                                  [ 93%]
tests/test_z_layer.py ..                                                   [100%]

=============================== 33 passed in 1.86s ===============================
```
