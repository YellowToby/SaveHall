import json
import os

# Adjust path to where your game_map.json is stored
GAME_MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "game_map.json")
GAME_MAP_PATH = os.path.abspath(GAME_MAP_PATH)

def load_game_map():
    if os.path.exists(GAME_MAP_PATH):
        with open(GAME_MAP_PATH, "r") as f:
            return json.load(f)
    return {}

def get_iso_for_disc_id(disc_id):
    game_map = load_game_map()
    return game_map.get(disc_id)
