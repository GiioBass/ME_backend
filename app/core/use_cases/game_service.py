from typing import Tuple
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.ports.repositories import GameRepository
from app.core.use_cases.command_parser import CommandParser
from app.core.use_cases.world_generator import WorldGenerator

class GameService:
    def __init__(self, repository: GameRepository):
        self.repo = repository
        self.parser = CommandParser()
        self.world_gen = WorldGenerator()

    def create_new_player(self, name: str) -> Player:
        # Check if the start location exists (using coordinates 0,0)
        # We assume the ID for (0,0) is "loc_0_0_0" based on WorldGenerator
        start_id = "loc_0_0_0"
        start_location = self.repo.get_location(start_id)
        
        if not start_location:
            # Generate initial chunk centered at 0,0
            # Let's generate a 5x5 chunk starting at -2, -2 so 0,0 is the center
            # Or just start at 0,0. The user agreed on "5x5 chunk".
            # Let's start at 0,0 for simplicity as per plan.
            generated_locations = self.world_gen.generate_chunk(start_x=0, start_y=0, size=5)
            for loc in generated_locations:
                self.repo.create_location(loc)
            
        player = Player(name=name, current_location_id=start_id)
        return self.repo.save_player(player)

    def process_command(self, player_id: str, command_text: str) -> Tuple[str, Player, Location]:
        player = self.repo.get_player(player_id)
        if not player:
            raise ValueError("Player not found")
        
        current_location = self.repo.get_location(player.current_location_id)
        if not current_location:
             current_location = self.world_gen.generate_limbo()

        # Define callback for saving player state
        def save_player_state(p: Player):
            self.repo.save_player(p)

        result = self.parser.parse(command_text, player, current_location, save_player_state)
        
        # Check if player moved (location ID changed)
        final_location = result.location
        if result.player.current_location_id != current_location.id:
            # Player successfully moved to an existing location
            new_loc_id = result.player.current_location_id
            new_loc = self.repo.get_location(new_loc_id)
            if new_loc:
                final_location = new_loc
        elif result.message == "You can't go that way.":
            # Attempt Dynamic Generation
            # 1. Parse direction from command (naive re-parsing or change parser return?)
            # Let's simple parse here for now to avoid breaking parser contract yet
            args = command_text.lower().split()
            if args:
                action = args[0]
                direction = args[1] if len(args) > 1 else action
                if direction in ["north", "south", "east", "west"]:
                     # Try to expand world
                     new_loc = self._attempt_expansion(player, current_location, direction)
                     if new_loc:
                         player.current_location_id = new_loc.id
                         save_player_state(player)
                         final_location = new_loc
                         result.message = f"You travel {direction} into uncharted lands..."
                         result.location = new_loc
        
        return result.message, result.player, final_location

    def _attempt_expansion(self, player: Player, current_loc: Location, direction: str) -> Location:
        if not current_loc.coordinates:
            return None
        
        # Calculate target coordinates
        x, y, z = current_loc.coordinates.x, current_loc.coordinates.y, current_loc.coordinates.z
        if direction == "north": y += 1
        elif direction == "south": y -= 1
        elif direction == "east": x += 1
        elif direction == "west": x -= 1
        
        # Check if location already exists (but wasn't linked?)
        existing_loc = self.repo.get_location_by_coordinates(x, y, z)
        if existing_loc:
            # Just link them and return
            self._link_locations(current_loc, existing_loc, direction)
            return existing_loc
        
        # Generate new Chunk centering on target or just target?
        # Let's generate a 5x5 chunk centered on the target to populate the area
        # This might overlap with existing, so we need to be careful.
        # WorldGenerator.generate_chunk logic:
        # It generates locations. We should check if they exist before creating.
        
        # Heuristic: If I move to X=3, I enter a new "zone".
        # Let's just generate the specific chunk that WOULD contain this coordinate.
        # Assuming grid of 5x5 chunks:
        # Chunk 0: Center 0,0. Range -2 to 2.
        # Chunk East: Center 5,0. Range 3 to 7.
        # This keeps chunks aligned to a grid.
        
        chunk_size = 5
        # Calculate chunk center based on target x,y
        # Center = k * chunk_size
        # But our initial chunk was 0,0 with size 5 (meaning 0 to 4? or centered?)
        # WorldGenerator: generate_chunk(start_x, start_y, size)
        # It loops x from start to start+size.
        # Initial call: start_x=0, start_y=0.
        # So locations are (0,0) to (4,4).
        
        # If I am at (4,0) and go East to (5,0).
        # Target (5,0).
        # I want to generate chunk starting at 5,0.
        
        # Simple grid alignment:
        # chunk_start_x = (target_x // chunk_size) * chunk_size
        # chunk_start_y = (target_y // chunk_size) * chunk_size
        
        # But wait, coordinates can be negative.
        # (-1 // 5) = -1. (-1 * 5) = -5.
        # If target -1. Chunk -5 to -1.
        
        # Let's trust this grid math.
        target_chunk_x = (x // chunk_size) * chunk_size
        target_chunk_y = (y // chunk_size) * chunk_size
        
        new_locations = self.world_gen.generate_chunk(target_chunk_x, target_chunk_y, chunk_size)
        
        target_loc = None
        for loc in new_locations:
            # Check if exists
            if self.repo.get_location(loc.id):
                 continue # Skip ID collision (unlikely with UUID)
            
            # Check if coord collision?
            if loc.coordinates:
                 conflict = self.repo.get_location_by_coordinates(loc.coordinates.x, loc.coordinates.y, loc.coordinates.z)
                 if conflict:
                     continue
            
            self.repo.create_location(loc)
            if loc.coordinates.x == x and loc.coordinates.y == y and loc.coordinates.z == z:
                target_loc = loc
                
        # Link current to target if found (it should be in the new chunk)
        if target_loc:
             self._link_locations(current_loc, target_loc, direction)
             return target_loc
        
        # Fallback: if target was skipped because it existed? (should have been caught by get_location_by_coordinates)
        return self.repo.get_location_by_coordinates(x, y, z)

    def _link_locations(self, loc_a: Location, loc_b: Location, dir_a_to_b: str):
        opposites = {"north": "south", "south": "north", "east": "west", "west": "east"}
        dir_b_to_a = opposites.get(dir_a_to_b)
        
        loc_a.exits[dir_a_to_b] = loc_b.id
        loc_b.exits[dir_b_to_a] = loc_a.id
        
        self.repo.create_location(loc_a) # Update
        self.repo.create_location(loc_b) # Update


