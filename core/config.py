
import json
import os

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".savetranslator_config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

def get_ppsspp_path():
    config = load_config()
    return config.get("ppsspp_path", "")

def set_ppsspp_path(path):
    config = load_config()
    config["ppsspp_path"] = path
    save_config(config)
