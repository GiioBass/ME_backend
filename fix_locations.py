from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from app.core.domain.item import ItemType
import sqlite3
import json

# Fix locations directly in SQLite
conn = sqlite3.connect("game.db")
c = conn.cursor()

c.execute("SELECT id, items, camp_storage FROM locations")
rows = c.fetchall()

fixed_count = 0
for row in rows:
    loc_id, items_json, camp_json = row
    items = json.loads(items_json) if items_json else []
    camp_items = json.loads(camp_json) if camp_json else []
    
    changed = False
    
    for item in items:
        if item.get("name") in ["Mushroom", "Berry"] and item.get("item_type") != "consumable":
            item["item_type"] = "consumable"
            if item.get("name") == "Mushroom":
                item["restore_hunger"] = 10
                item["restore_hp"] = -2
            elif item.get("name") == "Berry":
                item["restore_hunger"] = 5
                item["restore_hp"] = 2
            changed = True
            
    for item in camp_items:
        if item.get("name") in ["Mushroom", "Berry"] and item.get("item_type") != "consumable":
            item["item_type"] = "consumable"
            if item.get("name") == "Mushroom":
                item["restore_hunger"] = 10
                item["restore_hp"] = -2
            elif item.get("name") == "Berry":
                item["restore_hunger"] = 5
                item["restore_hp"] = 2
            changed = True
            
    if changed:
        c.execute("UPDATE locations SET items = ?, camp_storage = ? WHERE id = ?", (json.dumps(items), json.dumps(camp_items), loc_id))
        fixed_count += 1

conn.commit()
conn.close()
print(f"Fixed items in {fixed_count} locations in the DB.")
