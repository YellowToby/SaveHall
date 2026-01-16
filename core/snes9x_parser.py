"""
SNES9x Emulator Integration
Create as: core/snes9x_parser.py
"""

import os
import struct

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
