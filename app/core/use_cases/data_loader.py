import json
import os
from app.ports.repositories import GameRepository
from app.core.domain.location import Location, Coordinates

class DataLoader:
    def __init__(self, repo: GameRepository):
        self.repo = repo
        self.data_path = os.path.join(os.path.dirname(__file__), "../../../data")

    def load_static_locations(self):
        file_path = os.path.join(self.data_path, "static_locations.json")
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found.")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for loc_data in data:
                # loc_0_0_0 must be generated through the world_generator.generate_chunk now
                if loc_data["id"] == "loc_0_0_0":
                    continue
                # Check if it already exists
                existing = self.repo.get_location(loc_data["id"])
                if not existing:
                    # Construct Domain Location
                    coordinates = None
                    if "coordinates" in loc_data:
                        coordinates = Coordinates(
                            x=loc_data["coordinates"]["x"],
                            y=loc_data["coordinates"]["y"],
                            z=loc_data["coordinates"]["z"]
                        )
                    
                    loc = Location(
                        id=loc_data["id"],
                        name=loc_data["name"],
                        description=loc_data["description"],
                        exits=loc_data.get("exits", {}),
                        interactables=loc_data.get("interactables", []),
                        coordinates=coordinates
                    )
                    
                    self.repo.create_location(loc)
                    print(f"Loaded static location: {loc.name} ({loc.id})")

    def load_commands(self):
        file_path = os.path.join(self.data_path, "commands.json")
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found.")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for cmd_data in data:
                self.repo.create_command_help(
                    command=cmd_data["command"],
                    description=cmd_data["description"],
                    usage=cmd_data["usage"],
                    category=cmd_data["category"],
                    alias=cmd_data.get("alias")
                )
        print(f"Seeded {len(data)} commands from JSON.")

    def seed_items(self):
        from app.core.domain.item import Item
        files = ["consumables.json", "materials.json", "equipment.json"]
        total_seeded = 0
        for filename in files:
            file_path = os.path.join(self.data_path, filename)
            if not os.path.exists(file_path):
                print(f"Warning: {file_path} not found.")
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item_data in data:
                    item = Item(**item_data)
                    self.repo.save_item(item)
                    total_seeded += 1
        print(f"Seeded {total_seeded} base items from JSON files.")

    def seed_recipes(self):
        from app.core.domain.recipe import Recipe
        file_path = os.path.join(self.data_path, "recipes.json")
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found.")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for recipe_data in data:
                recipe = Recipe(**recipe_data)
                if not recipe.result_template:
                    result_item = self.repo.get_item_by_name(recipe.result_item_id)
                    if result_item:
                        recipe.result_template = result_item
                self.repo.create_recipe(recipe)
        print(f"Seeded {len(data)} recipes from JSON.")

    def seed_skills(self):
        from app.core.domain.skill import Skill, CharacterClass, SkillType
        file_path = os.path.join(self.data_path, "skills.json")
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found.")
            return

        if not hasattr(self.repo, "save_skill"):
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for s_data in data:
                skill = Skill(
                    id=s_data["id"],
                    name=s_data["name"],
                    description=s_data["description"],
                    character_class=CharacterClass(s_data.get("character_class", "adventurer")),
                    skill_type=SkillType(s_data.get("skill_type", "active")),
                    required_level=s_data.get("required_level", 1),
                    mp_cost=s_data.get("mp_cost", 0),
                    energy_cost=s_data.get("energy_cost", 0),
                    cooldown_turns=s_data.get("cooldown_turns", 0),
                    damage_multiplier=s_data.get("damage_multiplier", 1.0),
                    bonus_damage=s_data.get("bonus_damage", 0),
                    effect_type=s_data.get("effect_type"),
                    effect_duration=s_data.get("effect_duration", 0),
                    effect_value=s_data.get("effect_value", 0)
                )
                self.repo.save_skill(skill)
        print(f"Seeded {len(data)} skills from JSON.")

    # Helpers to get raw config for generators/services
    def get_world_config(self) -> dict:
        return self._load_json("world_config.json")

    def get_loot_tables(self) -> dict:
        return self._load_json("loot_tables.json")

    def get_enemies_config(self) -> dict:
        return self._load_json("enemies.json")

    def get_game_settings(self) -> dict:
        return self._load_json("game_settings.json")

    def _load_json(self, filename: str) -> dict:
        file_path = os.path.join(self.data_path, filename)
        if not os.path.exists(file_path):
            return {}
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
