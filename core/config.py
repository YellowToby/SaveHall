import json
import os
import sys

# Import path detector
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from core.path_detector import get_best_savedata_dir, get_best_savestate_dir
    PATH_DETECTOR_AVAILABLE = True
except ImportError:
    PATH_DETECTOR_AVAILABLE = False
    print("[WARNING] path_detector not available, using defaults")

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".savetranslator_config.json")

def load_config():
    """Load configuration from JSON file"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

def get_ppsspp_path():
    """Get PPSSPP executable path"""
    config = load_config()
    return config.get("ppsspp_path", "")

def set_ppsspp_path(path):
    """Set PPSSPP executable path"""
    config = load_config()
    config["ppsspp_path"] = path
    save_config(config)
    

def get_savedata_dir():
    """
    Get SAVEDATA directory with auto-detection fallback
    Priority:
    1. User-configured path (if set)
    2. Auto-detected path (if available)
    3. Default path
    """
    config = load_config()
    
    # Check if user has manually configured OR previously auto-detected a path
    if "savedata_dir" in config:
        if os.path.exists(config["savedata_dir"]):
            print("Manually configured or Previously auto detected Savedata directory exists")
            # Use cached path (fast!)
            return config["savedata_dir"]
        else:
            print(f"[WARNING] Cached path no longer exists: {config['savedata_dir']}")
     
    # Only run slow detection if no cached path
    print("[INFO] No cached path, running detection (this may take a moment)...")
    if PATH_DETECTOR_AVAILABLE:
        detected = get_best_savedata_dir()
        if detected:
            print(f"[AUTO-DETECT] Using SAVEDATA: {detected}")
            # Save the detected path for future use
            config["savedata_dir"] = detected
            save_config(config)
            return detected
    
    # Fallback to default
    default = os.path.expanduser("~/Documents/PPSSPP/PSP/SAVEDATA")
    print(f"[DEFAULT] Using SAVEDATA: {default}")
    return default

def get_savestate_dir():
    """
    Get SAVESTATE directory with auto-detection fallback
    Priority:
    1. User-configured path (if set)
    2. Auto-detected path (if available)
    3. Default paths (try both common locations)
    """
    config = load_config()
    
    # Check if user has manually configured OR previously auto-detected a path
    if "savestate_dir" in config:
        if os.path.exists(config["savestate_dir"]):
            print("Manually configured or Previously auto detected Savestate directory exists")
            # Use cached path (fast!)
            return config["savestate_dir"]
        else:
            print(f"[WARNING] Cached path no longer exists: {config['savestate_dir']}")
    
    # Only run slow detection if no cached path
    print("[INFO] No cached path, running detection (this may take a moment)...")
    if PATH_DETECTOR_AVAILABLE:
        detected = get_best_savestate_dir()
        if detected:
            print(f"[AUTO-DETECT] Using SAVESTATE: {detected}")
            # Save the detected path for future use
            config["savestate_dir"] = detected
            save_config(config)
            return detected
    
    # Try common default locations
    defaults = [
        os.path.expanduser("~/Documents/PPSSPP/PSP/PPSSPP_STATE"),
        os.path.expanduser("~/Documents/PPSSPP/PSP/SYSTEM/savestates"),
        os.path.expanduser("~/OneDrive/Documents/PPSSPP/PSP/PPSSPP_STATE"),
        os.path.expanduser("~/OneDrive/Documents/PPSSPP/PSP/SYSTEM/savestates"),
    ]
    
    for default in defaults:
        if os.path.exists(default):
            print(f"[DEFAULT] Using SAVESTATE: {default}")
            return default
    
    # If none exist, return first default
    print(f"[DEFAULT] Using SAVESTATE (not found): {defaults[0]}")
    return defaults[0]

def set_savedata_dir(path):
    """Manually set SAVEDATA directory"""
    if not os.path.exists(path):
        raise ValueError(f"Directory does not exist: {path}")
    
    config = load_config()
    config["savedata_dir"] = path
    save_config(config)
    print(f"[CONFIGURED] SAVEDATA directory set to: {path}")

def set_savestate_dir(path):
    """Manually set SAVESTATE directory"""
    if not os.path.exists(path):
        raise ValueError(f"Directory does not exist: {path}")
    
    config = load_config()
    config["savestate_dir"] = path
    save_config(config)
    print(f"[CONFIGURED] SAVESTATE directory set to: {path}")

def get_all_ppsspp_directories():
    """
    Get all detected PPSSPP directories
    Useful for showing user multiple options
    """
    if PATH_DETECTOR_AVAILABLE:
        from core.path_detector import find_ppsspp_directories
        return find_ppsspp_directories()
    return {'savedata_dirs': [], 'savestate_dirs': [], 'ppsspp_roots': []}

def reset_paths():
    """
    Clear configured paths and force re-detection
    """
    config = load_config()
    if "savedata_dir" in config:
        del config["savedata_dir"]
    if "savestate_dir" in config:
        del config["savestate_dir"]
    save_config(config)
    print("[RESET] Paths cleared, will auto-detect on next run")

# Test function
if __name__ == '__main__':
    print("="*60)
    print("Configuration Test")
    print("="*60)
    
    print("\nCurrent Configuration:")
    print(f"PPSSPP Path: {get_ppsspp_path()}")
    print(f"SAVEDATA Dir: {get_savedata_dir()}")
    print(f"SAVESTATE Dir: {get_savestate_dir()}")
    
    print("\nAll detected directories:")
    dirs = get_all_ppsspp_directories()
    print(f"SAVEDATA options: {dirs['savedata_dirs']}")
    print(f"SAVESTATE options: {dirs['savestate_dirs']}")
