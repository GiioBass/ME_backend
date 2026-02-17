from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_game_loop():
    # 1. Start Game
    print("\n[TEST] Starting Game...")
    response = client.post("/api/v1/start?name=Adventurer")
    assert response.status_code == 200
    data = response.json()
    player = data["player"]
    location = data["location"]
    
    assert player["name"] == "Adventurer"
    # Expect generated Forest Area at 0,0
    assert "Forest Area 0,0" in location["name"]
    print(f" > Player created: {player['name']} at {location['name']}")
    
    player_id = player["id"]

    # 2. Look Command
    print("[TEST] Looking around...")
    resp = client.post("/api/v1/command", json={"player_id": player_id, "command": "look"})
    assert resp.status_code == 200
    assert "forest" in resp.json()["message"].lower()
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
    assert "Forest Area 0,1" in new_loc["name"]
    print(f" > Moved to: {new_loc['name']}")

    # 5. Invalid Move (West from 0,0 was impossible, but now we are at 0,1)
    # Let's try going West from 0,1. 0,1 Only has North(0,2), South(0,0), East(1,1). West(-1,1) is out of bounds.
    print("[TEST] Trying INVALID move (West)...")
    resp = client.post("/api/v1/command", json={"player_id": player_id, "command": "go west"})
    assert "can't go that way" in resp.json()["message"]

