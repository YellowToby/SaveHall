
import os
import sys

def find_ppsspp_directories():
    """
    Search for PPSSPP directories in common locations
    Returns dict with found paths
    """
    found_paths = {
        'savedata_dirs': [],
        'savestate_dirs': [],
        'ppsspp_roots': []
    }
    
    # Possible base directories to search
    search_bases = [
        # Local Documents
        os.path.expanduser("~/Documents"),
        
        # OneDrive paths
        os.path.expanduser("~/OneDrive/Documents"),
        os.path.join(os.environ.get('OneDrive', ''), 'Documents') if 'OneDrive' in os.environ else None,
        os.path.join(os.environ.get('OneDriveConsumer', ''), 'Documents') if 'OneDriveConsumer' in os.environ else None,
        
        # Alternative user paths
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"),
        
        # Common installation locations
        "C:/PPSSPP",
        "C:/Program Files/PPSSPP",
        "C:/Program Files (x86)/PPSSPP",
        
        # Portable installations
        "D:/PPSSPP",
        "E:/PPSSPP",
    ]
    
    # Remove None values
    search_bases = [base for base in search_bases if base]
    print("[PPSSPP Detector] Searching for PPSSPP directories...")
    for base in search_bases:
        print(f"[SCAN] Checking: {base}")
        
        # Add timeout check
        import time
        start_time = time.time()
        
        if not os.path.exists(base):
            continue
        
        # If just checking existence took >2 seconds, skip this path
        if time.time() - start_time > 2:
            print(f"[SKIP] {base} is slow (network drive?), skipping...")
            continue
        
        # Continue with normal scanning...
    
    # PPSSPP directory structures to look for
    savedata_patterns = [
        "PPSSPP/PSP/SAVEDATA",
        "PSP/SAVEDATA"
    ]
    
    savestate_patterns = [
        "PPSSPP/PSP/PPSSPP_STATE",
        "PPSSPP/PSP/SYSTEM/savestates",
        "PSP/PPSSPP_STATE",
        "PSP/SYSTEM/savestates"
    ]
    
    print("[PPSSPP Detector] Searching for PPSSPP directories...")
    
    # Search each base directory
    for base in search_bases:
        if not os.path.exists(base):
            continue
        
        # Check for SAVEDATA directories
        for pattern in savedata_patterns:
            full_path = os.path.join(base, pattern)
            if os.path.exists(full_path) and os.path.isdir(full_path):
                if full_path not in found_paths['savedata_dirs']:
                    found_paths['savedata_dirs'].append(full_path)
                    print(f"[✓] Found SAVEDATA: {full_path}")
                    
                    # Store the PPSSPP root
                    ppsspp_root = os.path.dirname(os.path.dirname(full_path))
                    if ppsspp_root not in found_paths['ppsspp_roots']:
                        found_paths['ppsspp_roots'].append(ppsspp_root)
        
        # Check for SAVESTATE directories
        for pattern in savestate_patterns:
            full_path = os.path.join(base, pattern)
            if os.path.exists(full_path) and os.path.isdir(full_path):
                if full_path not in found_paths['savestate_dirs']:
                    found_paths['savestate_dirs'].append(full_path)
                    print(f"[✓] Found SAVESTATE: {full_path}")
    
    return found_paths


def get_best_savedata_dir():
    """
    Find the most likely SAVEDATA directory
    Priority: Directory with most save folders
    """
    paths = find_ppsspp_directories()
    
    if not paths['savedata_dirs']:
        print("[WARNING] No SAVEDATA directories found!")
        return None
    
    # Count save folders in each directory
    best_dir = None
    max_saves = 0
    
    for directory in paths['savedata_dirs']:
        try:
            saves = [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]
            save_count = len(saves)
            print(f"[INFO] {directory} contains {save_count} save folders")
            
            if save_count > max_saves:
                max_saves = save_count
                best_dir = directory
        except Exception as e:
            print(f"[ERROR] Could not scan {directory}: {e}")
    
    if best_dir:
        print(f"[SELECTED] Best SAVEDATA directory: {best_dir} ({max_saves} saves)")
    
    return best_dir


