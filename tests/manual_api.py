import requests

res = requests.post("http://localhost:8000/api/v1/action/look", json={"player_id": "ScoxAleera", "command": "look"}).json()
actions = res.get("available_actions", [])
print(f"AVAILABLE ACTIONS from API: {actions}")

