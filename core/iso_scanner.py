"""
ISO Scanner for SaveNexus
Automatically detects ISO/CSO files and maps them to disc IDs
"""

import os
import re
import sys
import json
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ppsspp_recent import get_ppsspp_recent_for_game_map
from core.snes9x_recent import get_snes9x_recent_for_rom_map
from core.ppsspp_recent import parse_ppsspp_ini, find_ppsspp_config_paths
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ISOScanner:
    """Scans directories for PSP ISO/CSO files and extracts disc IDs"""
    ppsspp_recent = get_ppsspp_recent_for_game_map()  # Auto-finds ISOs
    snes_recent = get_snes9x_recent_for_rom_map()      # Auto-finds ROMs
    
    COMMON_ISO_LOCATIONS = [
        # Windows common locations
        r"C:\PPSSPP games",
        r"C:\Games\PSP",
        r"D:\Games\PSP",
        r"E:\Games\PSP",
        
        # User directories
        
        os.path.expanduser("~/Games/PSP"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Desktop/PSP Games"),
        os.path.expanduser("~/Documents/PPSSPP/PSP/GAME"),
        
        # OneDrive locations
        os.path.join(os.environ.get('OneDrive', ''), 'Games', 'PSP'),
        os.path.join(os.environ.get('OneDriveConsumer', ''), 'Games', 'PSP'),
    ]
    
    SUPPORTED_EXTENSIONS = ['.iso', '.cso', '.pbp']
    
    def __init__(self, game_map_path: str = None):
        """Initialize scanner with path to game_map.json"""
        if game_map_path is None:
            # Default to project root
            project_root = Path(__file__).parent.parent
            game_map_path = project_root / "game_map.json"
        
        self.game_map_path = Path(game_map_path)
        self.found_isos: Dict[str, str] = {}
        self.disc_id_pattern = re.compile(
             r'(ULUS|ULES|ULJM|ULJS|NPJH|NPUH|NPUG|UCUS|UCES|NPPA|NPEZ|ULKP|ULKS|UCAS|UCJS|NPHG)'
             r'[-_ ]?(\d{5})',
             re.IGNORECASE
         )
    
    def scan_directory(self, directory: str, recursive: bool = True) -> Dict[str, str]:
        path = Path(directory)
        
        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            return {}
        
        found = {}
        
        if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
            # Single file case — process it directly
            disc_id = self.extract_disc_id(path)
            if disc_id:
                normalized = path.absolute().as_posix()
                found[disc_id] = normalized
                logger.info(f"Found single file: {disc_id} → {path.name}")
        
        elif path.is_dir():
            # Directory case — scan as before
            logger.info(f"Scanning directory: {path}")
            pattern = '**/*' if recursive else '*'
            for file_path in path.glob(pattern):
                if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    disc_id = self.extract_disc_id(file_path)
                    if disc_id:
                        normalized = file_path.absolute().as_posix()
                        found[disc_id] = normalized
                        logger.info(f"Found: {disc_id} → {file_path.name}")
        
        else:
            logger.warning(f"Path is neither file nor directory: {path}")
        
        return found
    
    def scan_all_common_locations(self) -> Dict[str, str]:
        """
        Scan all common ISO storage locations
        
        Returns:
            Dict mapping disc_id -> iso_path
        """
        logger.info("Scanning common ISO locations...")
        all_found = {}
        
        for location in self.COMMON_ISO_LOCATIONS:
            location = os.path.expandvars(location)  # Expand env vars
            if os.path.exists(location):
                found = self.scan_directory(location, recursive=True)
                all_found.update(found)
            else:
                logger.debug(f"Skipping non-existent: {location}")
        
        logger.info(f"Total ISOs found: {len(all_found)}")
        return all_found

    def scan_recent_ppsspp_paths(self) -> Dict[str, str]:
        """
        Quick-scan: Automatically scan paths from PPSSPP recent games list.
        Returns dict of newly found disc_id -> path
        """
        from core.ppsspp_recent import parse_ppsspp_ini, find_ppsspp_config_paths
        
        found = {}
        
        config_paths = find_ppsspp_config_paths()
        if not config_paths:
            logger.warning("No PPSSPP config found for quick scan")
            return found
        
        config = parse_ppsspp_ini(config_paths[0])
        recent_paths = config.get('recent_isos', [])
        
        if not recent_paths:
            logger.info("No recent games found in PPSSPP config")
            return found
        
        logger.info(f"Quick-scanning {len(recent_paths)} recent PPSSPP paths...")
        
        for raw_path in recent_paths:
            path = Path(raw_path)
            if not path.exists():
                logger.debug(f"Skipping missing recent path: {raw_path}")
                continue
            
            # Reuse existing scan_directory logic (supports both files and folders)
            if path.is_file():
                # Single file
                disc_id = self.extract_disc_id(path)
                if disc_id:
                    normalized = path.absolute().as_posix()
                    found[disc_id] = normalized
                    logger.info(f"Quick found (file): {disc_id} → {path.name}")
            else:
                # Directory → scan contents
                dir_found = self.scan_directory(str(path), recursive=True)
                found.update(dir_found)
        
        return found

    def extract_disc_id(self, file_path: Path) -> Optional[str]:
        """
        Extract disc ID from ISO/CSO file
        
        Tries multiple methods:
        1. Filename pattern matching
        2. ISO header parsing (for uncompressed ISOs)
        3. Directory name pattern matching
        
        Args:
            file_path: Path to ISO/CSO file
            
        Returns:
            Disc ID (e.g., ULUS10565) or None
        """
        # Method 1: Check filename
        filename_match = self.disc_id_pattern.search(file_path.name)
        if filename_match:
            return filename_match.group(0).upper()
        
        # Method 2: Check parent directory name
        parent_match = self.disc_id_pattern.search(file_path.parent.name)
        if parent_match:
            return parent_match.group(0).upper()
        
        # Method 3: Parse ISO header (only for .iso files, not .cso)
        if file_path.suffix.lower() == '.iso':
            header_id = self._parse_iso_header(file_path)
            if header_id:
                return header_id
        
        logger.warning(f"Could not extract disc ID from: {file_path.name}")
        return None
        path = Path(file_path)
        return self.extract_disc_id(path)


    
    def _parse_iso_header(self, iso_path: Path) -> Optional[str]:
        """
        Parse PSP ISO header to extract disc ID
        
        PSP ISO structure:
        - Sector 0x8000 (offset 0x8000 * 2048): UMD_DATA.BIN
        - Contains disc ID at specific offset
        
        Args:
            iso_path: Path to ISO file
            
        Returns:
            Disc ID or None
        """
        try:
            with open(iso_path, 'rb') as f:
                # Seek to UMD data area
                # Disc ID is usually at offset 0x8373 in many PSP ISOs
                f.seek(0x8373)
                disc_id_bytes = f.read(10)
                
                # Try to decode as ASCII
                disc_id = disc_id_bytes.decode('ascii', errors='ignore').strip()
                
                # Validate format
                if self.disc_id_pattern.match(disc_id):
                    return disc_id.upper()
                
                # Alternative: try different offset
                f.seek(0x0000)
                first_kb = f.read(1024)
                match = self.disc_id_pattern.search(first_kb.decode('ascii', errors='ignore'))
                if match:
                    return match.group(0).upper()
                    
        except Exception as e:
            logger.debug(f"Could not parse ISO header for {iso_path.name}: {e}")
        
        return None
    
    def load_existing_game_map(self) -> Dict[str, str]:
        """Load existing game_map.json"""
        if self.game_map_path.exists():
            try:
                with open(self.game_map_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Invalid game_map.json, starting fresh")
                return {}
        return {}
    
    def save_game_map(self, game_map: Dict[str, str], backup: bool = True):
        """
        Save game map to game_map.json
        
        Args:
            game_map: Dict mapping disc_id -> iso_path
            backup: Whether to create backup of existing file
        """
        # Create backup if requested
        if backup and self.game_map_path.exists():
            backup_path = self.game_map_path.with_suffix('.json.backup')
            import shutil
            shutil.copy2(self.game_map_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
        
        # Save new game map
        with open(self.game_map_path, 'w', encoding='utf-8') as f:
            json.dump(game_map, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Game map saved: {len(game_map)} entries")
    
    def merge_with_existing(self, new_entries: Dict[str, str]) -> Dict[str, str]:
        """
        Merge newly found ISOs with existing game_map.json
        
        Args:
            new_entries: New disc_id -> iso_path mappings
            
        Returns:
            Merged game map
        """
        existing = self.load_existing_game_map()
        
        # Track changes
        added = []
        updated = []
        
        for disc_id, iso_path in new_entries.items():
            if disc_id not in existing:
                added.append(disc_id)
            elif existing[disc_id] != iso_path:
                updated.append(disc_id)
            
            existing[disc_id] = iso_path
        
        logger.info(f"Merge complete: {len(added)} added, {len(updated)} updated")
        
        if added:
            logger.info(f"New games: {', '.join(added)}")
        if updated:
            logger.info(f"Updated paths: {', '.join(updated)}")
        
        return existing
    
    def scan_and_update(self, custom_paths: List[str] = None) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Full scan and update workflow
        
        Args:
            custom_paths: Additional paths to scan beyond common locations
            
        Returns:
            Tuple of (all_game_map, newly_found)
        """
        # Scan common locations
        found = self.scan_all_common_locations()
        
        # Scan custom paths if provided
        if custom_paths:
            for path in custom_paths:
                custom_found = self.scan_directory(path, recursive=True)
                found.update(custom_found)
        
        # Merge with existing
        merged = self.merge_with_existing(found)
        
        # Save to file
        self.save_game_map(merged)
        
        return merged, found


def interactive_scan():
    """Interactive CLI for scanning ISOs"""
    print("="*60)
    print("SaveNexus ISO Scanner")
    print("="*60)
    
    scanner = ISOScanner()
    
    print("\nOptions:")
    print("1. Scan common locations")
    print("2. Scan custom directory")
    print("3. Full scan (common + custom)")
    print("4. View current game map")
    print("5. Quick scan recent PPSSPP games")  
    print("0. Exit")
    
    choice = input("\nSelect option (0-5): ").strip()
        
    if choice == "0":
        print("Exiting scanner.")
    
    if choice == "1":
        found = scanner.scan_all_common_locations()
        merged = scanner.merge_with_existing(found)
        scanner.save_game_map(merged)
        print(f"\n✓ Found {len(found)} ISOs, game map now has {len(merged)} entries")
    
    elif choice == "2":
        path = input("Enter directory path: ").strip()
        found = scanner.scan_directory(path, recursive=True)
        merged = scanner.merge_with_existing(found)
        scanner.save_game_map(merged)
        print(f"\n✓ Found {len(found)} ISOs, game map now has {len(merged)} entries")
    
    elif choice == "3":
        custom_paths = []
        while True:
            path = input("Enter custom directory (or press Enter to finish): ").strip()
            if not path:
                break
            custom_paths.append(path)
        
        merged, found = scanner.scan_and_update(custom_paths)
        print(f"\n✓ Found {len(found)} new ISOs, game map now has {len(merged)} entries")
    
    elif choice == "4":
        game_map = scanner.load_existing_game_map()
        print(f"\nCurrent game map ({len(game_map)} entries):")
        for disc_id, path in game_map.items():
            print(f"  {disc_id}: {path}")

    elif choice == "5":
        # New quick scan from recent PPSSPP paths
        recent_found = scanner.scan_recent_ppsspp_paths()
        if recent_found:
            merged = scanner.merge_with_existing(recent_found)
            scanner.save_game_map(merged)
            print(f"\n✓ Quick scan added/updated {len(recent_found)} entries")
            print(f"   Game map now has {len(merged)} total entries")
        else:
            print("\nNo new valid recent games could be mapped.")

    else:
        print("Invalid choice")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    interactive_scan()
