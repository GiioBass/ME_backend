import sys
import os
import time
from sqlmodel import Session, select

# Add project root to path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.adapters.driven.persistence.db_config import engine
from app.adapters.driven.persistence.sql_models import LocationDB, PlayerDB

def visualize_world(player_name=None):
    with Session(engine) as session:
        # Fetch all locations
        locations_db = session.exec(select(LocationDB)).all()
        locations = [loc.to_domain() for loc in locations_db]
        
        # Fetch player if provided
        player = None
        if player_name:
            statement = select(PlayerDB).where(PlayerDB.name == player_name)
            player_db = session.exec(statement).first()
            if player_db:
                player = player_db.to_domain()
            else:
                print(f"Player '{player_name}' not found.")
        
        # If no name provided, list players or pick first
        if not player and not player_name:
             players_db = session.exec(select(PlayerDB)).all()
             if players_db:
                 player = players_db[-1].to_domain() # Get latest
                 print(f"Visualizing for player: {player.name}")

    if not locations:
        print("No world generated yet.")
        return

    grid = {}
    # Determine Viewport
    # Radius of 4 gives a 9x9 grid (covering more than a 5x5 chunk)
    radius = 4
    
    center_x, center_y = 0, 0
    if player and player.current_location_id:
        # Find player coords
        # optimized: could map ID to coords first, but list loop is fast enough for now
        player_loc = next((l for l in locations if l.id == player.current_location_id), None)
        if player_loc and player_loc.coordinates:
             center_x, center_y = player_loc.coordinates.x, player_loc.coordinates.y

    min_x = center_x - radius
    max_x = center_x + radius
    min_y = center_y - radius
    max_y = center_y + radius

    print(f"\nWorld Map (Viewport centered at {center_x},{center_y})")
    print(f"Bounds: ({min_x},{min_y}) to ({max_x},{max_y})")
    
    # Coordinate header
    header = "   " + " ".join([f"{x:3}" for x in range(min_x, max_x + 1)])
    print(header)

    for y in range(max_y, min_y - 1, -1):
        # Row 1: Vertical connections (North)
        line_north = "   "
        for x in range(min_x, max_x + 1):
            loc = grid.get((x, y))
            symbol = " | " if (loc and "north" in loc.exits) else "   "
            line_north += f" {symbol} "
        print(line_north)

        # Row 2: Content
        line_mid = f"{y:3}"
        for x in range(min_x, max_x + 1):
            loc = grid.get((x, y))
            if not loc:
                line_mid += "     "
                continue

            # West connect
            west = "-" if "west" in loc.exits else " "
            
            # Content
            # Check if player is here
            is_here = False
            if player and player.current_location_id == loc.id:
                is_here = True
            
            if is_here:
                center = "[P]" # Player
            elif x == 0 and y == 0:
                center = "[S]" # Start
            else:
                center = "[ ]"
            
            # East connect logic (peek next?)
            line_mid += f"{west}{center}"
            if x == max_x and "east" in loc.exits: 
                 line_mid += "-"
            
        print(line_mid)
        
    # Stats
    if player:
        curr_loc = grid.get((0,0)) # default
        # find actual obj
        for loc in locations:
            if loc.id == player.current_location_id:
                curr_loc = loc
                break
        
        if curr_loc:
             print(f"\nPlayer: {player.name}")
             print(f"Location: {curr_loc.name} {curr_loc.coordinates}")
             print(f"Exits: {list(curr_loc.exits.keys())}")
        else:
             print(f"\nPlayer: {player.name}")
             print(f"Location ID: {player.current_location_id} (Not found in loaded locations)")

def main(p_name):
    # Loop for real-time updates
    print(f"Monitoring player '{p_name or 'any'}'... (Ctrl+C to stop)")
    try:
        while True:
            # Clear screen
            os.system('cls' if os.name == 'nt' else 'clear')
            
            visualize_world(p_name)
            
            print("\nUpdating... (Ctrl+C to stop)")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    # Optional arg: player name
    p_name = sys.argv[1] if len(sys.argv) > 1 else None
    main(p_name)
