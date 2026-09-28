# Mystic Explorers - Comprehensive Command Reference Protocol

All commands can be entered via the terminal interface or interactive buttons in the HUD. Commands and aliases are case-insensitive.

---

## 1. Movement & Navigation (`movement`)
Navigate through surface terrain, sectors, and multi-layered dungeons.

| Command | Aliases | Usage | Description |
| :--- | :--- | :--- | :--- |
| `north` | `n` | `north` | Move one sector to the north (y+1). |
| `south` | `s` | `south` | Move one sector to the south (y-1). |
| `east` | `e` | `east` | Move one sector to the east (x+1). |
| `west` | `w` | `west` | Move one sector to the west (x-1). |
| `up` | `u`, `climb`, `surface` | `up` | Ascend staircase, climb out of cave, or return to surface layer (z+1). |
| `down` | `d`, `enter`, `dive` | `down` | Descend into cave entrance, dungeon portal, or subterranean level (z-1). |

---

## 2. General & Diagnostics (`general`)
Inspect environment, attributes, time, and maps.

| Command | Aliases | Usage | Description |
| :--- | :--- | :--- | :--- |
| `look` | `l`, `examine` | `look` | Inspect current sector, ground items, hostile enemies, and present adventurers. |
| `stats` | `status` | `stats` | Display HP, Mana, Stamina, Hunger, Thirst, Experience, and Level stats. |
| `inventory` | `i`, `inv` | `inventory` | List all carrying items, weight limits, and equipment inventory slots. |
| `time` | `clock`, `date` | `time` | Check current in-game clock and day/night cycle (regeneration & darkness). |
| `scout` | `map`, `radar` | `scout` | Scan surroundings to discover points of interest, water sources, and dungeons. |
| `help` | - | `help` | Display terminal protocol guide and available commands. |
| `clear` | `cls` | `clear` | Wipe terminal display history. |

---

## 3. World Interaction & Combat (`interaction`)
Interact with items, water sources, NPCs, vendors, and hostiles.

| Command | Aliases | Usage | Description |
| :--- | :--- | :--- | :--- |
| `take` | `get`, `pickup` | `take [item_name]` | Pick up an item from the current sector ground. |
| `drop` | `discard` | `drop [item_name]` | Drop an item from inventory to the ground. |
| `consume` | `use`, `eat`, `drink`| `consume [item_name]` | Consume food or potions to restore health, stamina, hunger, or thirst. |
| `fill` | `refill` | `fill [flask_name]` | Refill water flask from a natural water source (river, lake, oasis, spring). |
| `attack` | `fight`, `hit` | `attack [enemy_name]` | Engage an enemy in turn-based combat. |
| `talk` | `speak`, `greet` | `talk [npc_name]` | Initiate interactive dialogue tree with a sector NPC. |
| `shop` | - | `shop` | View shop goods, prices, and merchant inventory. |
| `buy` | `purchase` | `buy [item_name]` | Purchase an item from a merchant using gold. |
| `sell` | - | `sell [item_name]` | Sell an item from inventory to the merchant for gold. |
| `quests` | `journal`, `quest` | `quests` | View active and completed quest journal entries. |
| `turnin` | `complete` | `turnin [quest_id]` | Complete a quest by delivering required items to the NPC. |

---

## 4. Advanced Systems, Camps & Crafting (`advanced`)
Specialization, tactical abilities, campsite fast travel, and blueprints.

| Command | Aliases | Usage | Description |
| :--- | :--- | :--- | :--- |
| `equip` | - | `equip [item_name]` | Equip weapon or armor into character equipment slots. |
| `unequip` | - | `unequip [slot_name]` | Unequip gear back into inventory. |
| `camp` | `waypoint` | `camp [camp_name]` | Establish a campsite fast-travel waypoint at current location. |
| `travel` | `teleport` | `travel [camp_name]` | Fast travel back to a previously established campsite. |
| `rest` | `sleep`, `wait` | `rest` | Rest at a campsite to fully recover HP and Stamina (advances world clock). |
| `chest` | `storage` | `chest` | Open persistent campsite chest storage. |
| `store` | `stash` | `store [item_name]` | Move item from inventory into campsite storage chest. |
| `retrieve` | `withdraw` | `retrieve [item_name]` | Retrieve item from campsite storage chest. |
| `craft` | `make` | `craft [recipe_name]` | Synthesize items using crafting materials. |
| `recipes` | `blueprints` | `recipes` | List all discovered crafting recipes and ingredient requirements. |
| `class` | `choose_class` | `class [class_name]` | Specialize character class (Warrior, Mage, Rogue, Ranger). |
| `skills` | `abilities`, `spells`| `skills` | List character class tactical abilities, mana costs, and cooldowns. |
| `cast` | `skill` | `cast [skill_name] [target]` | Cast active combat ability or spell against target hostile. |
| `admin` | `god` | `admin [key] [subcommand]` | Game Master overrides (god mode, spawn items/enemies, teleport). |

---

## 5. Multiplayer & Party Communications (`multiplayer`)
Real-time cooperative party management, global comms, and private whispers.

| Command | Aliases | Usage | Description |
| :--- | :--- | :--- | :--- |
| `party` | `p` | `party [invite/accept/leave/kick]` | Create or manage party, invite adventurers, or chat (`/p <msg>`). |
| `whisper` | `w`, `tell`, `pm` | `whisper [player_name] [msg]` | Send a direct, private whisper to another online adventurer. |
| `shout` | `all`, `yell`, `g` | `shout [message]` | Broadcast global message to all connected players across the realm. |

---

### In-Chat Slash Commands
Within the **Neural Comms** chat panel, direct shortcuts are supported:
- `/p <mensaje>` or `/party <mensaje>`: Broadcast to Party Group.
- `/all <mensaje>` or `/shout <mensaje>`: Broadcast to All Realm Players.
- `/w <jugador> <mensaje>`: Private Whisper.
- `/invite <jugador>`: Send Party Invitation.
