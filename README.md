# Text RPG Backend

A text-based RPG backend built with Python, FastAPI, and Hexagonal Architecture.

## Setup

1.  **Create Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Database Configuration**:
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    The default configuration uses SQLite (`database.db`).

## Running the Server

Start the development server with hot reload:
```bash
uvicorn app.main:app --reload
```
API Documentation will be available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Developer Tools

### World Visualizer (Terminal)
A utility script to visualize the generated world map and player position in the terminal.

**Usage:**
```bash
# Visualize the world and specifically track a player
python scripts/visualize_world.py [PlayerName]

# Example
python scripts/visualize_world.py Hero
```

**Output:**
- Displays an ASCII grid of the generated chunks (e.g., 5x5 area).
- Marks the player position with `[P]`.
- **Updates automatically every second.** (Press `Ctrl+C` to stop).

## Testing

Run the test suite:
```bash
pytest
```
