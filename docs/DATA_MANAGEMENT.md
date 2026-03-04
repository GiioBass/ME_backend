# Data Management & System Reset

This document explains how Mystic Explorers handles data persistence, world regeneration, and system resets.

## 1. Database Lifecycle
The system uses **SQLite** for persistence. The database file is located at `ME_backend/database.db`.

### Automatic Initialization
The backend uses FastAPI's `lifespan` event (`app/main.py`) to manage data:
1.  **Schema Check**: On startup, it checks if `database.db` exists. If not, it creates it and applies all SQLModel tables.
2.  **Static Data Load**: It triggers the `DataLoader` to read `data/static_locations.json` and populate the "Hub" areas if they are missing.
3.  **World Seeds**: The first time a player moves into a coordinate, the `WorldGenerator` creates that room dynamically.

## 2. Resetting the Game State
If you want to start from a completely clean slate, follow these steps.

### Using the Reset Script
Run the automated script in the backend root:
```bash
cd /var/www/html/ME_backend
./reset_db.sh
```

### Manual Reset
1.  Stop the backend server (`me-be`).
2.  Delete the database file: `rm database.db`.
3.  Start the backend again: `me-be`.

## 3. Data Regeneration Internals
- **Items & Enemies**: When a new coordinate is generated, the `WorldGenerator` uses internal loot tables and enemy pools to populate the room.
- **Persistence**: Once a room is generated or a player is saved, it stays in the database. Deleting the DB file forces the generator to roll new random values for every room next time they are visited.
- **Static Locations**: Locations defined in `data/static_locations.json` are always recreated with the same IDs and names, ensuring the "Oakfield Hub" remains a consistent starting point.

## 4. Summary of Tools
- `me-be`: Starts server (and initializes DB if missing).
- `reset_db.sh`: Wipes progress and state.
