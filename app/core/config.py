from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///database.db"
    SECRET_KEY: str = "mystic_explorers_secure_jwt_secret_key_change_in_production_2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080 # 7 days
    
    # --- Game Mechanics ---
    # Time Costs (minutes)
    TIME_COST_MOVE: int = 10
    TIME_COST_TAKE: int = 1
    TIME_COST_DROP: int = 1
    TIME_COST_ATTACK: int = 2
    TIME_COST_SCOUT: int = 2
    TIME_COST_CRAFT: int = 10
    TIME_COST_FILL: int = 2
    TIME_COST_DRINK: int = 1
    TIME_COST_TRAVEL_BASE: int = 10 # Multiplied by distance
    
    # Survival Mechanics
    HUNGER_DRAIN_INTERVAL: int = 10 # Minutes per 1 hunger loss
    THIRST_DRAIN_INTERVAL: int = 8  # Minutes per 1 thirst loss
    STARVATION_DAMAGE_INTERVAL: int = 10
    DEHYDRATION_DAMAGE_INTERVAL: int = 8
    NATURAL_HEAL_INTERVAL: int = 10 # Heal 1 HP per interval if healthy
    
    # Resting
    REST_DURATION_MINS: int = 480  # 8 hours
    REST_HEAL_FULL: bool = True     # If True, resting restores full HP
    REST_HUNGER_COST: int = 15
    REST_THIRST_COST: int = 15
    REST_BASE_HEAL: int = 20        # Only used if REST_HEAL_FULL is False
    
    # Combat & Hazards
    ENEMY_ATTACK_CHANCE_MOVE_DUNGEON: float = 0.5
    ENEMY_ATTACK_CHANCE_MOVE_WILDERNESS: float = 0.3
    ENEMY_ATTACK_CHANCE_INTERACTION: float = 0.4 # take, drop, equip, consume, etc.
    SCOUT_RADIUS: int = 5
    TRAVEL_ENERGY_COST_MULT: int = 2 # HP loss per distance unit
    
    # Environment
    HOUR_DAWN: int = 6
    HOUR_NIGHT: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
