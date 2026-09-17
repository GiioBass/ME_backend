from typing import Tuple, Optional, List
from collections import Counter
import random
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.ports.repositories import GameRepository
from app.core.use_cases.world_generator import WorldGenerator
from app.core.use_cases.static_area_loader import StaticAreaLoader
from app.core.use_cases.dungeon_generator import DungeonGenerator
from app.core.use_cases.data_loader import DataLoader
from app.core.config import settings

from app.core.use_cases.services.movement_service import MovementService
from app.core.use_cases.services.combat_service import CombatService
from app.core.use_cases.services.inventory_service import InventoryService
from app.core.use_cases.services.survival_service import SurvivalService
from app.core.use_cases.services.crafting_service import CraftingService
from app.core.use_cases.services.quest_service import QuestService
from app.core.use_cases.services.dialogue_service import DialogueService
from app.core.use_cases.services.skill_service import SkillService

class GameService:
    def __init__(self, repository: GameRepository):
        self.repo = repository
        loader = DataLoader(repository)
        self.world_config = loader.get_world_config()
        self.loot_tables = loader.get_loot_tables()
        self.enemies_config = loader.get_enemies_config()
        self.game_settings = loader.get_game_settings()

        self.world_gen = WorldGenerator(
            repo=repository, 
            world_config=self.world_config, 
            loot_tables=self.loot_tables, 
            enemies_config=self.enemies_config
        )
        self.static_area_loader = StaticAreaLoader()
        self.dungeon_gen = DungeonGenerator(
            repo=repository, 
            loot_tables=self.loot_tables, 
            enemies_config=self.enemies_config
        )

        # Initialize core sub-services
        common_kwargs = {
            "repository": self.repo,
            "world_gen": self.world_gen,
            "dungeon_gen": self.dungeon_gen,
            "game_settings": self.game_settings
        }
        self.quest_service = QuestService(**common_kwargs)
        self.movement_service = MovementService(**common_kwargs)
        self.combat_service = CombatService(**common_kwargs, quest_service=self.quest_service)
        self.inventory_service = InventoryService(**common_kwargs, quest_service=self.quest_service)
        self.survival_service = SurvivalService(**common_kwargs)
        self.crafting_service = CraftingService(**common_kwargs, quest_service=self.quest_service)
        self.dialogue_service = DialogueService(**common_kwargs, quest_service=self.quest_service)
        self.skill_service = SkillService(
            **common_kwargs, 
            combat_service=self.combat_service, 
            quest_service=self.quest_service
        )

        self._setup_command_registry()

    def _setup_command_registry(self):
        self.registry = {
            # Movement
            "north": self._cmd_move, "n": self._cmd_move,
            "south": self._cmd_move, "s": self._cmd_move,
            "east": self._cmd_move, "e": self._cmd_move,
            "west": self._cmd_move, "w": self._cmd_move,
            "up": self._cmd_move, "u": self._cmd_move,
            "down": self._cmd_move, "d": self._cmd_move,
            "go": self._cmd_move, "move": self._cmd_move, "walk": self._cmd_move,
            "enter": self._cmd_move, "climb": self._cmd_move,
            
            # General
            "look": lambda p, a: self.look(p), "l": lambda p, a: self.look(p),
            "examine": lambda p, a: self.look(p),
            "stats": self._cmd_stats, "status": self._cmd_stats,
            "inventory": lambda p, a: self.map_inventory(p), "inv": lambda p, a: self.map_inventory(p), "i": lambda p, a: self.map_inventory(p),
            "time": self._cmd_time,
            "help": self._cmd_help,
            "clear": lambda p, a: ("Terminal cleared.", *self._get_player_and_location(p)),
            "scout": self._cmd_scout, "radar": self._cmd_scout, "map": self._cmd_scout,

            # Interaction & Items
            "take": self.take_item, "get": self.take_item, "pickup": self.take_item, "grab": self.take_item,
            "drop": self.drop_item, "discard": self.drop_item,
            "consume": self._cmd_consume, "eat": self._cmd_consume, "drink": self._cmd_consume, "use": self._cmd_consume,
            "fill": self.fill_flask, "refill": self.fill_flask,
            "attack": self.attack_enemy, "fight": self.attack_enemy, "hit": self.attack_enemy, "kill": self.attack_enemy,

            # Equipment & Camp
            "equip": self.equip_item, "wear": self.equip_item, "wield": self.equip_item,
            "unequip": self.unequip_item, "remove": self.unequip_item,
            "camp": self.create_camp, "waypoint": self.create_camp,
            "travel": self.fast_travel, "fasttravel": self.fast_travel,
            "rest": lambda p, a: self.rest(p), "sleep": lambda p, a: self.rest(p), "wait": lambda p, a: self.rest(p),
            "chest": lambda p, a: self.list_chest(p), "storage": lambda p, a: self.list_chest(p),
            "store": self.store_item, "stash": self.store_item,
            "retrieve": self.retrieve_item, "withdraw": self.retrieve_item,
            
            # Crafting
            "craft": self.craft_item, "make": self.craft_item, "create": self.craft_item,
            "recipes": lambda p, a: self.get_recipes_list(p), "blueprints": lambda p, a: self.get_recipes_list(p), "formulas": lambda p, a: self.get_recipes_list(p),

            # NPCs, Dialogue & Economy
            "talk": self.talk_to_npc, "speak": self.talk_to_npc, "greet": self.talk_to_npc,
            "dialogue": self.choose_dialogue_option, "option": self.choose_dialogue_option, "say": self.choose_dialogue_option, "1": lambda p, a: self.choose_dialogue_option(p, "1"), "2": lambda p, a: self.choose_dialogue_option(p, "2"), "3": lambda p, a: self.choose_dialogue_option(p, "3"), "4": lambda p, a: self.choose_dialogue_option(p, "4"),
            "buy": self.buy_item, "purchase": self.buy_item,
            "sell": self.sell_item,
            "shop": self._cmd_shop,

            # Quests
            "quests": lambda p, a: self.list_player_quests(p), "quest": lambda p, a: self.list_player_quests(p), "journal": lambda p, a: self.list_player_quests(p),
            "turnin": self.turn_in_quest, "complete": self.turn_in_quest,

            # Classes & Skills
            "class": self.select_class, "choose_class": self.select_class,
            "skills": lambda p, a: self.list_skills(p), "spells": lambda p, a: self.list_skills(p), "abilities": lambda p, a: self.list_skills(p),
            "skill": self._cmd_skill, "cast": self._cmd_skill,

            # Admin
            "admin": self.admin_command, "god": self.admin_command,
        }

    # Command Registry Wrappers
    def _cmd_move(self, player_id: str, arg_str: str) -> Tuple:
        direction = arg_str if arg_str else "unknown" 
        return self.move_player(player_id, direction)

    def _cmd_stats(self, player_id: str, arg_str: str) -> Tuple:
        player, location = self._get_player_and_location(player_id)
        return str(player.stats), player, location

    def _cmd_time(self, player_id: str, arg_str: str) -> Tuple:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        return world_time.get_time_string(), player, location

    def _cmd_help(self, player_id: str, arg_str: str) -> Tuple:
        player, location = self._get_player_and_location(player_id)
        commands = self.repo.get_command_help()
        lines = ["Available Commands:"]
        for cmd in commands:
            lines.append(f"- {cmd['command']}: {cmd['description']}")
        lines.append("- talk [npc]: Talk to an NPC in the area.")
        lines.append("- dialogue [number/text]: Select dialogue choice.")
        lines.append("- buy [item] / sell [item]: Trade with merchants.")
        lines.append("- quests: Check your active and completed quest journal.")
        lines.append("- class [fighter/marksman/mage]: Pick your combat class.")
        lines.append("- skill [name] [target]: Cast active class skill in combat.")
        return "\n".join(lines), player, location

    def _cmd_scout(self, player_id: str, arg_str: str) -> Tuple:
        res = self.scout_area(player_id)
        msg, p, l = res[:3]
        scouted = res[3] if len(res) > 3 else None
        return msg, p, l, scouted

    def _cmd_consume(self, player_id: str, arg_str: str) -> Tuple:
        if not arg_str or arg_str == "water":
            msg, p, l = self.drink_from_source(player_id)
            if "no water source" not in msg:
                return msg, p, l
            if not arg_str:
                arg_str = "water" 
        return self.consume_item(player_id, arg_str)

    def _cmd_shop(self, player_id: str, arg_str: str) -> Tuple:
        player, location = self._get_player_and_location(player_id)
        npcs = self.dialogue_service.get_npcs_in_location(location.id)
        merchant = next((n for n in npcs if n.npc_type == "merchant" or n.shop_inventory), None)
        if not merchant:
            return "There is no merchant here to trade with.", player, location
        return self.dialogue_service._render_shop(merchant), player, location

    def _cmd_skill(self, player_id: str, arg_str: str) -> Tuple:
        raw = arg_str.strip()
        if not raw:
            return self.list_skills(player_id)
        
        # Check matching skill name from registry
        for skill_key in sorted(self.skill_service.skills_registry.keys(), key=len, reverse=True):
            if raw.lower().startswith(skill_key):
                target = raw[len(skill_key):].strip() or None
                return self.use_skill(player_id, skill_key, target)
                
        parts = raw.split()
        skill_name = parts[0]
        target = parts[1] if len(parts) > 1 else None
        return self.use_skill(player_id, skill_name, target)

    def _get_player_and_location(self, player_id: str) -> Tuple[Player, Location]:
        return self.movement_service._get_player_and_location(player_id)

    def _advance_time_and_events(self, world_time, player: Player, time_cost: int) -> str:
        return self.movement_service._advance_time_and_events(world_time, player, time_cost)

    def _ensure_neighbors(self, location: Location):
        self.movement_service._ensure_neighbors(location)

    def create_new_player(self, name: str, character_class: Optional[str] = None) -> Tuple[Player, Location]:
        existing_player = self.repo.get_player_by_name(name)
        if existing_player:
            raise ValueError(f"Player name '{name}' is already taken.")

        start_id = "loc_0_0_0"
        start_location = self.repo.get_location(start_id)
        if not start_location:
            generated_locations = self.world_gen.generate_chunk(start_x=-2, start_y=-2, size=5)
            static_locations = self.static_area_loader.load_static_areas()
            static_coords = {(loc.coordinates.x, loc.coordinates.y, loc.coordinates.z): loc for loc in static_locations if loc.coordinates}
            
            for loc in generated_locations:
                coords = (loc.coordinates.x, loc.coordinates.y, loc.coordinates.z)
                if coords in static_coords:
                    static_loc = static_coords[coords]
                    loc.name = static_loc.name
                    loc.description = static_loc.description
                    loc.interactables = static_loc.interactables
                self.repo.create_location(loc)
            start_location = self.repo.get_location(start_id)
            if not start_location:
                start_location = next((l for l in generated_locations if l.id == start_id), None)

        if start_location:
            self._ensure_neighbors(start_location)
            
        player = Player(name=name, current_location_id=start_id)
        saved_player = self.repo.save_player(player)

        if character_class:
            self.select_class(saved_player.id, character_class)
            saved_player = self.repo.get_player(saved_player.id)

        return saved_player, start_location

    def login_player(self, name: str) -> Tuple[Player, Location]:
        player = self.repo.get_player_by_name(name)
        if not player:
            raise ValueError(f"Player '{name}' not found.")
        
        location = self.repo.get_location(player.current_location_id)
        if not location:
            location = self.world_gen.generate_limbo()
            
        return player, location

    def look(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        
        base_desc = location.description
        if world_time and world_time.is_night():
            base_desc = f"[NIGHT] {base_desc} (It is dark)"
        
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

        # Display NPCs in this location
        npcs = self.dialogue_service.get_npcs_in_location(location.id)
        if npcs:
            npc_names = [f"{n.name} ({n.title})" if n.title else n.name for n in npcs]
            base_desc += f"\nPeople here: {', '.join(npc_names)}"
        
        # Special Goblin Encounter at 4,4,0
        if location.coordinates and location.coordinates.x == 4 and location.coordinates.y == 4 and location.coordinates.z == 0:
            if any(e.name == "Friendly Goblin" and not getattr(e, "is_dead", False) for e in location.enemies):
                base_desc += "\n\n[SPECIAL] A goblin has given you such an... intense 'welcome' that you've discovered new meanings for the word 'flexibility'. He seems to have thoroughly enjoyed your company!"
            
        return base_desc, player, location

    # Delegated Methods
    def map_inventory(self, player_id: str) -> Tuple[str, Player, Location]:
        return self.inventory_service.map_inventory(player_id)

    def move_player(self, player_id: str, direction: str) -> Tuple[str, Player, Location]:
        return self.movement_service.move_player(player_id, direction)

    def take_item(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        return self.inventory_service.take_item(player_id, arg_str)

    def drop_item(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        return self.inventory_service.drop_item(player_id, arg_str)

    def equip_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        return self.inventory_service.equip_item(player_id, item_name)

    def unequip_item(self, player_id: str, slot: str) -> Tuple[str, Player, Location]:
        return self.inventory_service.unequip_item(player_id, slot)

    def attack_enemy(self, player_id: str, target_name: str) -> Tuple[str, Player, Location]:
        return self.combat_service.attack_enemy(player_id, target_name)

    def scout_area(self, player_id: str) -> Tuple[str, Player, Location, list]:
        return self.movement_service.scout_area(player_id)

    def create_camp(self, player_id: str, camp_name: str) -> Tuple[str, Player, Location]:
        return self.movement_service.create_camp(player_id, camp_name)

    def fast_travel(self, player_id: str, waypoint_name: str) -> Tuple[str, Player, Location]:
        return self.movement_service.fast_travel(player_id, waypoint_name)

    def list_chest(self, player_id: str) -> Tuple[str, Player, Location]:
        return self.inventory_service.list_chest(player_id)

    def store_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        return self.inventory_service.store_item(player_id, item_name)

    def retrieve_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        return self.inventory_service.retrieve_item(player_id, item_name)

    def consume_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        return self.survival_service.consume_item(player_id, item_name)

    def fill_flask(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        return self.survival_service.fill_flask(player_id, arg_str)

    def drink_from_source(self, player_id: str) -> Tuple[str, Player, Location]:
        return self.survival_service.drink_from_source(player_id)

    def rest(self, player_id: str) -> Tuple[str, Player, Location]:
        return self.survival_service.rest(player_id)

    def get_recipes_list(self, player_id: str) -> Tuple[str, Player, Location]:
        return self.crafting_service.get_recipes_list(player_id)

    def craft_item(self, player_id: str, recipe_name: str) -> Tuple[str, Player, Location]:
        return self.crafting_service.craft_item(player_id, recipe_name)

    # NPCs, Dialogue & Quests Delegations
    def talk_to_npc(self, player_id: str, npc_name: str) -> Tuple[str, Player, Location]:
        return self.dialogue_service.talk_to_npc(player_id, npc_name)

    def choose_dialogue_option(self, player_id: str, choice_input: str) -> Tuple[str, Player, Location]:
        return self.dialogue_service.choose_dialogue_option(player_id, choice_input)

    def buy_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        return self.dialogue_service.buy_item(player_id, item_name)

    def sell_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        return self.dialogue_service.sell_item(player_id, item_name)

    def list_player_quests(self, player_id: str) -> Tuple[str, Player, Location]:
        return self.quest_service.list_player_quests(player_id)

    def turn_in_quest(self, player_id: str, quest_id: str) -> Tuple[str, Player, Location]:
        return self.quest_service.turn_in_quest(player_id, quest_id)

    def select_class(self, player_id: str, class_name: str) -> Tuple[str, Player, Location]:
        return self.skill_service.select_class(player_id, class_name)

    def list_skills(self, player_id: str) -> Tuple[str, Player, Location]:
        return self.skill_service.list_skills(player_id)

    def use_skill(self, player_id: str, skill_name: str, target_name: Optional[str] = None) -> Tuple[str, Player, Location]:
        return self.skill_service.use_skill(player_id, skill_name, target_name)

    def get_command_help(self) -> list:
        return self.repo.get_command_help()

    def get_time_status(self) -> str:
        world_time = self.repo.get_world_time()
        return f"It is {world_time.get_time_string()}."

    def process_command(self, player_id: str, command_text: str) -> Tuple:
        raw_args = command_text.split()
        if not raw_args:
            player, location = self._get_player_and_location(player_id)
            return "Please enter a command.", player, location
        
        action = raw_args[0].lower()
        arg_str = " ".join(raw_args[1:])
        
        handler = self.registry.get(action)
        if not handler:
            player, location = self._get_player_and_location(player_id)
            return f"Unknown command: '{action}'. Type 'help' for a list of commands.", player, location

        if action in ["north", "south", "east", "west", "up", "down", "n", "s", "e", "w", "u", "d"] and not arg_str:
            arg_str = action

        res = handler(player_id, arg_str)
        
        msg, p, l = res[:3]
        scouted = res[3] if len(res) > 3 else None
        
        final_msg, final_p, final_l = self._post_process_special_encounters(msg, p, l)
        
        if not final_p.is_alive():
            final_p.heal()
            final_p.current_location_id = "loc_0_0_0"
            self.repo.save_player(final_p)
            final_l = self.repo.get_location("loc_0_0_0")
            if not final_l:
                final_l = self.world_gen.generate_start_location()
            final_msg += "\n\n*** YOU DIED ***\nYou succumbed to the harsh elements and perished. You wake up at the start."

        if scouted is not None:
            return final_msg, final_p, final_l, scouted
        return final_msg, final_p, final_l

    def _post_process_special_encounters(self, message: str, player: Player, location: Location) -> Tuple[str, Player, Location]:
        if location.coordinates and location.coordinates.x == 4 and location.coordinates.y == 4 and location.coordinates.z == 0:
            if any(e.name == "Friendly Goblin" and not getattr(e, "is_dead", False) for e in location.enemies):
                special_msg = "\n\n[SPECIAL] A goblin has given you such an... intense 'welcome' that you've discovered new meanings for the word 'flexibility'. He seems to have thoroughly enjoyed your company!"
                if special_msg not in message:
                    message += special_msg
        return message, player, location

    def admin_command(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        parts = arg_str.split()
        
        SYSTEM_KEY = self.game_settings.get("admin", {}).get("system_key", "ME_ROOT_2026")
        if not parts or parts[0].upper() != SYSTEM_KEY:
            return "Unauthorized access to system override. Protocol terminated.", player, location
            
        if len(parts) < 2:
            return "Admin authenticated. Subcommands: heal, god, gold [amount], tp [x] [y], give [item]", player, location
            
        sub = parts[1].lower()
        if sub == "heal":
            player.heal()
            player.stats.hunger = 100
            player.stats.thirst = 100
            msg = "[ADMIN] Vitality restored to 100%."
        elif sub == "god":
            player.stats.max_hp = 9999
            player.stats.hp = 9999
            player.stats.strength = 100
            msg = "[ADMIN] God Mode engaged."
        elif sub == "gold":
            amt = int(parts[2]) if len(parts) >= 3 else 100
            player.stats.gold += amt
            msg = f"[ADMIN] Added {amt} Gold. Total Gold: {player.stats.gold}g."
        elif sub in ["teleport", "tp"]:
            if len(parts) >= 4:
                try:
                    tx, ty = int(parts[2]), int(parts[3])
                    target_id = f"loc_{tx}_{ty}_0"
                    target_loc = self.repo.get_location(target_id)
                    if not target_loc:
                        target_loc = self.world_gen.generate_single_location(tx, ty, 0)
                        self.repo.create_location(target_loc)
                    player.current_location_id = target_loc.id
                    location = target_loc
                    msg = f"[ADMIN] Teleported to {tx}, {ty}."
                except:
                    msg = "[ADMIN] Invalid coordinates."
            else:
                msg = "[ADMIN] Usage: admin [key] tp [x] [y]"
        elif sub == "give":
            if len(parts) >= 3:
                item_name = " ".join(parts[2:])
                from app.core.domain.item import Item
                import uuid
                
                template = self.repo.get_item_by_name(item_name)
                if template:
                    item = Item(**template.model_dump())
                    item.id = str(uuid.uuid4())
                    player.add_item(item)
                    msg = f"[ADMIN] Item '{item.name}' granted."
                else:
                    msg = f"[ADMIN] Item '{item_name}' not found in registry."
            else:
                msg = "[ADMIN] Usage: admin [key] give [item_name]"
        else:
            msg = f"[ADMIN] Unknown subcommand: {sub}"
            
        self.repo.save_player(player)
        return msg, player, location