def get_best_savestate_dir():
    """
    Find the most likely SAVESTATE directory
    Priority: Directory with most .ppst files
    """
    paths = find_ppsspp_directories()
    
    if not paths['savestate_dirs']:
        print("[WARNING] No SAVESTATE directories found!")
        return None
    
    # Count .ppst files in each directory
    best_dir = None
    max_states = 0
    
    for directory in paths['savestate_dirs']:
        try:
            states = [f for f in os.listdir(directory) if f.endswith('.ppst')]
            state_count = len(states)
            print(f"[INFO] {directory} contains {state_count} save states")
            
            if state_count > max_states:
                max_states = state_count
                best_dir = directory
        except Exception as e:
            print(f"[ERROR] Could not scan {directory}: {e}")
    
    # If no directory has states, return the first one found
    if not best_dir and paths['savestate_dirs']:
        best_dir = paths['savestate_dirs'][0]
        print(f"[SELECTED] No save states found, using: {best_dir}")
    elif best_dir:
        print(f"[SELECTED] Best SAVESTATE directory: {best_dir} ({max_states} states)")
    
    return best_dir


def get_all_save_files():
    """
    Get all save files from all detected SAVEDATA directories
    Useful for comprehensive scanning
    """
    paths = find_ppsspp_directories()
    all_saves = []
    
    for savedata_dir in paths['savedata_dirs']:
        try:
            for folder in os.listdir(savedata_dir):
                folder_path = os.path.join(savedata_dir, folder)
                if os.path.isdir(folder_path):
                    param_path = os.path.join(folder_path, "PARAM.SFO")
                    if os.path.exists(param_path):
                        all_saves.append({
                            'folder': folder,
                            'path': folder_path,
                            'param_sfo': param_path,
                            'source_dir': savedata_dir
                        })
        except Exception as e:
            print(f"[ERROR] Failed to scan {savedata_dir}: {e}")
    
    return all_saves


def get_all_save_states():
    """
    Get all save states from all detected SAVESTATE directories
    """
    paths = find_ppsspp_directories()
    all_states = []
    
    for savestate_dir in paths['savestate_dirs']:
        try:
            for filename in os.listdir(savestate_dir):
                if filename.endswith('.ppst'):
                    full_path = os.path.join(savestate_dir, filename)
                    all_states.append({
                        'filename': filename,
                        'path': full_path,
                        'modified': os.path.getmtime(full_path),
                        'size': os.path.getsize(full_path),
                        'source_dir': savestate_dir
                    })
        except Exception as e:
            print(f"[ERROR] Failed to scan {savestate_dir}: {e}")
    
    return sorted(all_states, key=lambda x: x['modified'], reverse=True)


# Test function
if __name__ == '__main__':
    print("="*60)
    print("PPSSPP Path Auto-Detection Test")
    print("="*60)
    
    # Find all directories
    paths = find_ppsspp_directories()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"SAVEDATA directories found: {len(paths['savedata_dirs'])}")
    for d in paths['savedata_dirs']:
        print(f"  - {d}")
    
    print(f"\nSAVESTATE directories found: {len(paths['savestate_dirs'])}")
    for d in paths['savestate_dirs']:
        print(f"  - {d}")
    
    print(f"\nPPSSPP roots found: {len(paths['ppsspp_roots'])}")
    for d in paths['ppsspp_roots']:
        print(f"  - {d}")
    
    # Get best directories
    print("\n" + "="*60)
    print("RECOMMENDED DIRECTORIES")
    print("="*60)
    
    best_savedata = get_best_savedata_dir()
    if best_savedata:
        print(f"SAVEDATA: {best_savedata}")
    
    best_savestate = get_best_savestate_dir()
    if best_savestate:
        print(f"SAVESTATE: {best_savestate}")
    
    # Show all saves
    print("\n" + "="*60)
    print("ALL SAVES FOUND")
    print("="*60)
    saves = get_all_save_files()
    print(f"Total save folders: {len(saves)}")
    for save in saves[:5]:  # Show first 5
        print(f"  - {save['folder']} ({save['source_dir']})")
    if len(saves) > 5:
        print(f"  ... and {len(saves) - 5} more")
    
    # Show all states
    print("\n" + "="*60)
    print("ALL SAVE STATES FOUND")
    print("="*60)
    states = get_all_save_states()
    print(f"Total save states: {len(states)}")
    for state in states[:5]:  # Show first 5
        print(f"  - {state['filename']} ({state['source_dir']})")
    if len(states) > 5:
        print(f"  ... and {len(states) - 5} more")


