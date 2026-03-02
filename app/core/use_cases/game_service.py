from typing import Tuple
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.ports.repositories import GameRepository
from app.core.use_cases.world_generator import WorldGenerator
from app.core.use_cases.static_area_loader import StaticAreaLoader
from collections import Counter

class GameService:
    def __init__(self, repository: GameRepository):
        self.repo = repository
        self.world_gen = WorldGenerator()
        self.static_area_loader = StaticAreaLoader()
        from app.core.use_cases.dungeon_generator import DungeonGenerator
        self.dungeon_gen = DungeonGenerator()

    def create_new_player(self, name: str) -> Tuple[Player, Location]:
        # Check if player already exists
        existing_player = self.repo.get_player_by_name(name)
        if existing_player:
            raise ValueError(f"Player name '{name}' is already taken.")

        start_id = "loc_0_0_0"
        start_location = self.repo.get_location(start_id)
        if not start_location:
            print("GENERATING NEW CHUNK AROUND 0,0")
            generated_locations = self.world_gen.generate_chunk(start_x=-2, start_y=-2, size=5)
            # Load static areas and override generated ones
            static_locations = self.static_area_loader.load_static_areas()
            static_coords = {(loc.coordinates.x, loc.coordinates.y, loc.coordinates.z): loc for loc in static_locations if loc.coordinates}
            
            print(f"Generated {len(generated_locations)} locations.")
            for loc in generated_locations:
                coords = (loc.coordinates.x, loc.coordinates.y, loc.coordinates.z)
                if coords in static_coords:
                    # Replace with static location data
                    static_loc = static_coords[coords]
                    loc.name = static_loc.name
                    loc.description = static_loc.description
                    loc.interactables = static_loc.interactables
                    # Note: We keep the exits that might have been generated or we let them be overridden if needed?
                    # The chunk generator will still link neighbors.
                self.repo.create_location(loc)
            start_location = self.repo.get_location(start_id)
            if not start_location:
                # Fallback just in case, find it in the generated list
                start_location = next((l for l in generated_locations if l.id == start_id), None)
            print("FINISHED GENERATING NEW CHUNK")

        if start_location:
            self._ensure_neighbors(start_location)
            
        player = Player(name=name, current_location_id=start_id)
        saved_player = self.repo.save_player(player)
        return saved_player, start_location

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

            msg_add += self._apply_survival_mechanics(time_cost, player)
            self.repo.save_player(player)
        return msg_add

    def look(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        
        base_desc = location.description
        if world_time and world_time.is_night():
            base_desc = f"[NIGHT] {base_desc} (It is dark)"
        
        # Darkness check override
        if location.is_dark:
            has_light = any(getattr(item, "is_light_source", False) for item in player.inventory)
            if not has_light:
                return "It is pitch black. You cannot see anything without a light source.", player, location

        if location.items:
            item_names = [i.name for i in location.items]
            base_desc += f"\nYou see items: {', '.join(item_names)}"
            
        if location.enemies:
            enemy_names = [f"{e.name} (HP:{e.hp})" for e in location.enemies]
            base_desc += f"\nEnemies here: {', '.join(enemy_names)}"
        
        # Special Goblin Encounter at 4,4,0
        if location.coordinates and location.coordinates.x == 4 and location.coordinates.y == 4 and location.coordinates.z == 0:
            if any(e.name == "Friendly Goblin" and not getattr(e, "is_dead", False) for e in location.enemies):
                base_desc += "\n\n[SPECIAL] A goblin has given you such an... intense 'welcome' that you've discovered new meanings for the word 'flexibility'. He seems to have thoroughly enjoyed your company!"
            
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
        weight_info = f"Weight: {player.current_weight:.1f}/{player.stats.max_weight:.1f}"
        return f"Inventory ({weight_info}):\n" + "\n".join(items_list), player, location

    def move_player(self, player_id: str, direction: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()

        if direction in ["enter", "dive", "down"]: direction = "down"
        elif direction in ["climb", "surface", "up"]: direction = "up"
        if direction not in ["north", "south", "east", "west", "up", "down"]:
            return "Go where?", player, location
            
        if direction == "down":
            bosses = [e for e in location.enemies if getattr(e, "is_boss", False) and not getattr(e, "is_dead", False)]
            if bosses:
                return f"The {bosses[0].name} blocks your path deeper into the dungeon!", player, location

        next_location_id = player.move(direction, location.exits)
        if next_location_id:
            # Clear dropped items when player successfully leaves the location
            original_item_count = len(location.items)
            location.items = [item for item in location.items if not getattr(item, 'is_dropped', False)]
            if len(location.items) != original_item_count:
                self.repo.create_location(location)

            # Check if entering an ungenerated dungeon floor
            new_loc = self.repo.get_location(next_location_id)
            if not new_loc and next_location_id.startswith("dng_"):
                parts = next_location_id.split("_") # dng_x_y_z_start
                x, y, z = int(parts[1]), int(parts[2]), int(parts[3])
                
                # Generate floor
                dungeon_locations = self.dungeon_gen.generate_floor(x, y, z)
                for loc in dungeon_locations:
                    self.repo.create_location(loc)
                    
                new_loc = self.repo.get_location(next_location_id)

            player.current_location_id = next_location_id
            self.repo.save_player(player)
            
            # Trap logic
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

            time_msg = self._advance_time_and_events(world_time, player, 10)
            
            if new_loc:
                self._ensure_neighbors(new_loc)
                return f"You travel {direction}...{trap_msg}{time_msg}", player, new_loc
            return f"You travel {direction}...{trap_msg}{time_msg}", player, location
        return "You can't go that way.", player, location

    def _parse_item_arg(self, arg_str: str) -> Tuple[str, int]:
        parts = arg_str.strip().split()
        if not parts:
            return "", 1
        if parts[-1].isdigit():
            return " ".join(parts[:-1]), int(parts[-1])
        return arg_str, 1

    def take_item(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        
        item_name, quantity = self._parse_item_arg(arg_str)
        if not item_name: return "Take what?", player, location
        
        taken_count = 0
        taken_names = []
        for _ in range(quantity):
            found_item = location.remove_item(item_name)
            if not found_item:
                break
            
            if player.current_weight + found_item.weight > player.stats.max_weight:
                location.add_item(found_item) # put it back
                msg = f"Inventory full! ({player.current_weight:.1f}/{player.stats.max_weight:.1f})."
                if taken_count > 0:
                    msg = f"You grabbed {taken_count}x {taken_names[-1]} before getting too heavy. {msg}"
                return msg, player, location
                
            # Reset is_dropped if it was a player-dropped item
            found_item.is_dropped = False
            player.add_item(found_item)
            taken_count += 1
            taken_names.append(found_item.name)

        if taken_count == 0:
            return "You don't see that here.", player, location

        time_cost = 1
        name_display = taken_names[0]
        base_msg = f"You picked up {taken_count}x {name_display}."
        
        enemy_log, is_dead = self._process_enemy_turns(player, location)
        base_msg += enemy_log
        
        self.repo.save_player(player)
        self.repo.create_location(location)
        time_msg = self._advance_time_and_events(world_time, player, time_cost)
        
        if is_dead:
            return base_msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg + time_msg, player, location

    def drop_item(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        
        item_name, quantity = self._parse_item_arg(arg_str)
        if not item_name: return "Drop what?", player, location
        
        dropped_count = 0
        dropped_names = []
        for _ in range(quantity):
            found_item = player.remove_item(item_name)
            if not found_item:
                break
            found_item.is_dropped = True
            location.add_item(found_item)
            dropped_count += 1
            dropped_names.append(found_item.name)

        if dropped_count == 0:
            return "You don't have that.", player, location

        time_cost = 1
        name_display = dropped_names[0]
        base_msg = f"You dropped {dropped_count}x {name_display}."
        
        enemy_log, is_dead = self._process_enemy_turns(player, location)
        base_msg += enemy_log

        self.repo.save_player(player)
        self.repo.create_location(location)
        time_msg = self._advance_time_and_events(world_time, player, time_cost)
        
        if is_dead:
            return base_msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg + time_msg, player, location

    def equip_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        
        if not item_name:
            return "Equip what?", player, location
            
        found_item = next((i for i in player.inventory if i.name.lower() == item_name.lower()), None)
        if not found_item:
            return f"You don't have a '{item_name}' in your inventory.", player, location
            
        base_msg = player.equip(found_item)
        
        enemy_log, is_dead = self._process_enemy_turns(player, location)
        base_msg += enemy_log
        
        self.repo.save_player(player)
        if is_dead:
            return base_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg, player, location

    def unequip_item(self, player_id: str, slot: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        
        if not slot:
            return "Unequip from what slot?", player, location
            
        base_msg = player.unequip(slot)
        
        enemy_log, is_dead = self._process_enemy_turns(player, location)
        base_msg += enemy_log
        
        self.repo.save_player(player)
        if is_dead:
            return base_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg, player, location

    def _process_enemy_turns(self, player: Player, location: Location, excluded_enemy_id: str = None) -> Tuple[str, bool]:
        """
        Allows all enemies in the location (except excluded_enemy_id) to attack the player.
        Returns a tuple: (combat_log_string, is_player_dead_boolean)
        """
        if not getattr(location, 'enemies', None):
            return "", False
            
        combat_log = ""
        armor = player.equipment.get("armor")
        mitigation = 0
        if armor and "defense" in armor.stat_bonuses:
            mitigation = armor.stat_bonuses["defense"]

        is_dead = False
        for enemy in location.enemies:
            if enemy.id == excluded_enemy_id or enemy.is_dead:
                continue
                
            enemy_dmg = max(1, enemy.attack)
            final_dmg = max(1, enemy_dmg - mitigation)
            player.take_damage(final_dmg)
            
            combat_log += f"\n{enemy.name} attacks you for {final_dmg} damage! (Your HP: {player.stats.hp}/{player.stats.max_hp})"
            
            if not player.is_alive():
                combat_log += "\nYou have been defeated...\nYou wake up back at the start, feeling woozy."
                player.heal()
                player.current_location_id = "loc_0_0_0"
                is_dead = True
                break
                
        return combat_log, is_dead

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
            
            # Chance to drop worn equipment (10%)
            import random
            if random.random() < 0.10:
                from app.core.domain.item import Item, ItemType
                import uuid
                equipment_pool = [
                    {"name": "Rusty Sword", "type": ItemType.WEAPON, "desc": "An old sword, heavily rusted.", "weight": 3.0, "slot": "weapon", "stats": {"strength": 1}, "durability": 5, "max_durability": 100},
                    {"name": "Torn Tunic", "type": ItemType.ARMOR, "desc": "A moth-eaten cloth tunic.", "weight": 1.0, "slot": "armor", "stats": {"defense": 1}, "durability": 10, "max_durability": 100}
                ]
                choice = random.choice(equipment_pool)
                item = Item(
                    id=str(uuid.uuid4()),
                    name=choice["name"],
                    description=choice["desc"],
                    item_type=choice["type"],
                    value=5,
                    weight=choice["weight"],
                    equip_slot=choice["slot"],
                    stat_bonuses=choice["stats"],
                    durability=choice["durability"],
                    max_durability=choice["max_durability"]
                )
                location.items.append(item)
                combat_log += f"\n{enemy.name} dropped a {item.name}!"
            
            self.repo.save_player(player)
            self.repo.create_location(location)
            time_msg = self._advance_time_and_events(world_time, player, 2)
            return combat_log + time_msg, player, location
            
        # Enemy retaliates (the one being attacked)
        enemy_dmg = max(1, enemy.attack)
        armor = player.equipment.get("armor")
        mitigation = 0
        if armor and "defense" in armor.stat_bonuses:
            mitigation = armor.stat_bonuses["defense"]
            
        final_dmg = max(1, enemy_dmg - mitigation)
        player.take_damage(final_dmg)
        combat_log += f"\n{enemy.name} retaliates for {final_dmg} damage! (Your HP: {player.stats.hp}/{player.stats.max_hp})"
        
        # Other enemies attack
        other_combat_log, _ = self._process_enemy_turns(player, location, excluded_enemy_id=enemy.id)
        combat_log += other_combat_log
        
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
            nx, ny = loc.coordinates.x, loc.coordinates.y
            dx = nx - x
            dy = ny - y
            
            # Distance
            dist = max(abs(dx), abs(dy))
            
            report_name = loc.name
            
            # Detect vertical connections
            if z == 0 and "down" in loc.exits:
                report_name = "Cave Entrance"
            elif z < 0 and "up" in loc.exits:
                report_name = "Surface Exit"
            # Filter generic names if no special exits
            import re
            generic_biomes = ["Forest", "Desert", "Wilderness", "Deep Cavern", "Mountain", "Plains", "Forest Area", "Desert Area"]
            is_generic_biome = any(loc.name.startswith(b) for b in generic_biomes)
            if is_generic_biome and re.search(r"\s-?\d+,-?\d+$", loc.name):
                continue

            # Skip reporting the exact same location unless it's a special POI or exit
            if dist == 0 and report_name == loc.name:
                continue
                
            # Simple cardinal logic
            dir_str = ""
            if dy > 0: dir_str += "North"
            elif dy < 0: dir_str += "South"
            
            if dx > 0: dir_str += "East" if not dir_str else "-East"
            elif dx < 0: dir_str += "West" if not dir_str else "-West"
            
            dir_text = f"{dist} chunks {dir_str}" if dist > 0 else "Here"
            found_landmarks.append(f"- {report_name} ({dir_text})")
            scouted_data.append({
                "name": report_name,
                "distance": dist,
                "direction": dir_str if dist > 0 else "Here"
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
            import math
            dx = location.coordinates.x - target_loc.coordinates.x
            dy = location.coordinates.y - target_loc.coordinates.y
            dist = math.ceil(math.sqrt(dx*dx + dy*dy))
        else:
            # If undefined coordinates, assume a baseline distance
            dist = 5
            
        energy_cost = dist * 2
        time_cost = dist * 10
        
        if player.stats.hp <= energy_cost:
            return f"You are too exhausted to make the journey to {waypoint_name} (Requires {energy_cost} HP).", player, location
            
        player.take_damage(energy_cost)
        player.current_location_id = target_loc.id
        self.repo.save_player(player)
        
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, time_cost)
        
        travel_narrative = f"You traveled to {waypoint_name}, covering a great distance. You spent {energy_cost} HP."
            
        return f"{travel_narrative}{time_msg}", player, target_loc

    def list_chest(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if location.id not in player.waypoints.values():
            return "There is no camp chest here.", player, location
            
        if not location.camp_storage:
            return "The camp chest is empty.", player, location
            
        counts = Counter((i.name, i.item_type) for i in location.camp_storage)
        items_list = []
        for (name, item_type), count in sorted(counts.items()):
            display = f"- {name} ({item_type})"
            if count > 1: display += f" x{count}"
            items_list.append(display)
            
        return "Camp Chest Contents:\n" + "\n".join(items_list), player, location

    def store_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if location.id not in player.waypoints.values():
            return "There is no camp chest here to store items.", player, location
            
        if not item_name:
            return "Store what?", player, location
            
        found_item = player.remove_item(item_name)
        if found_item:
            location.store_camp_item(found_item)
            
            base_msg = f"You stored {found_item.name} in the camp chest."
            enemy_log, is_dead = self._process_enemy_turns(player, location)
            base_msg += enemy_log
            
            self.repo.save_player(player)
            self.repo.create_location(location)
            
            if is_dead:
                return base_msg, player, self.repo.get_location("loc_0_0_0") or location
            return base_msg, player, location
            
        return f"You don't have '{item_name}'.", player, location

    def retrieve_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if location.id not in player.waypoints.values():
            return "There is no camp chest here to retrieve items from.", player, location
            
        if not item_name:
            return "Retrieve what?", player, location
            
        found_item = location.retrieve_camp_item(item_name)
        if found_item:
            if player.current_weight + found_item.weight > player.stats.max_weight:
                location.store_camp_item(found_item) # put it back
                return f"You cannot carry {found_item.name}, it is too heavy.", player, location
                
            player.add_item(found_item)
            
            base_msg = f"You retrieved {found_item.name} from the camp chest."
            enemy_log, is_dead = self._process_enemy_turns(player, location)
            base_msg += enemy_log
            
            self.repo.save_player(player)
            self.repo.create_location(location)
            
            if is_dead:
                return base_msg, player, self.repo.get_location("loc_0_0_0") or location
            return base_msg, player, location
            
        return f"There is no '{item_name}' in the camp chest.", player, location

    def process_command(self, player_id: str, command_text: str) -> Tuple:
        args = command_text.lower().split()
        if not args:
            player, location = self._get_player_and_location(player_id)
            return "Please enter a command.", player, location
        
        action = args[0]
        arg_str = " ".join(args[1:])
        
        if action in ["go", "move", "walk", "north", "south", "east", "west", "up", "down", "enter", "climb"]:
            dir = args[1] if len(args) > 1 else action
            msg, p, l = self.move_player(player_id, dir)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["look", "examine"]:
            msg, p, l = self.look(player_id)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["scout", "radar", "map"]:
            res = self.scout_area(player_id)
            msg, p, l = self._post_process_special_encounters(res[0], res[1], res[2])
            return msg, p, l, res[3]
        elif action in ["stats", "status"]:
            player, location = self._get_player_and_location(player_id)
            msg = str(player.stats)
            return self._post_process_special_encounters(msg, player, location)
        elif action in ["take", "get", "pickup", "grab"]:
            msg, p, l = self.take_item(player_id, arg_str)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["drop", "discard"]:
            msg, p, l = self.drop_item(player_id, arg_str)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["equip", "wear", "wield"]:
            msg, p, l = self.equip_item(player_id, arg_str)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["unequip", "remove"]:
            msg, p, l = self.unequip_item(player_id, arg_str)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["inventory", "inv", "i"]:
            msg, p, l = self.map_inventory(player_id)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["attack", "fight", "hit", "kill"]:
            msg, p, l = self.attack_enemy(player_id, arg_str)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["camp", "waypoint"]:
            msg, p, l = self.create_camp(player_id, arg_str)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["travel", "fasttravel"]:
            msg, p, l = self.fast_travel(player_id, arg_str)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["chest", "storage"]:
            msg, p, l = self.list_chest(player_id)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["store", "stash"]:
            msg, p, l = self.store_item(player_id, arg_str)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["retrieve", "withdraw"]:
            msg, p, l = self.retrieve_item(player_id, arg_str)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["consume", "eat", "drink", "use"]:
            msg, p, l = self.consume_item(player_id, arg_str)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["fill", "refill"]:
            msg, p, l = self.fill_flask(player_id, arg_str)
            return self._post_process_special_encounters(msg, p, l)
        elif action in ["time", "clock", "date"]:
            player, location = self._get_player_and_location(player_id)
            msg = self.get_time_status()
            return self._post_process_special_encounters(msg, player, location)
        
        player, location = self._get_player_and_location(player_id)
        msg = "I don't understand that command."
        
        # We need to wrap all returns to append the special message if applicable
        # But for now let's just use a helper to post-process the message
        return self._post_process_special_encounters(msg, player, location)

    def _post_process_special_encounters(self, message: str, player: Player, location: Location) -> Tuple[str, Player, Location]:
        # Special Goblin Encounter at 4,4,0
        if location.coordinates and location.coordinates.x == 4 and location.coordinates.y == 4 and location.coordinates.z == 0:
            if any(e.name == "Friendly Goblin" and not getattr(e, "is_dead", False) for e in location.enemies):
                special_msg = "\n\n[SPECIAL] A goblin has given you such an... intense 'welcome' that you've discovered new meanings for the word 'flexibility'. He seems to have thoroughly enjoyed your company!"
                if special_msg not in message:
                    message += special_msg
        return message, player, location

    def _apply_survival_mechanics(self, time_passed: int, player: Player) -> str:
        if not hasattr(player, "stats"):
            return ""
            
        msg = ""
        hunger_loss = max(0, time_passed // 10)
        thirst_loss = max(0, time_passed // 8)
        
        # Always at least 1 loss if time_passed > 0 and we want to be strict? 
        # No, small actions (1 tick) shouldn't drain hunger.
        if hunger_loss > 0:
            player.stats.hunger = max(0, player.stats.hunger - hunger_loss)
        if thirst_loss > 0:
            player.stats.thirst = max(0, player.stats.thirst - thirst_loss)
            
        is_starving = player.stats.hunger == 0
        is_dehydrated = player.stats.thirst == 0
        
        damage = 0
        if is_starving:
            damage += max(1, time_passed // 10)
            msg += "\nYou are starving! You lose HP."
        if is_dehydrated:
            damage += max(1, time_passed // 8)
            msg += "\nYou are dehydrated! You lose HP."
            
        if damage > 0:
            player.take_damage(damage)
        elif player.stats.hp < player.stats.max_hp and time_passed >= 10:
            # Heal if not starving/dehydrated and significant time passed
            heal_amount = time_passed // 10
            player.stats.hp = min(player.stats.max_hp, player.stats.hp + heal_amount)
            
        return msg

    def consume_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not item_name: return "Consume what?", player, location
        
        found_item = player.remove_item(item_name)
        if not found_item:
            return f"You don't have '{item_name}'.", player, location
            
        item_type_str = str(found_item.item_type).lower()
        if not item_type_str.endswith("consumable"):
            player.add_item(found_item) # Put it back
            return f"{found_item.name} is not consumable.", player, location
            
        # Apply effects
        msg = f"You consumed {found_item.name}."
        
        if found_item.restore_hp != 0 or found_item.restore_hp_pct != 0:
            pct_restore = int(player.stats.max_hp * found_item.restore_hp_pct)
            total_hp_restore = found_item.restore_hp + pct_restore
            player.stats.hp = min(player.stats.max_hp, max(0, player.stats.hp + total_hp_restore))
            action_word = "Restored" if total_hp_restore > 0 else "Lost"
            msg += f" {action_word} {abs(total_hp_restore)} HP."
            
        if found_item.restore_mp != 0 or found_item.restore_mp_pct != 0:
            pct_restore = int(player.stats.max_mp * found_item.restore_mp_pct)
            total_mp_restore = found_item.restore_mp + pct_restore
            player.stats.mp = min(player.stats.max_mp, max(0, player.stats.mp + total_mp_restore))
            action_word = "Restored" if total_mp_restore > 0 else "Lost"
            msg += f" {action_word} {abs(total_mp_restore)} MP."
        if found_item.restore_hunger != 0:
            player.stats.hunger = min(100, max(0, player.stats.hunger + found_item.restore_hunger))
            action_word = "Restored" if found_item.restore_hunger > 0 else "Lost"
            msg += f" {action_word} {abs(found_item.restore_hunger)} Hunger."
        if found_item.restore_thirst != 0:
            player.stats.thirst = min(100, max(0, player.stats.thirst + found_item.restore_thirst))
            action_word = "Restored" if found_item.restore_thirst > 0 else "Lost"
            msg += f" {action_word} {abs(found_item.restore_thirst)} Thirst."
            
        # Process arbitrary effects if any
        for effect in found_item.effects:
            if effect.get("type") == "heal":
                amount = effect.get("amount", 0)
                player.stats.hp = min(player.stats.max_hp, player.stats.hp + amount)
                msg += f" Restored {amount} HP."
                
        self.repo.save_player(player)
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, 1)
        
        return msg + time_msg, player, location

    def fill_flask(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        
        # Check for water source
        has_water = any(inter.startswith("water_source:") for inter in location.interactables)
        if not has_water:
            return "There is no water source here to fill anything.", player, location
            
        # Find empty flask
        empty_flask = next((i for i in player.inventory if i.name.lower() == "empty flask"), None)
        if not empty_flask:
            return "You don't have an Empty Flask to fill.", player, location
            
        # Replace Empty Flask with Water Flask
        player.remove_item("Empty Flask")
        
        from app.core.domain.item import Item, ItemType
        import uuid
        water_flask = Item(
            id=str(uuid.uuid4()),
            name="Water Flask",
            description="A flask filled with fresh water.",
            item_type=ItemType.CONSUMABLE,
            restore_thirst=40,
            value=2,
            weight=1.0
        )
        player.add_item(water_flask)
        
        msg = "You fill the Empty Flask with water."
        self.repo.save_player(player)
        
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, 2)
        
        return msg + time_msg, player, location

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

    def fill_vessel(self, player_id: str, item_name: str = None) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        # Check for water_source in interactables
        if "water_source" not in location.interactables:
             return "There is no water source here.", player, location
             
        found_flask = None
        if item_name:
            found_flask = player.remove_item(item_name)
            if not found_flask:
                return f"You don't have '{item_name}'.", player, location
        else:
            # Fallback to first empty flask if no name provided
            for item in player.inventory:
                if "Empty" in item.name and "Flask" in item.name:
                    found_flask = player.remove_item(item.name)
                    break
        
        if not found_flask:
            return "You don't have an empty flask to fill.", player, location
            
        if "Empty" not in found_flask.name or "Flask" not in found_flask.name:
            player.add_item(found_flask) # Put it back
            return f"You can't fill {found_flask.name}.", player, location

        # Transform it
        from app.core.domain.item import ItemType
        found_flask.name = "Water Flask (Full)"
        found_flask.description = "A flask filled with fresh water."
        found_flask.item_type = ItemType.CONSUMABLE
        found_flask.restore_thirst = 30
        found_flask.restore_hunger = 0
        found_flask.restore_hp = 0
        
        player.add_item(found_flask) # Put back the transformed item
        self.repo.save_player(player)
        return f"You filled the {found_flask.name} from the {location.name}.", player, location

