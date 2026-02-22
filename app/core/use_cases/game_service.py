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
            generated_locations = self.world_gen.generate_chunk(start_x=0, start_y=0, size=5)
            for loc in generated_locations:
                self.repo.create_location(loc)
            start_location = self.repo.get_location(start_id)

        # Ensure neighbors for the start location (Infinite Gen start)
        if start_location:
             self._ensure_neighbors(start_location)
            
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
            
        def save_location_state(l: Location):
            self.repo.create_location(l) 

        # Load World Time
        world_time = self.repo.get_world_time()
        
        # Parse Command
        result = self.parser.parse(command_text, player, current_location, world_time, save_player_state, save_location_state)
        
        # Advance Time based on action (simplified)
        # If command was successful (implied by checking if message is not error? or just always?)
        # For now, let's say any command advances time by 1 minute, moving/fighting more?
        # Let's let the PARSER decide cost? Or Service?
        # Service doesn't know what happened easily without parsing result message or structured result.
        # Plan said: Move 10 mins, Attack 2 mins.
        # But Parser handles the logic.
        # Maybe Parser returns `time_cost` in CommandResult?
        
        # Modification: I need to update CommandResult to include time_cost first?
        # Or I just assume 1 tick per command for MVP?
        # The plan says "Time will currently only advance when the user performs an action".
        # Let's assume the parser handles the action.
        # But the Parser signature in `game_service` is being changed here.
        # I need to update Parser signature too.
        
        # Let's update Parser first? No, I can update Service to call it with new arg, 
        # but I need to update Parser to accept it.
        # For this step, I will pass world_time to parser.
        
        # Time Advancement Logic:
        # If result.time_cost > 0: world_time.advance(result.time_cost); repo.save(world_time)
        # I'll need to update CommandResult to have time_cost.
        
        if hasattr(result, 'time_cost') and result.time_cost > 0:
            world_time.advance(result.time_cost)
            self.repo.save_world_time(world_time)
            
            # Simple Day/Night Announcement
            if world_time.hour == 20 and world_time.minute < result.time_cost:
                result.message += "\nNight has fallen."
            elif world_time.hour == 6 and world_time.minute < result.time_cost:
                result.message += "\nDawn breaks."

            # Periodic Events
            self._handle_periodic_events(world_time.total_ticks, result.player)
            # Re-save player in case of healing
            self.repo.save_player(result.player)
        
        # Check if player moved (location ID changed)
        final_location = result.location
        if result.player.current_location_id != current_location.id:
            # Player successfully moved
            new_loc_id = result.player.current_location_id
            new_loc = self.repo.get_location(new_loc_id)
            if new_loc:
                final_location = new_loc
                # NEW: Ensure neighbors exist for the new location (Infinite Gen)
                self._ensure_neighbors(final_location)
                
        return result.message, result.player, final_location

    def _handle_periodic_events(self, current_tick: int, player: Player):
        # Every 10 ticks: Passive Heal
        if current_tick % 10 == 0:
            if player.stats.hp < player.stats.max_hp:
                player.stats.hp += 1
                # We could add a message, but CommandResult message is already set.
                # Maybe just silent heal.

    def _ensure_neighbors(self, location: Location):
        """Checks cardinal neighbors and generates them if missing."""
        if not location.coordinates:
            return

        x, y, z = location.coordinates.x, location.coordinates.y, location.coordinates.z
        
        # Directions mapping to coordinate deltas
        deltas = {
            "north": (0, 1, 0),
            "south": (0, -1, 0),
            "east": (1, 0, 0),
            "west": (-1, 0, 0),
            # Vertical neighbors handled by generate_single_location logic usually
            # But we could check "down" if we are on surface?
        }
        
        for direction, (dx, dy, dz) in deltas.items():
            nx, ny, nz = x + dx, y + dy, z + dz
            
            # Check if neighbor already linked
            if direction in location.exits:
                continue # Already linked
            
            # Check if neighbor exists in DB but not linked
            neighbor = self.repo.get_location_by_coordinates(nx, ny, nz)
            
            if not neighbor:
                # Generate new
                neighbor = self.world_gen.generate_single_location(nx, ny, nz)
                self.repo.create_location(neighbor)
            
            # Link them
            self._link_locations(location, neighbor, direction)

    def _link_locations(self, loc_a: Location, loc_b: Location, dir_a_to_b: str):
        opposites = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}
        dir_b_to_a = opposites.get(dir_a_to_b)
        
        loc_a.exits[dir_a_to_b] = loc_b.id
        loc_b.exits[dir_b_to_a] = loc_a.id
        
        self.repo.create_location(loc_a)
        self.repo.create_location(loc_b)




