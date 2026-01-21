"""
PPSSPP Recent Games Parser
Extract recent games from PPSSPP's ppsspp.ini config file
"""

import os
import re
import struct
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


#import iso_scanner


def find_ppsspp_config_paths() -> List[str]:
    """
    Find PPSSPP configuration file locations
    
    PPSSPP stores config in:
    - Windows: Documents/PPSSPP/memstick/PSP/SYSTEM/ppsspp.ini
    - Windows: Documents/PPSSPP/PSP/SYSTEM/ppsspp.ini
    - Windows (alt): AppData/Roaming/ppsspp.org/ppsspp.ini
    - Portable: Same directory as PPSSPP.exe
    """
    possible_paths = [
        # Standard Documents location
        os.path.expanduser("~/Documents/PPSSPP/memstick/PSP/SYSTEM/ppsspp.ini"),
        os.path.expanduser("~/Documents/PPSSPP/PSP/SYSTEM/ppsspp.ini"),
        
        # OneDrive Documents
        os.path.expanduser("~/OneDrive/Documents/PPSSPP/memstick/PSP/SYSTEM/ppsspp.ini"),
        os.path.expanduser("~/OneDrive/Documents/PPSSPP/PSP/SYSTEM/ppsspp.ini"),
        
        # AppData Roaming
        os.path.expanduser("~/AppData/Roaming/ppsspp.org/ppsspp.ini"),
        
        # Program Files (portable mode)
        "C:/Program Files/PPSSPP/memstick/PSP/SYSTEM/ppsspp.ini",
        "C:/Program Files (x86)/PPSSPP/memstick/PSP/SYSTEM/ppsspp.ini",
    ]
    
    found_paths = []
    for path in possible_paths:
        if os.path.exists(path):
            found_paths.append(path)
            print(f"[FOUND] {path}")
    
    return found_paths


from typing import Dict, List
import os

