# Arquitectura y Plan de Implementación Multijugador (MUD / Realtime)

Este documento detalla la especificación técnica, arquitectura y desglose de tareas para transformar el juego en una experiencia multijugador en tiempo real.

---

## 1. Evaluación de Viabilidad y Estado Actual

- **Viabilidad Técnica**: Muy Alta (85% de la base ya desacoplada).
- **Modelo Actual**: Cliente-Servidor REST (FastAPI + React). La base de datos SQLite ya centraliza el estado del mundo, items en el suelo y enemigos por coordenadas.
- **Transición**: Evolución a arquitectura híbrida **REST + WebSockets** (MUD Moderno).

---

## 2. Componentes de la Arquitectura

### A. Gestor de Conexiones en Tiempo Real (`ConnectionManager`)
* **Ubicación**: `app/api/websocket/connection_manager.py`
* **Responsabilidad**:
  - Mantener diccionario en memoria de conexiones activas: `active_connections[player_id] = WebSocket`.
  - Mapeo de jugadores por sala/coordenadas: `room_members[location_id] = Set[player_id]`.
  - Métodos de difusión (*broadcasting*):
    - `broadcast_to_room(location_id, event_type, data, exclude_player_id)`
    - `broadcast_global(event_type, data)`
    - `send_direct_message(player_id, event_type, data)`

### B. Protocolo de Mensajería WebSocket
Todos los mensajes se estructuran en formato JSON estandarizado:

```json
{
  "event": "ROOM_EVENT",
  "subtype": "PLAYER_ENTERED",
  "timestamp": 1726982400,
  "data": {
    "player_id": "p-123",
    "player_name": "Alden",
    "direction": "south",
    "message": "Alden ha llegado desde el norte."
  }
}
```

#### Tipos de Eventos Principales:
1. **Presencia y Movimiento**:
   - `PLAYER_JOINED_ROOM`: Se emite cuando un jugador entra a la casilla actual.
   - `PLAYER_LEFT_ROOM`: Se emite cuando un jugador sale de la casilla.
2. **Chat y Comunicación**:
   - `CHAT_SAY`: Mensaje local (solo visible en la misma casilla).
   - `CHAT_SHOUT`: Mensaje global (para todos los jugadores conectados).
   - `CHAT_WHISPER`: Mensaje privado entre dos jugadores.
3. **Mundo y Combate**:
   - `ROOM_LOOT_TAKEN`: Se emite cuando alguien recoge un ítem del suelo.
   - `ROOM_COMBAT_ACTION`: Se emite cuando un jugador golpea o usa una habilidad contra un enemigo en la sala.
   - `ENEMY_DEFEATED`: Se emite cuando el enemigo de la sala muere y deja caer botín.

---

## 3. Control de Concurrencia y Consistencia

Para evitar condiciones de carrera (por ejemplo, que dos jugadores intenten recoger la misma espada del suelo al mismo milisegundo):
- **Locks por Sala (Room-level Locks)**: Bloqueo asíncrono temporal en el backend para operaciones de inventario o combate en la misma `location_id`.
- **Transacciones Atómicas en Repositorio**: Si el ítem ya no se encuentra en `location.items` al momento de persistir, la acción retorna "El objeto ya no está aquí" de forma segura.

---

## 4. Desglose de Tareas por Fases

### Fase 1: Autenticación, Sesiones y Conexión WebSocket Base
- [ ] **1.1. Sistema de Cuentas y Login**:
  - [ ] Crear modelo de cuenta de usuario (`UserAccount`: username, password_hash, created_at).
  - [ ] Endpoint `/api/v1/auth/register` y `/api/v1/auth/login`.
  - [ ] Generación y validación de tokens de sesión JWT.
- [ ] **1.2. Servidor WebSocket en FastAPI**:
  - [ ] Implementar `ConnectionManager` en `app/api/websocket/`.
  - [ ] Crear endpoint `/ws/{player_id}` con validación de autenticación.
  - [ ] Control de conexión, desconexión y latidos (*heartbeats / ping-pong*).

### Fase 2: Presencia de Jugadores y Sistema de Chat
- [ ] **2.1. Presencia Espacial**:
  - [ ] Notificar a los ocupantes de una sala cuando un jugador entra o sale (`move_player`).
  - [ ] Incluir lista de jugadores presentes en la respuesta de `Location` (`present_players`).
- [ ] **2.2. Canales de Chat**:
  - [ ] Comando `say <mensaje>` (chat local de sala).
  - [ ] Comando `shout <mensaje>` (chat global).
  - [ ] Comando `whisper <jugador> <mensaje>` (mensajería directa privada).
- [ ] **2.3. Frontend - Componente de Chat y Presencia**:
  - [ ] Hook de React `useMultiplayerSocket` para reconexión automática.
  - [ ] Panel de Chat con pestañas (Sala, Global, Sistema, Privado).
  - [ ] Lista visual de "Jugadores en esta zona" en la barra lateral.

### Fase 3: Acciones Compartidas y Concurrencia
- [ ] **3.1. Sincronización de Botín (Loot)**:
  - [ ] Difusión inmediata de objetos tirados o recogidos del suelo en la sala.
  - [ ] Manejo de errores por recolección concurrente sin desincronización.
- [ ] **3.2. Sistema de Intercambio (Trading)**:
  - [ ] Comandos `trade offer <jugador>`, `trade accept`, `trade cancel`.
  - [ ] Modal interactivo de intercambio seguro de oro e ítems.

### Fase 4: Combate Cooperativo y Sistema de Grupos (Party)
- [ ] **4.1. Combate en Sala Compartida**:
  - [ ] Los enemigos en la sala reciben daño compartido de múltiples atacantes.
  - [ ] Registro de combate en tiempo real visible para todos los presentes en la casilla.
  - [ ] Distribución justa de experiencia (XP) y botín según contribución.
- [ ] **4.2. Sistema de Grupos (Party)**:
  - [ ] Comandos `party invite <jugador>`, `party accept`, `party leave`.
  - [ ] Chat privado de grupo y visualización de barras de vida de los compañeros de equipo.
