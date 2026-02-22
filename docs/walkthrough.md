# Walkthrough - Initial Backend Prototype

## Overview
I have successfully implemented the core structure for the Text RPG backend using **Hexagonal Architecture**. The codebase is now cleaner, modular, and testable.

### Key Components Implemented
1.  **Domain Layer** (`app/core/domain/`)
    -   `Player`: Manages stats, inventory, and movement logic.
    -   `Location`: Represents rooms or areas in the world.
    -   `Item`: Base structure for game items.

2.  **Logic Layer** (`app/core/use_cases/`)
    -   `GameService`: Orchestrates the game flow.
    -   `CommandParser`: Handles text input parsing (e.g., "go north", "look").
    -   `WorldGenerator`: Creates a 5x5 chunk of connected locations (Forest biome) upon game start.

    -   `WorldGenerator`: Creates a 5x5 chunk of connected locations (Forest biome) upon game start.

3.  **Persistence Layer** (`app/adapters/driven/persistence/`)
    -   `SQLGameRepository`: Uses **SQLModel** and **SQLite** to persist game state to `database.db`.
    -   `sql_models.py`: Defines database schema.

## Verification
I ran the automated test suite to ensure the game loop works as expected.

### Test Results
```bash
$ pytest tests/test_game_flow.py
================ test session starts =================
tests/test_game_flow.py .                      [100%]
================ 1 passed in 0.36s =================
```

### Manual Verification Steps
You can try the API yourself by running the server:

1.  **Start the Server**:
    Make sure you are in the root directory and your virtual environment is active.
    ```bash
    uvicorn app.main:app --reload
    ```
    The server will start at `http://127.0.0.1:8000`.

2.  **API Documentation (Swagger UI)**:
    Open your browser and navigate to:
    [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
    Here you can interactively test all endpoints without using `curl`.

3.  **Command Line (curl)**:
    -   **Start Game**:
        ```bash
        curl -X POST "http://127.0.0.1:8000/api/v1/start?name=Hero"
        ```
    -   **Look Around**:
        ```bash
        curl -X POST "http://127.0.0.1:8000/api/v1/command" \
             -H "Content-Type: application/json" \
             -d '{"player_id": "YOUR_PLAYER_ID_FROM_START_RESPONSE", "command": "look"}'
        ```

4.  **Visualize the World (Terminal Tool)**:
    To see where you are on the map:
    ```bash
    python scripts/visualize_world.py [PlayerName]
    ```
    This script now runs in a loop, updating every second to show your movement in real-time. Press `Ctrl+C` to exit.

### 4. Interacting with Items
As you explore, you will find items generated in the world (Sticks, Stones, etc.).
- Use `look` to see what is on the ground.
- Use `take [item name]` to pick it up.
- Use `inventory` or `i` to check your bag.
- Use `drop [item name]` to leave it behind.

### 5. Combat
You may encounter enemies like Goblins or Cave Spiders, especially in caves or dangerous biomes.
- Use `look` to spot enemies.
- Use `attack [enemy name]` to fight.
- Watch your HP! If you die, you will respawn at the start.

### 6. Time & Events
Time passes as you act (turn-based).
- **Movement** takes 10 minutes.
- **Combat** takes 2 minutes.
- **Inventory actions** take 1 minute.
- **Day/Night Cycle:** It gets dark at 20:00.
- **Healing:** You regenerate 1 HP for every 10 minutes of activity.
- Use `time` command to check the clock.

For a full list of supported commands, see [COMMANDS.md](COMMANDS.md).

## Next Steps
-   **Expand World Generation**: Add more rooms and procedural generation.
-   **Add Items**: Implement picking up and using items.
-   **Combat System**: Basic turn-based combat.
