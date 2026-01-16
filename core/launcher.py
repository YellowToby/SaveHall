"""
Enhanced PPSSPP Launcher with Save State Support
"""

import subprocess
import os
import struct
import sys
#from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

"""
PSP
"""

from core.config import get_ppsspp_path

def launch_ppsspp(iso_path, save_state=None):
    """
    Launch PPSSPP with optional save state loading
    
    Args:
        iso_path: Path to the game ISO/CSO file
        save_state: Optional path to .ppst save state file
    
    Raises:
        FileNotFoundError: If PPSSPP executable or ISO doesn't exist
        RuntimeError: If launch fails
    """
    exe_path = get_ppsspp_path()

    # Logging for debugging
    with open("launch.log", "a") as log:
        log.write(f"\n[DEBUG] === New Launch Request ===\n")
        log.write(f"[DEBUG] Executable: {exe_path}\n")
        log.write(f"[DEBUG] ISO: {iso_path}\n")
        log.write(f"[DEBUG] Save State: {save_state}\n")

    # Validate executable
    if not exe_path or not os.path.exists(exe_path):
        error_msg = "PPSSPP executable path not set or does not exist."
        with open("launch.log", "a") as log:
            log.write(f"[ERROR] {error_msg}\n")
        raise FileNotFoundError(error_msg)

    # Validate ISO
    if not iso_path or not os.path.exists(iso_path):
        error_msg = "Game ISO path is invalid or does not exist."
        with open("launch.log", "a") as log:
            log.write(f"[ERROR] {error_msg}\n")
        raise FileNotFoundError(error_msg)

    # Build command line arguments
    args = [exe_path, iso_path]
    
    # Add save state loading if specified
    if save_state and os.path.exists(save_state):
        # PPSSPP command line: --state=<path>
        args.append(f"--state={save_state}")
        with open("launch.log", "a") as log:
            log.write(f"[DEBUG] Loading save state: {save_state}\n")
    elif save_state:
        with open("launch.log", "a") as log:
            log.write(f"[WARNING] Save state not found: {save_state}\n")

    # Launch PPSSPP
    try:
        #process = subprocess.Popen(args, shell=False)
        #time.sleep(2)  # Give PPSSPP time to start
        with open("launch.log", "a") as log:
            log.write(f"[DEBUG] Launching with args: {args}\n")
        
        subprocess.Popen(args, shell=False)
        
        with open("launch.log", "a") as log:
            log.write("[DEBUG] Launched successfully.\n")
            
    except Exception as e:
        error_msg = f"Failed to launch PPSSPP: {e}"
        with open("launch.log", "a") as log:
            #log.write(f"[ERROR] {datetime.now()}: {e}\n")
            log.write(f"[ERROR] {error_msg}\n")
            log.write(f"[CONTEXT] ISO: {iso_path}\n")
            log.write(f"[CONTEXT] State: {save_state}\n")
        raise RuntimeError(error_msg)


def get_save_states_for_game(disc_id):
    """
    Find all save states for a specific game
    
    Args:
        disc_id: Game disc ID (e.g., ULUS10565)
    
    Returns:
        List of save state file paths
    """
    from core.config import get_savestate_dir
    
    savestate_dir = get_savestate_dir()
    save_states = []
    
    if not os.path.exists(savestate_dir):
        print(f"[WARNING] Save state directory not found: {savestate_dir}")
        return save_states
    
    print(f"[DEBUG] Scanning for save states in: {savestate_dir}")
    
    # PPSSPP names save states: DISCID_slot.ppst
    # Examples: ULUS10565_1.ppst, ULUS10565_2.ppst
    for filename in os.listdir(savestate_dir):
        if filename.startswith(disc_id) and filename.endswith('.ppst'):
            full_path = os.path.join(savestate_dir, filename)
            save_states.append({
                'filename': filename,
                'path': full_path,
                'modified': os.path.getmtime(full_path),
                'size': os.path.getsize(full_path)
            })
            print(f"[DEBUG] Found save state: {filename}")
    
    # Sort by modification time (newest first)
    return sorted(save_states, key=lambda x: x['modified'], reverse=True)


