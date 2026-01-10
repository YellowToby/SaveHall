"""
Enhanced PPSSPP Launcher with Save State Support
Replaces core/launcher.py
"""

import subprocess
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
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
        with open("launch.log", "a") as log:
            log.write(f"[DEBUG] Launching with args: {args}\n")
        
        subprocess.Popen(args, shell=False)
        
        with open("launch.log", "a") as log:
            log.write("[DEBUG] Launched successfully.\n")
            
    except Exception as e:
        error_msg = f"Failed to launch PPSSPP: {e}"
        with open("launch.log", "a") as log:
            log.write(f"[ERROR] {error_msg}\n")
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
