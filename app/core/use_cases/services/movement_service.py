from typing import Tuple, List, Dict, Any
import math
import re
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.core.config import settings
from app.core.use_cases.services.base_service import BaseGameService

class MovementService(BaseGameService):
    def move_player(self, player_id: str, direction: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()

        if direction in ["enter", "dive", "down"]:
            direction = "down"
        elif direction in ["climb", "surface", "up"]:
            direction = "up"
            
        if direction not in ["north", "south", "east", "west", "up", "down"]:
            return "Go where?", player, location
            
        if direction == "down":
            bosses = [e for e in location.enemies if getattr(e, "is_boss", False) and not getattr(e, "is_dead", False)]
            if bosses:
                return f"The {bosses[0].name} blocks your path deeper into the dungeon!", player, location

        # Engagement Check: Dungeon enemies and provoked enemies block movement
        alive_enemies = [e for e in location.enemies if not getattr(e, "is_dead", False)]
        bypass_msg = ""
        if alive_enemies:
            is_dungeon = location.id.startswith("dng_")
            is_provoked = any(e.hp < e.max_hp for e in alive_enemies)
            
            if is_dungeon or is_provoked:
                enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_MOVE_DUNGEON)
                block_reason = "in a dungeon" if is_dungeon else "engaged in combat"
                msg = f"You are {block_reason}! The {alive_enemies[0].name} blocks your escape!"
                if enemy_log:
                    msg += f"\nAs you turn to run, they strike: {enemy_log}"
                
                self.repo.save_player(player)
                if is_dead:
                    return msg, player, self.repo.get_location("loc_0_0_0") or location
                return msg, player, location
            else:
                enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_MOVE_WILDERNESS)
                if is_dead:
                    return f"You try to slip past the {alive_enemies[0].name}, but it's fatal! {enemy_log}", player, self.repo.get_location("loc_0_0_0") or location
                if enemy_log:
                    bypass_msg = f"\nAs you slip past, the {alive_enemies[0].name} lunges: {enemy_log}"

        next_location_id = player.move(direction, location.exits)
        if next_location_id:
            # Clear dropped items when player successfully leaves the location
            original_item_count = len(location.items)
            location.items = [item for item in location.items if not getattr(item, 'is_dropped', False)]
            if len(location.items) != original_item_count:
                self.repo.create_location(location)

            # Check if entering an ungenerated dungeon floor
            new_loc = self.repo.get_location(next_location_id)
            if not new_loc and next_location_id.startswith("dng_") and self.dungeon_gen:
                parts = next_location_id.split("_")
                x, y, z = int(parts[1]), int(parts[2]), int(parts[3])
                
                dungeon_locations = self.dungeon_gen.generate_floor(x, y, z)
                for loc in dungeon_locations:
                    self.repo.create_location(loc)
                    
                new_loc = self.repo.get_location(next_location_id)

            player.current_location_id = next_location_id
            self.repo.save_player(player)
            
            trap_msg = ""
            if new_loc and new_loc.trap_damage > 0:
                damage = new_loc.trap_damage
                player.take_damage(damage)
                trap_msg = f"\n[TRAP] You triggered a trap and took {damage} damage!"
                if not player.is_alive():
                    trap_msg += "\nThe trap was fatal..."
                    player.heal()
                    player.current_location_id = "loc_0_0_0"
                    self.repo.save_player(player)
                    new_loc = self.repo.get_location("loc_0_0_0")
                else:
                    self.repo.save_player(player)

            time_msg = self._advance_time_and_events(world_time, player, settings.TIME_COST_MOVE)
            
            if new_loc:
                self._ensure_neighbors(new_loc)
                return f"{bypass_msg}You travel {direction}...{trap_msg}{time_msg}", player, new_loc
            return f"{bypass_msg}You travel {direction}...{trap_msg}{time_msg}", player, location
            
        return "You can't go that way.", player, location

    def scout_area(self, player_id: str) -> Tuple[str, Player, Location, list]:
        player, location = self._get_player_and_location(player_id)
        if not location.coordinates:
            return "You cannot orient yourself here.", player, location, []
            
        x, y, z = location.coordinates.x, location.coordinates.y, location.coordinates.z
        radius = settings.SCOUT_RADIUS
        
        if location.id.startswith("dng_"):
            radius = 1
        else:
            # Ensure full 360-degree radius is generated on the surface
            if self.world_gen:
                for nx in range(x - radius, x + radius + 1):
                    for ny in range(y - radius, y + radius + 1):
                        loc_id = f"loc_{nx}_{ny}_0"
                        if not self.repo.get_location(loc_id):
                            new_loc = self.world_gen.generate_single_location(nx, ny, 0)
                            self.repo.create_location(new_loc)

        nearby = self.repo.get_locations_in_radius(x, y, z, radius)
        
        if not nearby:
            return "You scout the area but see nothing of interest.", player, location, []
            
        scouted_data = []
        found_landmarks = []
        for loc in nearby:
            if not loc.coordinates:
                continue
            nx, ny, nz = loc.coordinates.x, loc.coordinates.y, loc.coordinates.z
            dx = nx - x
            dy = ny - y
            
            # Skip current player location
            if dx == 0 and dy == 0:
                continue

            dist = max(abs(dx), abs(dy))
            report_name = loc.name
            poi_type = "landmark"
            
            # 1. Detect Cave Entrances and Surface Exits
            if z == 0 and "down" in loc.exits:
                report_name = "Cave Entrance"
                poi_type = "cave"
            elif z < 0 and "up" in loc.exits:
                report_name = "Surface Exit"
                poi_type = "cave"
            elif any("water" in str(inter).lower() for inter in getattr(loc, 'interactables', [])) or any(loc.name.startswith(w) for w in ["River", "Stream", "Small Lake", "Lake", "Old Well", "Well", "Oasis", "Spring"]):
                clean_name = re.sub(r"\s+(at\s+)?-?\d+\s*,\s*-?\d+$", "", loc.name).strip()
                report_name = f"{clean_name} (Water Source)"
                poi_type = "water"
            elif "oakfield" in loc.name.lower() or "village" in loc.name.lower() or "town" in loc.name.lower() or "hub" in loc.name.lower():
                poi_type = "town"
            else:
                # Filter out generic empty wilderness tiles with coordinates in name
                generic_biomes = ["forest", "desert", "wilderness", "deep cavern", "cavern", "mountain", "plains"]
                is_generic = any(loc.name.lower().startswith(b) for b in generic_biomes)
                has_coords = bool(re.search(r"(-?\d+\s*,\s*-?\d+)", loc.name))
                if is_generic and (has_coords or not loc.exits or not any(k in ["up", "down"] for k in loc.exits)):
                    continue
                poi_type = "poi"
                
            dir_str = ""
            if dy > 0:
                dir_str += "North"
            elif dy < 0:
                dir_str += "South"
            
            if dx > 0:
                dir_str += "East" if not dir_str else "-East"
            elif dx < 0:
                dir_str += "West" if not dir_str else "-West"
            
            dir_text = f"{dist} chunks {dir_str}" if dist > 0 else "Here"
            found_landmarks.append(f"- {report_name} ({dir_text})")
            scouted_data.append({
                "name": report_name,
                "distance": dist,
                "direction": dir_str if dist > 0 else "Here",
                "dx": dx,
                "dy": dy,
                "x": nx,
                "y": ny,
                "z": nz,
                "type": poi_type
            })
            
        if not found_landmarks:
            return "You scout the area but only see endless wilderness.", player, location, []
            
        msg = "You look around and spot notable landmarks:\n" + "\n".join(found_landmarks)
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, 2)
        return msg + time_msg, player, location, scouted_data

    def create_camp(self, player_id: str, camp_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not camp_name:
            return "You must provide a name for your camp.", player, location
            
        msg = player.add_waypoint(camp_name, location.id)
        self.repo.save_player(player)
        return msg, player, location

    def fast_travel(self, player_id: str, waypoint_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not waypoint_name:
            return "Travel where?", player, location
            
        target_id = player.waypoints.get(waypoint_name)
        if not target_id:
            return f"You don't know the way to '{waypoint_name}'.", player, location
            
        if target_id == location.id:
            return "You are already there.", player, location

        target_loc = self.repo.get_location(target_id)
        if not target_loc:
            return "The destination is unreachable.", player, location

        dist = 0
        if location.coordinates and target_loc.coordinates:
            dx = location.coordinates.x - target_loc.coordinates.x
            dy = location.coordinates.y - target_loc.coordinates.y
            dist = math.ceil(math.sqrt(dx*dx + dy*dy))
        else:
            dist = 5
            
        energy_cost = dist * settings.TRAVEL_ENERGY_COST_MULT
        time_cost = dist * settings.TIME_COST_TRAVEL_BASE
        
        if player.stats.hp <= energy_cost:
            return f"You are too exhausted to make the journey to {waypoint_name} (Requires {energy_cost} HP).", player, location
            
        player.take_damage(energy_cost)
        player.current_location_id = target_loc.id
        self.repo.save_player(player)
        
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, time_cost)
        
        travel_narrative = f"You traveled to {waypoint_name}, covering a great distance. You spent {energy_cost} HP."
        return f"{travel_narrative}{time_msg}", player, target_loc
