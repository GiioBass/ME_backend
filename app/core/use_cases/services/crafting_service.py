from typing import Tuple, List
from collections import Counter
import uuid
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.core.domain.item import Item
from app.core.config import settings
from app.core.use_cases.services.base_service import BaseGameService

class CraftingService(BaseGameService):
    def __init__(self, repository, world_gen=None, dungeon_gen=None, game_settings=None, quest_service=None):
        super().__init__(repository, world_gen, dungeon_gen, game_settings)
        self.quest_service = quest_service

    def _get_recipes(self) -> List:
        recipes = self.repo.get_recipes()
        if not recipes:
            from app.core.use_cases.data_loader import DataLoader
            loader = DataLoader(self.repo)
            loader.seed_items()
            loader.seed_recipes()
            recipes = self.repo.get_recipes()
        return recipes

    def get_recipes_list(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        recipes = self._get_recipes()
        if not recipes:
            return "No recipes discovered yet.", player, location
            
        lines = ["Available Recipes:"]
        for r in recipes:
            ing_list = ", ".join([f"{name} x{qty}" for name, qty in r.ingredients.items()])
            req_station = getattr(r, 'required_station', None)
            station_info = f" (Requires: {req_station})" if req_station and req_station != "none" else ""
            lines.append(f"- {r.name}: {ing_list}{station_info}")
            
        return "\n".join(lines), player, location

    def craft_item(self, player_id: str, recipe_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not recipe_name:
            return "Craft what? Use 'recipes' to see available options.", player, location
            
        recipes = self._get_recipes()
        recipe = next((r for r in recipes if r.name.lower() == recipe_name.lower()), None)
        
        if not recipe:
            return f"Recipe for '{recipe_name}' not found.", player, location
            
        # Check required station if present
        req_station = getattr(recipe, 'required_station', None)
        if req_station and req_station.lower() not in ["none", ""]:
            # Check if current location has the workstation interactable
            station_match = any(req_station.lower() in str(inter).lower() for inter in getattr(location, 'interactables', []))
            if not station_match:
                return f"You need a {req_station.replace('_', ' ').title()} nearby to craft {recipe.name}.", player, location

        # Check ingredients
        inv_counts = Counter(item.name for item in player.inventory)
        missing = []
        for ing_name, qty in recipe.ingredients.items():
            if inv_counts[ing_name] < qty:
                missing.append(f"{ing_name} (need {qty - inv_counts[ing_name]} more)")
                
        if missing:
            return f"Missing ingredients: {', '.join(missing)}", player, location
            
        # Consume ingredients
        for ing_name, qty in recipe.ingredients.items():
            count = 0
            new_inv = []
            for item in player.inventory:
                if item.name == ing_name and count < qty:
                    count += 1
                    continue
                new_inv.append(item)
            player.inventory = new_inv
            
        # Create result items
        result_template = recipe.result_template
        if not result_template:
            result_template = self.repo.get_item_by_name(recipe.result_item_id) or self.repo.get_item_by_name(recipe.name)
            
        for _ in range(recipe.result_qty):
            if result_template:
                new_item = Item(**result_template.model_dump())
            else:
                from app.core.domain.item import ItemType
                new_item = Item(name=recipe.name, description=recipe.description, item_type=ItemType.MATERIAL, value=10, weight=1.0)
            new_item.id = str(uuid.uuid4())
            player.add_item(new_item)
            
        msg = f"Successfully crafted {recipe.result_qty}x {recipe.name}!"
        if self.quest_service:
            q_msg = self.quest_service.update_craft_progress(player, recipe.name)
            msg += q_msg
        
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, settings.TIME_COST_CRAFT)
        
        self.repo.save_player(player)
        return msg + time_msg, player, location
