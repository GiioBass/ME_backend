import json
import logging
import time
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from app.adapters.driving.websocket.connection_manager import manager
from app.core.services.auth_service import auth_service
from app.adapters.driven.persistence.sql_repository import SQLGameRepository

logger = logging.getLogger("multiplayer_ws")
ws_router = APIRouter()
_repo = SQLGameRepository()

@ws_router.get("/ws/status")
def websocket_status():
    return {
        "status": "online",
        "service": "Mystic Explorers Multiplayer WebSocket",
        "protocol": "WebSocket (ws:// o wss://)",
        "active_players": len(manager.active_connections)
    }

@ws_router.websocket("/ws/game")
async def websocket_game_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    player_id: Optional[str] = Query(None)
):
    # 1. Authenticate user
    authenticated_player_id = None
    player_name = "Adventurer"
    
    if token:
        payload = auth_service.decode_token(token)
        if payload:
            authenticated_player_id = payload.get("sub")
            player_name = payload.get("name", "Adventurer")

    if not authenticated_player_id and player_id:
        # Fallback to direct player_id for dev compatibility
        authenticated_player_id = player_id

    if not authenticated_player_id:
        await websocket.accept()
        await websocket.send_text(json.dumps({
            "event": "SYSTEM_EVENT",
            "subtype": "AUTH_FAILED",
            "message": "Authentication failed or token missing/expired"
        }))
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # 2. Fetch Player from database to get current location & class
    player = _repo.get_player(authenticated_player_id)
    if not player and player_id:
        player = _repo.get_player(player_id)

    if player:
        player_name = player.name
        current_location_id = player.current_location_id or "loc_0_0_0"
        character_class = player.stats.character_class if player.stats else "adventurer"
    else:
        current_location_id = "loc_0_0_0"
        character_class = "adventurer"

    # 3. Connect to manager
    await manager.connect(
        websocket=websocket,
        player_id=authenticated_player_id,
        player_name=player_name,
        location_id=current_location_id,
        character_class=character_class
    )

    try:
        while True:
            text_data = await websocket.receive_text()
            if not text_data:
                continue

            try:
                msg = json.loads(text_data)
            except json.JSONDecodeError:
                # Handle raw string ping
                if text_data.strip().lower() == "ping":
                    await websocket.send_text(json.dumps({"event": "PONG", "timestamp": int(time.time())}))
                continue

            msg_type = msg.get("type") or msg.get("event") or ""
            msg_type = msg_type.upper()

            # Heartbeat ping
            if msg_type == "PING":
                await websocket.send_text(json.dumps({"event": "PONG", "timestamp": int(time.time())}))
                continue

            # Party Chat (Party / Group)
            elif msg_type in ["CHAT_PARTY", "PARTY"]:
                chat_text = msg.get("text") or msg.get("message") or ""
                party_id = manager.player_party.get(authenticated_player_id)
                if party_id and chat_text.strip():
                    await manager.broadcast_to_party(
                        party_id,
                        {
                            "event": "CHAT_MESSAGE",
                            "subtype": "PARTY",
                            "sender_id": authenticated_player_id,
                            "sender_name": player_name,
                            "text": chat_text,
                            "message": f"[PARTY] {player_name}: \"{chat_text}\"",
                            "timestamp": int(time.time())
                        }
                    )
                elif not party_id:
                    await manager.send_personal_message(
                        authenticated_player_id,
                        {
                            "event": "SYSTEM_EVENT",
                            "subtype": "PARTY_ERROR",
                            "message": "You are not in a party. Create or join a party to use party chat."
                        }
                    )

            # Global Chat (Shout / All)
            elif msg_type in ["CHAT_SHOUT", "SHOUT", "ALL", "CHAT_ALL"]:
                chat_text = msg.get("text") or msg.get("message") or ""
                if chat_text.strip():
                    await manager.broadcast_global(
                        {
                            "event": "CHAT_MESSAGE",
                            "subtype": "SHOUT",
                            "sender_id": authenticated_player_id,
                            "sender_name": player_name,
                            "text": chat_text,
                            "message": f"[ALL] {player_name}: \"{chat_text}\"",
                            "timestamp": int(time.time())
                        }
                    )

            # Private Whisper
            elif msg_type in ["CHAT_WHISPER", "WHISPER"]:
                target_name = msg.get("target") or msg.get("target_name") or ""
                chat_text = msg.get("text") or msg.get("message") or ""
                if target_name and chat_text.strip():
                    await manager.send_whisper(
                        sender_id=authenticated_player_id,
                        target_name=target_name,
                        text=chat_text
                    )

            # Party Commands
            elif msg_type == "PARTY_CREATE":
                await manager.create_party(authenticated_player_id)

            elif msg_type == "PARTY_INVITE":
                target_name = msg.get("target") or msg.get("target_name") or ""
                if target_name:
                    success, response_msg = await manager.invite_to_party(authenticated_player_id, target_name)
                    await manager.send_personal_message(
                        authenticated_player_id,
                        {
                            "event": "PARTY_EVENT",
                            "subtype": "INVITE_SENT_RESULT",
                            "success": success,
                            "message": response_msg
                        }
                    )

            elif msg_type == "PARTY_ACCEPT":
                success, response_msg = await manager.accept_party_invite(authenticated_player_id)
                await manager.send_personal_message(
                    authenticated_player_id,
                    {
                        "event": "PARTY_EVENT",
                        "subtype": "ACCEPT_RESULT",
                        "success": success,
                        "message": response_msg
                    }
                )

            elif msg_type == "PARTY_DECLINE":
                await manager.decline_party_invite(authenticated_player_id)

            elif msg_type == "PARTY_LEAVE":
                await manager.leave_party(authenticated_player_id)

            elif msg_type == "PARTY_KICK":
                target_id = msg.get("target_id")
                if target_id:
                    await manager.kick_from_party(authenticated_player_id, target_id)

            # Online Players Request
            elif msg_type == "GET_ONLINE_PLAYERS":
                online_players = manager.get_all_online_players()
                await manager.send_personal_message(
                    authenticated_player_id,
                    {
                        "event": "SYSTEM_EVENT",
                        "subtype": "ONLINE_PLAYERS_LIST",
                        "online_players": online_players
                    }
                )

            # Location Update Notification
            elif msg_type in ["LOCATION_UPDATE", "MOVE_SYNC"]:
                new_loc_id = msg.get("location_id")
                if new_loc_id:
                    await manager.update_player_location(authenticated_player_id, new_loc_id)

    except WebSocketDisconnect:
        await manager.disconnect(authenticated_player_id)
    except Exception as e:
        logger.error(f"WebSocket error for player {authenticated_player_id}: {e}")
        await manager.disconnect(authenticated_player_id)
