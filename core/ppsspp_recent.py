"""
PPSSPP Recent Games Parser
Extract recent games from PPSSPP's ppsspp.ini config file
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional


def find_ppsspp_config_paths() -> List[str]:
    """
    Find PPSSPP configuration file locations
    
    PPSSPP stores config in:
    - Windows: Documents/PPSSPP/memstick/PSP/SYSTEM/ppsspp.ini
    - Windows (alt): AppData/Roaming/ppsspp.org/ppsspp.ini
    - Portable: Same directory as PPSSPP.exe
    """
    possible_paths = [
        # Standard Documents location
        os.path.expanduser("~/Documents/PPSSPP/memstick/PSP/SYSTEM/ppsspp.ini"),
        
        # OneDrive Documents
        os.path.expanduser("~/OneDrive/Documents/PPSSPP/memstick/PSP/SYSTEM/ppsspp.ini"),
        
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


def parse_ppsspp_ini(ini_path: str) -> Dict:
    """
    Parse PPSSPP ppsspp.ini configuration file
    
    Returns:
        Dict with recent games and settings
    """
    if not os.path.exists(ini_path):
        print(f"[ERROR] Config not found: {ini_path}")
        return {}
    
    config = {
        'recent_isos': [],
        'current_directory': None,
        'game_settings': {}
    }
    
    current_section = None
    
    try:
        with open(ini_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                
                # Section headers [SectionName]
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    continue
                
                # Key = Value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Recent ISO entries
                    if key.startswith('RecentIso'):
                        if value:  # Not empty
                            config['recent_isos'].append(value)
                    
                    # Current directory
                    elif key == 'CurrentDirectory':
                        config['current_directory'] = value
                    
                    # Other useful settings
                    elif current_section == 'General':
                        config['game_settings'][key] = value
    
    except Exception as e:
        print(f"[ERROR] Failed to parse {ini_path}: {e}")
    
    return config


def extract_game_info_from_path(iso_path: str) -> Dict[str, str]:
    """
    Extract game information from ISO path
    
    Args:
        iso_path: Full path to ISO file
        
    Returns:
        Dict with game_name, disc_id, directory
    """
    path = Path(iso_path)
    
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
            game_info = extract_game_info_from_path(iso_path)
            game_info['exists'] = True
            recent_games.append(game_info)
        else:
            # Track missing ISOs
            game_info = extract_game_info_from_path(iso_path)
            game_info['exists'] = False
            recent_games.append(game_info)
    
    return recent_games


def auto_populate_game_map_from_recent() -> Dict[str, str]:
    """
    Automatically create game_map.json entries from recent games
    
    Returns:
        Dict suitable for game_map.json
    """
    recent_games = get_recent_games()
    
    game_map = {}
    
    for game in recent_games:
        if game.get('disc_id') and game.get('exists'):
            game_map[game['disc_id']] = game['full_path']
    
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
        output_path = 'game_map_from_ppsspp.json'
        with open(output_path, 'w') as f:
            json.dump(game_map, f, indent=4)
        print(f"\n💾 Saved to: {output_path}")
