import asyncio
import json
import logging
import time
from typing import Dict, Set, Optional, List, Any, Tuple
from fastapi import WebSocket

logger = logging.getLogger("multiplayer")

class ConnectionManager:
    def __init__(self):
        # player_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # player_id -> location_id
        self.player_locations: Dict[str, str] = {}
        # player_id -> player_name
        self.player_names: Dict[str, str] = {}
        # player_id -> character_class
        self.player_classes: Dict[str, str] = {}
        # location_id -> Set of player_id
        self.room_members: Dict[str, Set[str]] = {}
        
        # Party Management:
        # party_id -> { "id": party_id, "leader_id": leader_id, "members": [player_id, ...] }
        self.parties: Dict[str, Dict[str, Any]] = {}
        # player_id -> party_id
        self.player_party: Dict[str, str] = {}
        # target_player_id -> { "from_player_id": str, "from_player_name": str, "party_id": str, "timestamp": float }
        self.party_invites: Dict[str, Dict[str, Any]] = {}

        # asyncio locks for rooms to ensure concurrency safety
        self._room_locks: Dict[str, asyncio.Lock] = {}

    def get_room_lock(self, location_id: str) -> asyncio.Lock:
        if location_id not in self._room_locks:
            self._room_locks[location_id] = asyncio.Lock()
        return self._room_locks[location_id]

    async def connect(
        self, 
        websocket: WebSocket, 
        player_id: str, 
        player_name: str, 
        location_id: str, 
        character_class: str = "adventurer"
    ):
        await websocket.accept()
        self.active_connections[player_id] = websocket
        self.player_names[player_id] = player_name
        self.player_locations[player_id] = location_id
        self.player_classes[player_id] = character_class

        if location_id not in self.room_members:
            self.room_members[location_id] = set()
        self.room_members[location_id].add(player_id)

        logger.info(f"Player {player_name} ({player_id}) connected in room {location_id}")

        # 1. Notify others in the room
        await self.broadcast_to_room(
            location_id,
            {
                "event": "ROOM_EVENT",
                "subtype": "PLAYER_JOINED_ROOM",
                "player_id": player_id,
                "player_name": player_name,
                "character_class": character_class,
                "message": f"{player_name} has entered the area."
            },
            exclude_player_id=player_id
        )

        # 2. Check if player belongs to an existing party
        party_info = None
        party_id = self.player_party.get(player_id)
        if party_id and party_id in self.parties:
            party_info = self.get_party_details(party_id)
            # Notify party members that player is back online
            await self.broadcast_party_sync(party_id)

        # 3. Send initial connected state to the connecting player
        room_players = self.get_room_players(location_id)
        online_players = self.get_all_online_players()
        await self.send_personal_message(
            player_id,
            {
                "event": "SYSTEM_EVENT",
                "subtype": "CONNECTED_SUCCESS",
                "player_id": player_id,
                "location_id": location_id,
                "present_players": room_players,
                "online_players": online_players,
                "party": party_info,
                "message": f"Connected to Mystic Explorers multiplayer network. {len(online_players)} player(s) online."
            }
        )

    async def disconnect(self, player_id: str):
        player_name = self.player_names.get(player_id, "Unknown")
        old_location_id = self.player_locations.get(player_id)
        party_id = self.player_party.get(player_id)

        if player_id in self.active_connections:
            del self.active_connections[player_id]

        if old_location_id and old_location_id in self.room_members:
            self.room_members[old_location_id].discard(player_id)
            if not self.room_members[old_location_id]:
                del self.room_members[old_location_id]
            
            # Notify old room members
            await self.broadcast_to_room(
                old_location_id,
                {
                    "event": "ROOM_EVENT",
                    "subtype": "PLAYER_LEFT_ROOM",
                    "player_id": player_id,
                    "player_name": player_name,
                    "message": f"{player_name} has left the area (disconnected)."
                }
            )

        if party_id and party_id in self.parties:
            await self.broadcast_party_sync(party_id)

        logger.info(f"Player {player_name} ({player_id}) disconnected.")

    async def update_player_location(self, player_id: str, new_location_id: str):
        old_location_id = self.player_locations.get(player_id)
        if old_location_id == new_location_id:
            return

        player_name = self.player_names.get(player_id, "Adventurer")
        player_class = self.player_classes.get(player_id, "adventurer")

        # Leave old room
        if old_location_id and old_location_id in self.room_members:
            self.room_members[old_location_id].discard(player_id)
            if not self.room_members[old_location_id]:
                del self.room_members[old_location_id]

            await self.broadcast_to_room(
                old_location_id,
                {
                    "event": "ROOM_EVENT",
                    "subtype": "PLAYER_LEFT_ROOM",
                    "player_id": player_id,
                    "player_name": player_name,
                    "message": f"{player_name} moved to another area."
                }
            )

        # Enter new room
        self.player_locations[player_id] = new_location_id
        if new_location_id not in self.room_members:
            self.room_members[new_location_id] = set()
        self.room_members[new_location_id].add(player_id)

        # Notify new room
        await self.broadcast_to_room(
            new_location_id,
            {
                "event": "ROOM_EVENT",
                "subtype": "PLAYER_JOINED_ROOM",
                "player_id": player_id,
                "player_name": player_name,
                "character_class": player_class,
                "message": f"{player_name} has arrived."
            },
            exclude_player_id=player_id
        )

        # Send updated presence list to the moving player
        room_players = self.get_room_players(new_location_id)
        await self.send_personal_message(
            player_id,
            {
                "event": "ROOM_EVENT",
                "subtype": "PRESENCE_SYNC",
                "location_id": new_location_id,
                "present_players": room_players
            }
        )

        # Sync location with Party if in one
        party_id = self.player_party.get(player_id)
        if party_id and party_id in self.parties:
            await self.broadcast_party_sync(party_id)

    def get_room_players(self, location_id: str) -> List[Dict[str, Any]]:
        members = self.room_members.get(location_id, set())
        result = []
        for pid in members:
            result.append({
                "id": pid,
                "name": self.player_names.get(pid, "Unknown"),
                "character_class": self.player_classes.get(pid, "adventurer")
            })
        return result

    def get_all_online_players(self) -> List[Dict[str, Any]]:
        result = []
        for pid in list(self.active_connections.keys()):
            result.append({
                "id": pid,
                "name": self.player_names.get(pid, "Adventurer"),
                "character_class": self.player_classes.get(pid, "adventurer"),
                "location_id": self.player_locations.get(pid, "loc_0_0_0"),
                "party_id": self.player_party.get(pid)
            })
        return result

    async def send_personal_message(self, player_id: str, message: dict):
        websocket = self.active_connections.get(player_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send personal message to {player_id}: {e}")

    async def broadcast_to_room(self, location_id: str, message: dict, exclude_player_id: Optional[str] = None):
        members = list(self.room_members.get(location_id, set()))
        dead_connections = []
        for pid in members:
            if exclude_player_id and pid == exclude_player_id:
                continue
            ws = self.active_connections.get(pid)
            if ws:
                try:
                    await ws.send_text(json.dumps(message))
                except Exception:
                    dead_connections.append(pid)
        for dead_id in dead_connections:
            await self.disconnect(dead_id)

    async def broadcast_global(self, message: dict, exclude_player_id: Optional[str] = None):
        dead_connections = []
        for pid, ws in list(self.active_connections.items()):
            if exclude_player_id and pid == exclude_player_id:
                continue
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead_connections.append(pid)
        for dead_id in dead_connections:
            await self.disconnect(dead_id)

    # -------------------------------------------------------------
    # Party / Group Management
    # -------------------------------------------------------------
    def get_party_details(self, party_id: str) -> Optional[Dict[str, Any]]:
        party = self.parties.get(party_id)
        if not party:
            return None
        members_info = []
        for pid in party["members"]:
            members_info.append({
                "id": pid,
                "name": self.player_names.get(pid, "Adventurer"),
                "character_class": self.player_classes.get(pid, "adventurer"),
                "location_id": self.player_locations.get(pid, "Unknown"),
                "is_leader": (pid == party["leader_id"]),
                "is_online": (pid in self.active_connections)
            })
        return {
            "id": party["id"],
            "leader_id": party["leader_id"],
            "members": members_info
        }

    async def broadcast_to_party(self, party_id: str, message: dict, exclude_player_id: Optional[str] = None):
        party = self.parties.get(party_id)
        if not party:
            return
        for pid in party["members"]:
            if exclude_player_id and pid == exclude_player_id:
                continue
            ws = self.active_connections.get(pid)
            if ws:
                try:
                    await ws.send_text(json.dumps(message))
                except Exception:
                    pass

    async def broadcast_party_sync(self, party_id: str):
        party_info = self.get_party_details(party_id)
        if not party_info:
            return
        await self.broadcast_to_party(
            party_id,
            {
                "event": "PARTY_EVENT",
                "subtype": "PARTY_UPDATE",
                "party": party_info
            }
        )

    async def create_party(self, player_id: str) -> Dict[str, Any]:
        existing_party_id = self.player_party.get(player_id)
        if existing_party_id and existing_party_id in self.parties:
            return self.get_party_details(existing_party_id)

        party_id = f"party_{player_id[:8]}_{int(time.time())}"
        self.parties[party_id] = {
            "id": party_id,
            "leader_id": player_id,
            "members": [player_id]
        }
        self.player_party[player_id] = party_id

        party_info = self.get_party_details(party_id)
        await self.send_personal_message(
            player_id,
            {
                "event": "PARTY_EVENT",
                "subtype": "PARTY_CREATED",
                "party": party_info,
                "message": "You created a new party!"
            }
        )
        return party_info

    async def invite_to_party(self, inviter_id: str, target_name: str) -> Tuple[bool, str]:
        inviter_name = self.player_names.get(inviter_id, "Adventurer")

        # Find target
        target_id = None
        for pid, name in self.player_names.items():
            if name.lower() == target_name.lower():
                target_id = pid
                break

        if not target_id or target_id not in self.active_connections:
            return False, f"Player '{target_name}' is not currently online."

        if target_id == inviter_id:
            return False, "You cannot invite yourself to a party."

        # Ensure inviter has a party
        party_id = self.player_party.get(inviter_id)
        if not party_id or party_id not in self.parties:
            created = await self.create_party(inviter_id)
            party_id = created["id"]

        party = self.parties.get(party_id)
        if party and party["leader_id"] != inviter_id:
            return False, "Only the party leader can invite new members."

        if len(party.get("members", [])) >= 6:
            return False, "Party is full (maximum 6 members)."

        if target_id in party.get("members", []):
            return False, f"Player '{target_name}' is already in your party."

        target_party = self.player_party.get(target_id)
        if target_party and target_party in self.parties:
            return False, f"Player '{target_name}' is already in another party."

        # Save invite
        self.party_invites[target_id] = {
            "from_player_id": inviter_id,
            "from_player_name": inviter_name,
            "party_id": party_id,
            "timestamp": time.time()
        }

        # Send invite notification to target
        await self.send_personal_message(
            target_id,
            {
                "event": "PARTY_EVENT",
                "subtype": "INVITE_RECEIVED",
                "from_player_id": inviter_id,
                "from_player_name": inviter_name,
                "party_id": party_id,
                "message": f"{inviter_name} invited you to join their party!"
            }
        )

        return True, f"Party invitation sent to {target_name}."

    async def accept_party_invite(self, player_id: str) -> Tuple[bool, str]:
        invite = self.party_invites.pop(player_id, None)
        if not invite:
            return False, "No pending party invitation found."

        party_id = invite["party_id"]
        party = self.parties.get(party_id)
        if not party:
            return False, "The party no longer exists."

        if len(party["members"]) >= 6:
            return False, "The party is full."

        # If player was in an old party, leave it first
        old_party_id = self.player_party.get(player_id)
        if old_party_id:
            await self.leave_party(player_id)

        player_name = self.player_names.get(player_id, "Adventurer")
        party["members"].append(player_id)
        self.player_party[player_id] = party_id

        # Sync party to all members
        await self.broadcast_party_sync(party_id)

        # Broadcast welcome message in party chat
        await self.broadcast_to_party(
            party_id,
            {
                "event": "CHAT_MESSAGE",
                "subtype": "PARTY",
                "sender_id": player_id,
                "sender_name": "PARTY",
                "text": f"{player_name} joined the party!",
                "timestamp": int(time.time())
            }
        )
        return True, f"Joined party successfully!"

    async def decline_party_invite(self, player_id: str) -> Tuple[bool, str]:
        invite = self.party_invites.pop(player_id, None)
        if not invite:
            return False, "No pending party invitation found."

        from_id = invite.get("from_player_id")
        player_name = self.player_names.get(player_id, "Adventurer")
        if from_id:
            await self.send_personal_message(
                from_id,
                {
                    "event": "PARTY_EVENT",
                    "subtype": "INVITE_DECLINED",
                    "message": f"{player_name} declined your party invitation."
                }
            )
        return True, "Party invitation declined."

    async def leave_party(self, player_id: str) -> Tuple[bool, str]:
        party_id = self.player_party.pop(player_id, None)
        if not party_id or party_id not in self.parties:
            return False, "You are not currently in a party."

        party = self.parties.get(party_id)
        player_name = self.player_names.get(player_id, "Adventurer")

        if party:
            if player_id in party["members"]:
                party["members"].remove(player_id)
            
            if not party["members"]:
                del self.parties[party_id]
            else:
                # Reassign leader if leader left
                if party["leader_id"] == player_id:
                    party["leader_id"] = party["members"][0]
                
                await self.broadcast_party_sync(party_id)
                await self.broadcast_to_party(
                    party_id,
                    {
                        "event": "CHAT_MESSAGE",
                        "subtype": "PARTY",
                        "sender_id": player_id,
                        "sender_name": "PARTY",
                        "text": f"{player_name} left the party.",
                        "timestamp": int(time.time())
                    }
                )

        await self.send_personal_message(
            player_id,
            {
                "event": "PARTY_EVENT",
                "subtype": "PARTY_LEFT",
                "message": "You left the party."
            }
        )
        return True, "You have left the party."

    async def kick_from_party(self, leader_id: str, target_id: str) -> Tuple[bool, str]:
        party_id = self.player_party.get(leader_id)
        if not party_id or party_id not in self.parties:
            return False, "You are not in a party."

        party = self.parties.get(party_id)
        if party["leader_id"] != leader_id:
            return False, "Only the party leader can kick members."

        if target_id not in party["members"]:
            return False, "Player is not in your party."

        if target_id == leader_id:
            return False, "You cannot kick yourself from the party."

        self.player_party.pop(target_id, None)
        party["members"].remove(target_id)
        target_name = self.player_names.get(target_id, "Player")

        await self.broadcast_party_sync(party_id)
        await self.send_personal_message(
            target_id,
            {
                "event": "PARTY_EVENT",
                "subtype": "PARTY_LEFT",
                "message": "You were removed from the party."
            }
        )
        await self.broadcast_to_party(
            party_id,
            {
                "event": "CHAT_MESSAGE",
                "subtype": "PARTY",
                "sender_id": leader_id,
                "sender_name": "PARTY",
                "text": f"{target_name} was removed from the party.",
                "timestamp": int(time.time())
            }
        )
        return True, f"{target_name} removed from party."

    # -------------------------------------------------------------
    # Whisper and Direct Comms
    # -------------------------------------------------------------
    async def send_whisper(self, sender_id: str, target_name: str, text: str) -> bool:
        sender_name = self.player_names.get(sender_id, "Adventurer")
        # Find target player_id by name (case-insensitive)
        target_id = None
        for pid, name in self.player_names.items():
            if name.lower() == target_name.lower():
                target_id = pid
                break

        if not target_id:
            await self.send_personal_message(
                sender_id,
                {
                    "event": "CHAT_MESSAGE",
                    "subtype": "WHISPER_FAILED",
                    "message": f"Player '{target_name}' is not currently online."
                }
            )
            return False

        # Send to target
        await self.send_personal_message(
            target_id,
            {
                "event": "CHAT_MESSAGE",
                "subtype": "WHISPER_RECEIVED",
                "sender_id": sender_id,
                "sender_name": sender_name,
                "text": text,
                "message": f"[Whisper from {sender_name}]: {text}"
            }
        )

        # Echo back to sender
        await self.send_personal_message(
            sender_id,
            {
                "event": "CHAT_MESSAGE",
                "subtype": "WHISPER_SENT",
                "target_name": self.player_names.get(target_id, target_name),
                "text": text,
                "message": f"[Whisper to {self.player_names.get(target_id, target_name)}]: {text}"
            }
        )
        return True

    def broadcast_sync(self, coro):
        """Helper to run async broadcast from synchronous route handlers"""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.create_task(coro)
        except RuntimeError:
            pass

manager = ConnectionManager()
