from pydantic import BaseModel

class WorldTime(BaseModel):
    total_ticks: int = 0
    
    @property
    def day(self) -> int:
        # 1 day = 24 * 60 = 1440 minutes
        return (self.total_ticks // 1440) + 1
    
    @property
    def hour(self) -> int:
        return (self.total_ticks % 1440) // 60
    
    @property
    def minute(self) -> int:
        return self.total_ticks % 60
    
    def advance(self, minutes: int):
        self.total_ticks += minutes
        
    def get_time_string(self) -> str:
        return f"Day {self.day}, {self.hour:02d}:{self.minute:02d}"
    
    def is_night(self) -> bool:
        # Night from 20:00 (8 PM) to 06:00 (6 AM)
        return self.hour >= 20 or self.hour < 6
