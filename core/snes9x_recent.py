"""
SNES9x Recent Games Parser
Extract recent games from snes9x.conf file
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional


def find_snes9x_config_paths() -> List[str]:
    """
    Find SNES9x configuration file locations
    
    SNES9x stores config in:
    - Windows: AppData/Roaming/Snes9x/snes9x.conf
    - Linux: ~/.snes9x/snes9x.conf
    - Portable: Same directory as snes9x.exe
    """
    possible_paths = [
        # AppData Roaming (Windows)
        os.path.expanduser("~/AppData/Roaming/Snes9x/snes9x.conf"),
        
        # Documents folder
        os.path.expanduser("~/Documents/Snes9x/snes9x.conf"),
        
        # Linux home directory
        os.path.expanduser("~/.snes9x/snes9x.conf"),
        
        # Portable installations
        "C:/Program Files/Snes9x/snes9x.conf",
        "C:/Program Files (x86)/Snes9x/snes9x.conf",
        "C:/Snes9x/snes9x.conf",
    ]
    
    found_paths = []
    for path in possible_paths:
        if os.path.exists(path):
            found_paths.append(path)
            print(f"[FOUND] {path}")
    
    return found_paths


def parse_snes9x_conf(conf_path: str) -> Dict:
    """
    Parse SNES9x snes9x.conf configuration file
    
    Recent files section looks like:
    [RecentFiles]
    ROM0=C:\Games\SNES\Super Metroid.smc
    ROM1=C:\Games\SNES\Chrono Trigger.sfc
    ...
    
    Returns:
        Dict with recent ROMs and settings
    """
    if not os.path.exists(conf_path):
        print(f"[ERROR] Config not found: {conf_path}")
        return {}
    
    config = {
        'recent_roms': [],
        'rom_directory': None,
        'settings': {}
    }
    
    current_section = None
    
    try:
        with open(conf_path, 'r', encoding='utf-8', errors='ignore') as f:
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
                    
                    # Recent ROM entries (in [RecentFiles] section)
                    if current_section == 'RecentFiles' and key.startswith('ROM'):
                        if value and value != '""':  # Not empty or just quotes
                            # Remove quotes if present
                            value = value.strip('"')
                            if value:
                                config['recent_roms'].append(value)
                    
                    # ROM directory setting
                    elif key == 'ROMDirectory' or key == 'InitialDirectory':
                        value = value.strip('"')
                        if value:
                            config['rom_directory'] = value
                    
                    # Store other settings
                    else:
                        config['settings'][key] = value
    
    except Exception as e:
        print(f"[ERROR] Failed to parse {conf_path}: {e}")
    
    return config


def extract_rom_info(rom_path: str) -> Dict[str, str]:
    """
    Extract ROM information from file path
    
    Args:
        rom_path: Full path to ROM file
        
    Returns:
        Dict with rom_name, directory, etc.
    """
    path = Path(rom_path)
    
    info = {
        'full_path': rom_path,
        'filename': path.name,
        'directory': str(path.parent),
        'extension': path.suffix,
        'rom_name': path.stem,  # Filename without extension
        'exists': os.path.exists(rom_path)
    }
    
    return info


def get_recent_snes_games() -> List[Dict]:
    """
    Get list of recently played SNES games
    
    Returns:
        List of dicts with ROM information
    """
    config_paths = find_snes9x_config_paths()
    
    if not config_paths:
        print("[WARNING] No SNES9x config files found")
        return []
    
    # Use the first found config
    config_path = config_paths[0]
    print(f"\n[USING] {config_path}\n")
    
    config = parse_snes9x_conf(config_path)
    
    recent_games = []
    for rom_path in config['recent_roms']:
        rom_info = extract_rom_info(rom_path)
        recent_games.append(rom_info)
    
    return recent_games


def scan_snes_rom_directory() -> List[str]:
    """
    Scan the SNES ROM directory from config
    
    Returns:
        List of ROM file paths
    """
    config_paths = find_snes9x_config_paths()
    
    if not config_paths:
        return []
    
    config = parse_snes9x_conf(config_paths[0])
    rom_dir = config.get('rom_directory')
    
    if not rom_dir or not os.path.exists(rom_dir):
        return []
    
    rom_files = []
    extensions = ['.smc', '.sfc', '.fig', '.swc', '.zip']
    
    try:
        for file in os.listdir(rom_dir):
            if any(file.lower().endswith(ext) for ext in extensions):
                full_path = os.path.join(rom_dir, file)
                rom_files.append(full_path)
    except Exception as e:
        print(f"[ERROR] Failed to scan {rom_dir}: {e}")
    
    return rom_files


def get_snes9x_recent_for_rom_map():
    """
    Get recent SNES games formatted for SaveNexus ROM mapping
    
    Returns:
        Dict mapping game_name -> rom_path
    """
    recent_games = get_recent_snes_games()
    
    rom_map = {}
    print("\n" + "="*60)
    print("Recent SNES9x Games")
    print("="*60)
    
    for i, game in enumerate(recent_games, 1):
        status = "✓" if game['exists'] else "✗"
        
        print(f"{i}. [{status}] {game['rom_name']}")
        print(f"   Path: {game['full_path']}")
        
        if game['exists']:
            rom_map[game['rom_name']] = game['full_path']
        
        print()
    
    print(f"Total: {len(recent_games)} recent ROMs")
    print(f"Available: {len(rom_map)} ROMs found")
    print("="*60)
    
    return rom_map


def test_snes9x_config():
    """Test function to display SNES9x configuration"""
    print("="*60)
    print("SNES9x Configuration Test")
    print("="*60)
    
    # Find config files
    config_paths = find_snes9x_config_paths()
    
    if not config_paths:
        print("\n❌ No SNES9x configuration found!")
        print("\nExpected locations:")
        print("  • ~/AppData/Roaming/Snes9x/snes9x.conf")
        print("  • ~/.snes9x/snes9x.conf")
        return
    
    # Parse first config
    config = parse_snes9x_conf(config_paths[0])
    
    print(f"\n📁 ROM Directory:")
    print(f"   {config.get('rom_directory', 'Not set')}")
    
    print(f"\n🎮 Recent ROMs ({len(config['recent_roms'])}):")
    for i, rom_path in enumerate(config['recent_roms'], 1):
        exists = "✓" if os.path.exists(rom_path) else "✗"
        rom_name = Path(rom_path).stem
        print(f"   {i}. [{exists}] {rom_name}")
        print(f"      {rom_path}")
    
    # Show ROM directory scan
    print("\n📂 ROMs in Directory:")
    roms = scan_snes_rom_directory()
    if roms:
        for i, rom in enumerate(roms[:10], 1):  # Show first 10
            print(f"   {i}. {Path(rom).name}")
        if len(roms) > 10:
            print(f"   ... and {len(roms) - 10} more")
    else:
        print("   (No ROMs found or directory not set)")
    
    print("\n" + "="*60)


if __name__ == '__main__':
    # Run test
    test_snes9x_config()
    
    # Example: Get ROM map for SaveNexus
    print("\n\n")
    rom_map = get_snes9x_recent_for_rom_map()
    
    # Save to file
    if rom_map:
        import json
        output_path = 'snes_rom_map.json'
        with open(output_path, 'w') as f:
            json.dump(rom_map, f, indent=4)
        print(f"\n💾 Saved to: {output_path}")