def create_save_state_after_save(disc_id, slot=0):
    """
    Utility function to create a save state immediately after in-game save
    This would be called by a file watcher monitoring SAVEDATA changes
    
    Args:
        disc_id: Game disc ID
        slot: Save state slot number (0-9)
    
    Note: This requires PPSSPP to be running and the game to be loaded
    PPSSPP doesn't have direct API for this, so this is a placeholder
    for future implementation using hotkey simulation or similar
    """
    # TODO: Implement this via:
    # 1. Monitor PSP/SAVEDATA for changes
    # 2. When PARAM.SFO modified time changes, trigger save state
    # 3. Use keyboard automation to send F2 (default save state hotkey)
    pass


# Example usage and testing
if __name__ == "__main__":
    # Test basic launch
    print("Testing PPSSPP Launcher")
    
    # Test getting save states
    test_disc_id = "ULUS10565"
    states = get_save_states_for_game(test_disc_id)
    print(f"\nFound {len(states)} save states for {test_disc_id}:")
    for state in states:
        from datetime import datetime
        mod_time = datetime.fromtimestamp(state['modified'])
        print(f"  - {state['filename']} ({mod_time})")

"""
SNES
"""

def parse_snes9x_save(save_path):
    """
    Parse SNES9x .srm save file to extract game info
    
    SNES save files are typically just raw SRAM dumps without metadata,
    so we'll need to infer game info from filename and file size
    """
    try:
        filename = os.path.basename(save_path)
        game_name = os.path.splitext(filename)[0]
        
        # Get file size to determine save type
        file_size = os.path.getsize(save_path)
        
        # Common SNES save sizes
        save_types = {
            2048: "2KB SRAM",
            8192: "8KB SRAM", 
            32768: "32KB SRAM",
            65536: "64KB SRAM",
            131072: "128KB SRAM"
        }
        
        save_type = save_types.get(file_size, f"{file_size} bytes")
        
        return {
            'game_name': game_name,
            'save_type': save_type,
            'file_size': file_size,
            'valid': True
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to parse SNES save {save_path}: {e}")
        return None


def find_snes9x_saves():
    """
    Find SNES9x save files in common locations
    
    Common SNES9x save locations:
    - Documents/Snes9x/Saves
    - Snes9x installation directory
    - OneDrive/Documents/Snes9x/Saves
    """
    possible_paths = [
        os.path.expanduser("~/Documents/Snes9x/Saves"),
        os.path.expanduser("~/OneDrive/Documents/Snes9x/Saves"),
        "C:/Program Files/Snes9x",
        "C:/Program Files (x86)/Snes9x",
        os.path.expanduser("~/AppData/Roaming/Snes9x"),
    ]
    
    found_saves = []
    
    for base_path in possible_paths:
        if not os.path.exists(base_path):
            continue
            
        print(f"[SNES9X] Scanning: {base_path}")
        
        try:
            for file in os.listdir(base_path):
                if file.endswith('.srm') or file.endswith('.sav'):
                    full_path = os.path.join(base_path, file)
                    save_info = parse_snes9x_save(full_path)
                    
                    if save_info:
                        save_info['path'] = full_path
                        save_info['folder'] = base_path
                        found_saves.append(save_info)
                        
        except Exception as e:
            print(f"[ERROR] Failed to scan {base_path}: {e}")
    
    return found_saves


def get_snes9x_save_states(game_name, save_folder):
    """
    Find SNES9x save states (.000, .001, etc.)
    
    SNES9x save states are named: game.000, game.001, etc.
    """
    save_states = []
    
    if not os.path.exists(save_folder):
        return save_states
    
    # Look for numbered save states
    for i in range(10):  # SNES9x typically has 10 slots (0-9)
        state_file = os.path.join(save_folder, f"{game_name}.{i:03d}")
        if os.path.exists(state_file):
            save_states.append({
                'filename': f"{game_name}.{i:03d}",
                'path': state_file,
                'slot': i,
                'modified': os.path.getmtime(state_file),
                'size': os.path.getsize(state_file)
            })
    
    return sorted(save_states, key=lambda x: x['modified'], reverse=True)


# Test function
if __name__ == '__main__':
    print("="*60)
    print("SNES9x Save Detection Test")
    print("="*60)
    
    saves = find_snes9x_saves()
    print(f"\nFound {len(saves)} SNES saves:")
    
    for save in saves:
        print(f"\n  Game: {save['game_name']}")
        print(f"  Type: {save['save_type']}")
        print(f"  Path: {save['path']}")
        
        # Check for save states
        states = get_snes9x_save_states(save['game_name'], save['folder'])
        if states:
            print(f"  Save States: {len(states)} found")
            for state in states[:3]:
                print(f"    - Slot {state['slot']}: {state['filename']}")
