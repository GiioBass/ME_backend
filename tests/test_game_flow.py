from fastapi.testclient import TestClient
from app.main import app

def test_full_game_loop():
    import uuid
    test_num = str(uuid.uuid4())[:8]
    test_name = f"Adventurer_{test_num}"
    with TestClient(app) as client:
        # 1. Start Game
        print("\n[TEST] Starting Game...")
        response = client.post(f"/api/v1/start?name={test_name}")
        assert response.status_code == 200
        data = response.json()
        player = data["player"]
        location = data["location"]
    
        assert player["name"] == test_name
        # Expect generated Oakfield Hub at 0,0
        assert "Oakfield Hub" in location["name"]
        print(f" > Player created: {player['name']} at {location['name']}")
        
        player_id = player["id"]

        # 2. Look Command
        print("[TEST] Looking around...")
        resp = client.post("/api/v1/command", json={"player_id": player_id, "command": "look"})
        assert resp.status_code == 200
        assert "Oakfield" in resp.json()["message"]
        print(f" > Look response: {resp.json()['message']}")

        # 3. Stats Command
        print("[TEST] Checking stats...")
        resp = client.post("/api/v1/command", json={"player_id": player_id, "command": "stats"})
        assert resp.status_code == 200
        assert "hp" in resp.json()["message"]
        print(f" > Stats: {resp.json()['message']}")

        # 4. Valid Move (North)
        # Since we generated a 5x5 chunk at 0,0, North (0,1) exists.
        print("[TEST] Trying VALID move (North)...")
        resp = client.post("/api/v1/command", json={"player_id": player_id, "command": "go north"})
        assert resp.status_code == 200
        assert "You travel north..." in resp.json()["message"]
        
        # Verify new location
        new_loc = resp.json()["location"]
        # Can be Forest OR a water source (Lake, River, Stream, Well)
        valid_names = ["Forest", "River", "Stream", "Lake", "Well"]
        assert any(name in new_loc["name"] for name in valid_names)
        print(f" > Moved to: {new_loc['name']}")

        # 5. Invalid Move
        # Let's try going up from 0,1 (no exit).
        print("[TEST] Trying INVALID move (Up)...")
        resp = client.post("/api/v1/command", json={"player_id": player_id, "command": "go up"})
        assert "can't go that way" in resp.json()["message"]