def parse_ppsspp_ini(ini_path: str) -> Dict[str, any]:
    """
    Parse PPSSPP's ppsspp.ini file.
    
    Focuses on extracting:
    - Recent game paths (FileName0=, FileName1=, ... under [Recent])
    - CurrentDirectory (if present)
    
    Returns:
        {
            'recent_isos': List[str],         # full paths from recent entries
            'current_directory': str | None   # CurrentDirectory value or None
        }
    """
    if not os.path.exists(ini_path):
        print(f"[ERROR] Config not found: {ini_path}")
        return {'recent_isos': [], 'current_directory': None}

    recent_isos: List[str] = []
    current_directory: str | None = None

    in_recent_section = False

    try:
        with open(ini_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()

                # Skip blank lines and comments
                if not line or line.startswith(('#', ';')):
                    continue

                # Section start/end detection
                if line.startswith('[') and line.endswith(']'):
                    section_name = line[1:-1].strip()
                    in_recent_section = (section_name == 'Recent')
                    continue

                # Only process key=value lines inside [Recent] or for CurrentDirectory
                if '=' not in line:
                    continue

                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                if in_recent_section:
                    if key.startswith('FileName') and value:
                        recent_isos.append(value)

                # Optional: capture CurrentDirectory (can appear outside [Recent])
                elif key == 'CurrentDirectory' and value:
                    current_directory = value

    except Exception as e:
        print(f"[ERROR] Failed to parse {ini_path}: {e}")
        return {'recent_isos': [], 'current_directory': None}

    return {
        'recent_isos': recent_isos,
        'current_directory': current_directory,
    }

def extract_disc_id_from_iso(iso_path: Path) -> str | None:
    """Very basic: tries to find DISC_ID from PARAM.SFO in ISO"""
    try:
        with open(iso_path, 'rb') as f:
            # PSP ISOs start with data at sector 16 (offset 0x8000 sectors * 2048 bytes)
            f.seek(16 * 2048)  # UMD_DATA.BIN area
            data = f.read(1024 * 1024)  # read ~1MB, should be enough

            # Look for PARAM.SFO signature "PSF" + version
            pos = data.find(b'PSF\x00')
            if pos == -1:
                return None

            f.seek(16 * 2048 + pos)
            # Skip header (read real offsets)
            header = f.read(20)
            if len(header) < 20:
                return None

            key_table_start, = struct.unpack('<I', header[8:12])
            data_table_start, = struct.unpack('<I', header[12:16])

            # Now read keys (simplified - look for "DISC_ID" key)
            f.seek(16 * 2048 + pos + key_table_start)
            keys_data = f.read(4096)  # enough for keys

            disc_id_pos = keys_data.find(b'DISC_ID\x00')
            if disc_id_pos == -1:
                return None

            # Value offset is after keys, but this is approximate
            # Better full parser exists, but for quick: search nearby for ULUSxxxx etc.
            nearby = keys_data[max(0, disc_id_pos-200):disc_id_pos+200].decode('ascii', errors='ignore')
            import re
            match = re.search(r'(ULUS|ULES|NPJH|NPUH|NPUG|UCUS|UCES|NPPA|NPEZ|ULJM|ULJS)[-_]?[0-9]{5}', nearby, re.I)
            if match:
                raw = match.group(0).upper().replace('-', '')
                return raw

    except Exception:
        pass
    return None

def extract_game_info_from_path(iso_path: str) -> Dict[str, str]:
    """
    Extract game information from ISO path
    
    Args:
        iso_path: Full path to ISO file
        
    Returns:
        Dict with game_name, disc_id, directory
    """
    normalized = iso_path.replace('\\', '/').strip()
    path = Path(normalized)
    
    info = {
        'full_path': iso_path,
        'filename': path.name,
        'directory': str(path.parent),
        'extension': path.suffix,
        'game_name': path.stem,  # Filename without extension
        'disc_id': None
    }
    
    # Try to extract disc ID from filename
    # Common patterns: [ULUS10565], ULUS10565, (ULUS10565)
    disc_id_pattern = re.compile(r'[\[\(]?(ULUS|ULES|NPJH|NPUH|NPUG|UCUS|UCES|NPPA|NPEZ|ULJM|ULJS)[\s\-_]?(\d{5})[\]\)]?', re.IGNORECASE)
    match = disc_id_pattern.search(path.name)
    
    if match:
        info['disc_id'] = f"{match.group(1).upper()}{match.group(2)}"
    
    return info

    if file_path.suffix.lower() in ['.iso', '.cso']:
        disc_id = extract_disc_id_from_iso(file_path)
        if disc_id:
            info['disc_id'] = disc_id
            # no need for filename fallback!

def get_recent_games() -> List[Dict]:
    """
    Get list of recently played games from PPSSPP
    
    Returns:
        List of dicts with game information
    """
    config_paths = find_ppsspp_config_paths()
    
    if not config_paths:
        print("[WARNING] No PPSSPP config files found")
        return []
    
    # Use the first found config
    config_path = config_paths[0]
    print(f"\n[USING] {config_path}\n")
    
    config = parse_ppsspp_ini(config_path)
    
    recent_games = []
    for iso_path in config['recent_isos']:
        if os.path.exists(iso_path):
            exists = os.path.exists(iso_path)
            game_info = extract_game_info_from_path(iso_path)
            game_info['exists'] = True
            game_info['exists'] = exists
            recent_games.append(game_info)
        else:
            # Track missing ISOs
            game_info = extract_game_info_from_path(iso_path)
            game_info['exists'] = False
            recent_games.append(game_info)
    
    return recent_games


"""def auto_populate_game_map_from_recent() -> Dict[str, str]:

    recent_games = get_recent_games()
    
    game_map = {}
    
    for game in recent_games:
        if game.get('disc_id') and game.get('exists'):
            normalized_path = game['full_path'].replace('\\', '/')
            game_map[game['disc_id']] = normalized_path
    
    return game_map
"""

def auto_populate_game_map_from_recent() -> Dict[str, str]:
    from iso_scanner import ISOScanner
    from pathlib import Path
         
    recent_games = get_recent_games()  # your existing function
    
    scanner = ISOScanner()  # creates with default game_map.json path
    
    game_map = {}
    
    for game in recent_games:
        if not game['exists']:
            continue
            
        full_path_str = game['full_path']
        full_path = Path(full_path_str)  # convert once
        
        # Reuse scanner's disc ID extraction (filename + parent + header if .iso)
        disc_id = scanner.extract_disc_id(full_path)
        
        if disc_id:
            #normalized_path = full_path.replace('\\', '/')
            normalized_path = full_path.as_posix()
            game_map[disc_id] = normalized_path
            #game_map[disc_id] = game['full_path'] #normalized
            print(f"  Mapped recent: {disc_id} → {normalized_path}")
        else:
            print(f"  Could not get disc ID for recent: {game['filename']}")
    
    return game_map

def scan_directory_for_isos(directory: str) -> List[str]:
    """
    Scan a directory for ISO/CSO files
    Useful for scanning the current_directory from PPSSPP config
    
    Args:
        directory: Path to directory
        
    Returns:
        List of ISO/CSO file paths
    """
    iso_files = []
    extensions = ['.iso', '.cso', '.pbp']
    
    if not os.path.exists(directory):
        return iso_files
    
    try:
        for file in os.listdir(directory):
            if any(file.lower().endswith(ext) for ext in extensions):
                full_path = os.path.join(directory, file)
                iso_files.append(full_path)
    except Exception as e:
        print(f"[ERROR] Failed to scan {directory}: {e}")
    
    return iso_files


# ===== Integration with SaveNexus =====

def get_ppsspp_recent_for_game_map():
    """
    Get recent games formatted for SaveNexus game_map.json
    
    This can be called from your ISO scanner to auto-populate
    """
    recent_games = get_recent_games()
    
    game_map = {}
    print("\n" + "="*60)
    print("Recent PPSSPP Games")
    print("="*60)
    
    for i, game in enumerate(recent_games, 1):
        status = "✓" if game['exists'] else "✗"
        disc_id = game.get('disc_id', 'Unknown')
        
        print(f"{i}. [{status}] {game['game_name']}")
        print(f"   Disc ID: {disc_id}")
        print(f"   Path: {game['full_path']}")
        
        if game['exists'] and disc_id != 'Unknown':
            game_map[disc_id] = game['full_path']
        
        print()
    
    print(f"Total: {len(recent_games)} recent games")
    print(f"Mappable: {len(game_map)} games with disc IDs")
    print("="*60)
    
    return game_map


# ===== Test & Utility Functions =====

def test_ppsspp_config():
    """Test function to display PPSSPP configuration"""
    print("="*60)
    print("PPSSPP Configuration Test")
    print("="*60)
    
    # Find config files
    config_paths = find_ppsspp_config_paths()
    
    if not config_paths:
        print("\n❌ No PPSSPP configuration found!")
        print("\nExpected locations:")
        print("  • ~/Documents/PPSSPP/memstick/PSP/SYSTEM/ppsspp.ini")
        print("  • ~/Documents/PPSSPP/PSP/SYSTEM/ppsspp.ini")
        print("  • ~/AppData/Roaming/ppsspp.org/ppsspp.ini")
        return
    
    # Parse first config
    config = parse_ppsspp_ini(config_paths[0])
    
    print(f"\n📁 Current Directory:")
    print(f"   {config.get('current_directory', 'Not set')}")
    
    print(f"\n🎮 Recent Games ({len(config['recent_isos'])}):")
    for i, iso_path in enumerate(config['recent_isos'], 1):
        exists = "✓" if os.path.exists(iso_path) else "✗"
        game_name = Path(iso_path).stem
        print(f"   {i}. [{exists}] {game_name}")
        print(f"      {iso_path}")
    
    # Show auto-generated game map
    print("\n📋 Auto-Generated Game Map:")
    game_map = auto_populate_game_map_from_recent()
    
    if game_map:
        import json
        print(json.dumps(game_map, indent=2))
    else:
        print("   (No games with detectable disc IDs)")
    
    print("\n" + "="*60)


if __name__ == '__main__':
    # Run test
    test_ppsspp_config()
    
    # Example: Get game map for SaveNexus
    print("\n\n")
    game_map = get_ppsspp_recent_for_game_map()
    
    # Save to file
    if game_map:
        import json
        
        # Load existing game_map.json
        existing_map = {}
        if os.path.exists('game_map.json'):
            with open('game_map.json', 'r') as f:
                existing_map = json.load(f)
        
        # Merge (new entries won't overwrite existing ones)
        merged_map = {**game_map, **existing_map}
        
        clean_map = {k: v.replace('\\', '/') for k, v in merged_map.items()}
        with open('game_map.json', 'w') as f:
            json.dump(merged_map, f, indent=4)
        
        print(f"\n💾 Merged {len(game_map)} new entries into game_map.json")
