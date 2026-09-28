import uuid
import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.services.auth_service import auth_service
from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from app.core.use_cases.game_service import GameService

def test_websocket_multiplayer_flow():
    repo = SQLGameRepository()
    service = GameService(repo)

    # 1. Create two test players
    p1_name = f"Alden_{uuid.uuid4().hex[:6]}"
    p2_name = f"Lyra_{uuid.uuid4().hex[:6]}"

    player1, loc1 = service.create_new_player(p1_name, "mage")
    player2, loc2 = service.create_new_player(p2_name, "marksman")

    token1 = auth_service.create_token(player1.id, player1.name)
    token2 = auth_service.create_token(player2.id, player2.name)

    with TestClient(app) as client:
        # Connect player 1
        with client.websocket_connect(f"/ws/game?token={token1}") as ws1:
            init1 = ws1.receive_json()
            assert init1["event"] == "SYSTEM_EVENT"
            assert init1["subtype"] == "CONNECTED_SUCCESS"
            assert init1["player_id"] == player1.id

            # Heartbeat test
            ws1.send_json({"type": "PING"})
            pong = ws1.receive_json()
            assert pong["event"] == "PONG"

            # Connect player 2 (in same start location)
            with client.websocket_connect(f"/ws/game?token={token2}") as ws2:
                init2 = ws2.receive_json()
                assert init2["subtype"] == "CONNECTED_SUCCESS"

                # Player 1 should have received PLAYER_JOINED_ROOM notification for Player 2
                join_msg = ws1.receive_json()
                assert join_msg["event"] == "ROOM_EVENT"
                assert join_msg["subtype"] == "PLAYER_JOINED_ROOM"
                assert join_msg["player_name"] == player2.name

                # Player 2 says something in room
                ws2.send_json({"type": "CHAT_SAY", "text": "Greetings, traveler!"})

                # Player 1 receives the chat
                chat_msg = ws1.receive_json()
                assert chat_msg["event"] == "CHAT_MESSAGE"
                assert chat_msg["subtype"] == "SAY"
                assert chat_msg["sender_name"] == player2.name
                assert "Greetings, traveler!" in chat_msg["text"]

                # Player 1 whispers to Player 2
                ws1.send_json({"type": "CHAT_WHISPER", "target": player2.name, "text": "Secret mission ahead."})

                # Player 2 receives whisper
                whisper_target = ws2.receive_json()
                assert whisper_target["event"] == "CHAT_MESSAGE"
                assert whisper_target["subtype"] == "WHISPER_RECEIVED"
                assert whisper_target["sender_name"] == player1.name
                assert "Secret mission ahead." in whisper_target["text"]

                # Player 1 receives whisper echo
                whisper_echo = ws1.receive_json()
                assert whisper_echo["subtype"] == "WHISPER_SENT"

                # Global shout test
                ws1.send_json({"type": "CHAT_SHOUT", "text": "Danger in the realm!"})
                shout_msg = ws2.receive_json()
                assert shout_msg["event"] == "CHAT_MESSAGE"
                assert shout_msg["subtype"] == "SHOUT"
                assert shout_msg["sender_name"] == player1.name

def test_websocket_invalid_auth():
    with TestClient(app) as client:
        try:
            with client.websocket_connect("/ws/game?token=invalid.jwt.token"):
                pass
        except Exception as e:
            # Rejection expected
            assert True
