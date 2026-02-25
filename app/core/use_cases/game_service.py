from typing import Tuple
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.ports.repositories import GameRepository
from app.core.use_cases.world_generator import WorldGenerator
from collections import Counter

class GameService:
    def __init__(self, repository: GameRepository):
        self.repo = repository
        self.world_gen = WorldGenerator()

    def create_new_player(self, name: str) -> Player:
        # Check if player already exists
        existing_player = self.repo.get_player_by_name(name)
        if existing_player:
            return existing_player

        start_id = "loc_0_0_0"
        start_location = self.repo.get_location(start_id)
        if not start_location:
            print("GENERATING NEW CHUNK AROUND 0,0")
            # Generate a 5x5 chunk centered roughly on 0,0
            generated_locations = self.world_gen.generate_chunk(start_x=-2, start_y=-2, size=5)
            # Force Oakfield at 0,0
            print(f"Generated {len(generated_locations)} locations.")
            for loc in generated_locations:
                if loc.coordinates.x == 0 and loc.coordinates.y == 0:
                    loc.name = "Oakfield Hub"
                    loc.description = "You stand in the center of Oakfield, a bustling safe haven. A sturdy forge burns to the west, and a merchant's wagon is parked to the east. The wilderness calls from the north and south."
                    loc.interactables = ["forge", "wagon"]
                self.repo.create_location(loc)
            start_location = self.repo.get_location(start_id)
            print("FINISHED GENERATING NEW CHUNK")

        if start_location:
            self._ensure_neighbors(start_location)
            
        player = Player(name=name, current_location_id=start_id)
        return self.repo.save_player(player)

    def login_player(self, name: str) -> Tuple[Player, Location]:
        player = self.repo.get_player_by_name(name)
        if not player:
            raise ValueError(f"Player '{name}' not found.")
        
        location = self.repo.get_location(player.current_location_id)
        if not location:
            location = self.world_gen.generate_limbo()
            
        return player, location

    def _get_player_and_location(self, player_id: str) -> Tuple[Player, Location]:
        player = self.repo.get_player(player_id)
        if not player:
            raise ValueError("Player not found")
        current_location = self.repo.get_location(player.current_location_id)
        if not current_location:
            current_location = self.world_gen.generate_limbo()
        return player, current_location

    def _advance_time_and_events(self, world_time, player: Player, time_cost: int) -> str:
        msg_add = ""
        if time_cost > 0:
            world_time.advance(time_cost)
            self.repo.save_world_time(world_time)
            
            if world_time.hour == 20 and world_time.minute < time_cost:
                msg_add += "\nNight has fallen."
            elif world_time.hour == 6 and world_time.minute < time_cost:
                msg_add += "\nDawn breaks."

            self._handle_periodic_events(world_time.total_ticks, player)
            self.repo.save_player(player)
        return msg_add

    def look(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        
        base_desc = location.description
        if world_time and world_time.is_night():
            base_desc = f"[NIGHT] {base_desc} (It is dark)"
        
        if location.items:
            item_names = [i.name for i in location.items]
            base_desc += f"\nYou see items: {', '.join(item_names)}"
            
        if location.enemies:
            enemy_names = [f"{e.name} (HP:{e.hp})" for e in location.enemies]
            base_desc += f"\nEnemies here: {', '.join(enemy_names)}"
            
        return base_desc, player, location

    def map_inventory(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not player.inventory:
            return "You are not carrying anything.", player, location
        counts = Counter((i.name, i.item_type) for i in player.inventory)
        items_list = []
        for (name, item_type), count in sorted(counts.items()):
            display = f"- {name} ({item_type})"
            if count > 1: display += f" x{count}"
            items_list.append(display)
        return f"Inventory:\n" + "\n".join(items_list), player, location

    def move_player(self, player_id: str, direction: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()

        if direction in ["enter", "dive", "down"]: direction = "down"
        elif direction in ["climb", "surface", "up"]: direction = "up"
        if direction not in ["north", "south", "east", "west", "up", "down"]:
            return "Go where?", player, location

        next_location_id = player.move(direction, location.exits)
        if next_location_id:
            player.current_location_id = next_location_id
            self.repo.save_player(player)
            time_msg = self._advance_time_and_events(world_time, player, 10)
            
            new_loc = self.repo.get_location(next_location_id)
            if new_loc:
                self._ensure_neighbors(new_loc)
                return f"You travel {direction}...{time_msg}", player, new_loc
            return f"You travel {direction}...{time_msg}", player, location
        return "You can't go that way.", player, location

    def take_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        if not item_name: return "Take what?", player, location
        
        found_item = location.remove_item(item_name)
        if found_item:
            player.add_item(found_item)
            self.repo.save_player(player)
            self.repo.create_location(location)
            time_msg = self._advance_time_and_events(world_time, player, 1)
            return f"You picked up {found_item.name}.{time_msg}", player, location
        return "You don't see that here.", player, location

    def drop_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        if not item_name: return "Drop what?", player, location
        
        found_item = player.remove_item(item_name)
        if found_item:
            location.add_item(found_item)
            self.repo.save_player(player)
            self.repo.create_location(location)
            time_msg = self._advance_time_and_events(world_time, player, 1)
            return f"You dropped {found_item.name}.{time_msg}", player, location
        return "You don't have that.", player, location

    def equip_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        
        if not item_name:
            return "Equip what?", player, location
            
        found_item = next((i for i in player.inventory if i.name.lower() == item_name.lower()), None)
        if not found_item:
            return f"You don't have a '{item_name}' in your inventory.", player, location
            
        msg = player.equip(found_item)
        self.repo.save_player(player)
        return msg, player, location

    def unequip_item(self, player_id: str, slot: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        
        if not slot:
            return "Unequip from what slot?", player, location
            
        msg = player.unequip(slot)
        self.repo.save_player(player)
        return msg, player, location

    def attack_enemy(self, player_id: str, target_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        if not target_name: return "Attack what?", player, location
        
        enemy = location.get_enemy(target_name)
        if not enemy: return f"You don't see '{target_name}' here.", player, location

        # Calculate player damage
        total_strength = player.stats.strength
        weapon = player.equipment.get("weapon")
        if weapon and "strength" in weapon.stat_bonuses:
            total_strength += weapon.stat_bonuses["strength"]
            
        damage = max(1, (total_strength // 2))
        actual_dmg = enemy.take_damage(damage)
        combat_log = f"You hit {enemy.name} for {actual_dmg} damage. (Enemy HP: {enemy.hp}/{enemy.max_hp})"
        
        if enemy.is_dead:
            combat_log += f"\n{enemy.name} collapses and dies!"
            location.remove_enemy(enemy.id)
            player.gain_xp(enemy.xp_reward)
            combat_log += f"\nYou gain {enemy.xp_reward} XP."
            self.repo.save_player(player)
            self.repo.create_location(location)
            time_msg = self._advance_time_and_events(world_time, player, 2)
            return combat_log + time_msg, player, location
            
        # Calculate enemy damage vs player armor mitigation
        enemy_dmg = max(1, enemy.attack)
        armor = player.equipment.get("armor")
        mitigation = 0
        if armor and "defense" in armor.stat_bonuses:
            mitigation = armor.stat_bonuses["defense"]
            
        final_dmg = max(1, enemy_dmg - mitigation)
        player.take_damage(final_dmg)
        combat_log += f"\n{enemy.name} attacks you for {final_dmg} damage! (Your HP: {player.stats.hp}/{player.stats.max_hp})"
        
        if not player.is_alive():
            combat_log += "\nYou have been defeated...\nYou wake up back at the start, feeling woozy."
            player.heal()
            player.current_location_id = "loc_0_0_0"
            self.repo.save_player(player)
            self.repo.create_location(location)
            time_msg = self._advance_time_and_events(world_time, player, 2)
            return combat_log + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        
        self.repo.save_player(player)
        self.repo.create_location(location)
        time_msg = self._advance_time_and_events(world_time, player, 2)
        return combat_log + time_msg, player, location

    def scout_area(self, player_id: str) -> Tuple[str, Player, Location, list]:
        player, location = self._get_player_and_location(player_id)
        if not location.coordinates:
            return "You cannot orient yourself here.", player, location, []
            
        x, y, z = location.coordinates.x, location.coordinates.y, location.coordinates.z
        radius = 5
        nearby = self.repo.get_locations_in_radius(x, y, z, radius)
        
        if not nearby:
            return "You scout the area but see nothing of interest.", player, location, []
            
        scouted_data = []
        found_landmarks = []
        for loc in nearby:
            # Filter generic names starting with Biomes or Wilderness
            if loc.name.startswith("Forest Area") or loc.name.startswith("Desert Area") or loc.name.startswith("Wilderness"):
                continue
                
            nx, ny = loc.coordinates.x, loc.coordinates.y
            dx = nx - x
            dy = ny - y
            
            # Simple cardinal logic
            dir_str = ""
            if dy > 0: dir_str += "North"
            elif dy < 0: dir_str += "South"
            
            if dx > 0: dir_str += "East" if not dir_str else "-East"
            elif dx < 0: dir_str += "West" if not dir_str else "-West"
            
            # Distance
            dist = max(abs(dx), abs(dy))
            found_landmarks.append(f"- {loc.name} ({dist} chunks {dir_str})")
            scouted_data.append({
                "name": loc.name,
                "distance": dist,
                "direction": dir_str
            })
            
        if not found_landmarks:
            return "You scout the area but only see endless wilderness.", player, location, []
            
        msg = "You look around and spot notable landmarks:\n" + "\n".join(found_landmarks)
        
        # Scouting takes 2 ticks
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, 2)
        return msg + time_msg, player, location, scouted_data

    def get_time_status(self) -> str:
        world_time = self.repo.get_world_time()
        return f"It is {world_time.get_time_string()}."

    def process_command(self, player_id: str, command_text: str) -> Tuple:
        args = command_text.lower().split()
        if not args:
            player, location = self._get_player_and_location(player_id)
            return "Please enter a command.", player, location
        
        action = args[0]
        arg_str = " ".join(args[1:])
        
        if action in ["go", "move", "walk", "north", "south", "east", "west", "up", "down", "enter", "climb"]:
            dir = args[1] if len(args) > 1 else action
            return self.move_player(player_id, dir)
        elif action in ["look", "examine"]:
            return self.look(player_id)
        elif action in ["scout", "radar", "map"]:
            return self.scout_area(player_id)
        elif action in ["stats", "status"]:
            player, location = self._get_player_and_location(player_id)
            return str(player.stats), player, location
        elif action in ["take", "get", "pickup", "grab"]:
            return self.take_item(player_id, arg_str)
        elif action in ["drop", "discard"]:
            return self.drop_item(player_id, arg_str)
        elif action in ["equip", "wear", "wield"]:
            return self.equip_item(player_id, arg_str)
        elif action in ["unequip", "remove"]:
            return self.unequip_item(player_id, arg_str)
        elif action in ["inventory", "inv", "i"]:
            return self.map_inventory(player_id)
        elif action in ["attack", "fight", "hit", "kill"]:
            return self.attack_enemy(player_id, arg_str)
        elif action in ["time", "clock", "date"]:
            player, location = self._get_player_and_location(player_id)
            return self.get_time_status(), player, location
        
        player, location = self._get_player_and_location(player_id)
        return "I don't understand that command.", player, location

    def _handle_periodic_events(self, current_tick: int, player: Player):
        if hasattr(player, "stats") and current_tick % 10 == 0:
            if player.stats.hp < player.stats.max_hp:
                player.stats.hp += 1

    def _ensure_neighbors(self, location: Location):
        if not location.coordinates: return
        x, y, z = location.coordinates.x, location.coordinates.y, location.coordinates.z
        deltas = {
            "north": (0, 1, 0), "south": (0, -1, 0),
            "east": (1, 0, 0), "west": (-1, 0, 0),
        }
        for direction, (dx, dy, dz) in deltas.items():
            nx, ny, nz = x + dx, y + dy, z + dz
            if direction in location.exits: continue
            neighbor = self.repo.get_location_by_coordinates(nx, ny, nz)
            if not neighbor:
                neighbor = self.world_gen.generate_single_location(nx, ny, nz)
                self.repo.create_location(neighbor)
            self._link_locations(location, neighbor, direction)

    def _link_locations(self, loc_a: Location, loc_b: Location, dir_a_to_b: str):
        opposites = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}
        dir_b_to_a = opposites.get(dir_a_to_b)
        loc_a.exits[dir_a_to_b] = loc_b.id
        loc_b.exits[dir_b_to_a] = loc_a.id
        self.repo.create_location(loc_a)
        self.repo.create_location(loc_b)
