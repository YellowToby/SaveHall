"""
Enhanced ISO Scanner for SaveHall
Automatically detects ISO/CSO files and maps them to disc IDs with improved directory handling
"""

import os
import re
import json
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ISOScanner:
    """Enhanced scanner for PSP ISO/CSO files with smart directory detection"""
    
    # Common ISO storage locations (priority ordered)
    COMMON_ISO_LOCATIONS = [
        # Recent PPSSPP paths (highest priority)
        'ppsspp_recent',
        
        # Primary drives
        r"C:\PPSSPP games",
        r"C:\Games\PSP",
        r"D:\Games\PSP",
        r"D:\Kurt",  # From your game_map.json
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
    
    # PSP disc ID patterns
    DISC_ID_PATTERN = re.compile(
        r'(ULUS|ULES|ULJM|ULJS|NPJH|NPUH|NPUG|UCUS|UCES|NPPA|NPEZ|ULKP|ULKS|UCAS|UCJS|NPHG)'
        r'[-_ ]?(\d{5})',
        re.IGNORECASE
    )
    
    def __init__(self, game_map_path: str = None):
        """Initialize scanner with path to game_map.json"""
        if game_map_path is None:
            project_root = Path(__file__).parent.parent
            game_map_path = project_root / "game_map.json"
        
        self.game_map_path = Path(game_map_path)
        self.found_isos: Dict[str, str] = {}
        self.scan_history: List[str] = []
    
    def get_ppsspp_recent_paths(self) -> List[str]:
        """Get paths from PPSSPP recent games list"""
        try:
            from core.ppsspp_recent import get_ppsspp_recent_for_game_map
            recent_map = get_ppsspp_recent_for_game_map()
            
            # Extract unique directory paths
            paths = set()
            for iso_path in recent_map.values():
                paths.add(str(Path(iso_path).parent))
            
            logger.info(f"Found {len(paths)} directories from PPSSPP recent")
            return list(paths)
        except ImportError:
            logger.warning("Could not import ppsspp_recent")
            return []
    
    def scan_directory(self, directory: str, recursive: bool = True) -> Dict[str, str]:
        """
        Scan directory for ISO/CSO files
        
        Args:
            directory: Directory path or file path
            recursive: Scan subdirectories
            
        Returns:
            Dict mapping disc_id -> iso_path
        """
        path = Path(directory)
        
        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            return {}
        
        found = {}
        
        # Handle single file
        if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
            disc_id = self.extract_disc_id(path)
            if disc_id:
                normalized = path.absolute().as_posix()
                found[disc_id] = normalized
                logger.info(f"Found: {disc_id} → {path.name}")
        
        # Handle directory
        elif path.is_dir():
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
        logger.info("Starting comprehensive scan...")
        all_found = {}
        
        # First, check PPSSPP recent games
        if 'ppsspp_recent' in self.COMMON_ISO_LOCATIONS:
            recent_paths = self.get_ppsspp_recent_paths()
            for path in recent_paths:
                if os.path.exists(path):
                    found = self.scan_directory(path, recursive=True)
                    all_found.update(found)
        
        # Then scan common locations
        for location in self.COMMON_ISO_LOCATIONS:
            if location == 'ppsspp_recent':
                continue
                
            location = os.path.expandvars(location)
            if os.path.exists(location):
                found = self.scan_directory(location, recursive=True)
                all_found.update(found)
            else:
                logger.debug(f"Skipping non-existent: {location}")
        
        logger.info(f"Scan complete: {len(all_found)} ISOs found")
        return all_found
    
    def extract_disc_id(self, file_path: Path) -> Optional[str]:
        """
        Extract disc ID from ISO/CSO file
        
        Methods (priority order):
        1. Filename pattern matching
        2. Parent directory name matching
        3. ISO header parsing (for .iso files only)
        
        Args:
            file_path: Path to ISO/CSO file
            
        Returns:
            Disc ID (e.g., ULUS10565) or None
        """
        # Method 1: Check filename
        filename_match = self.DISC_ID_PATTERN.search(file_path.name)
        if filename_match:
            disc_id = f"{filename_match.group(1).upper()}{filename_match.group(2)}"
            return disc_id.replace('-', '').replace('_', '')
        
        # Method 2: Check parent directory name
        parent_match = self.DISC_ID_PATTERN.search(file_path.parent.name)
        if parent_match:
            disc_id = f"{parent_match.group(1).upper()}{parent_match.group(2)}"
            return disc_id.replace('-', '').replace('_', '')
        
        # Method 3: Parse ISO header (only for .iso files)
        if file_path.suffix.lower() == '.iso':
            header_id = self._parse_iso_header(file_path)
            if header_id:
                return header_id
        
        logger.warning(f"Could not extract disc ID from: {file_path.name}")
        return None
    
    def _parse_iso_header(self, iso_path: Path) -> Optional[str]:
        """
        Parse PSP ISO header to extract disc ID
        
        PSP ISO structure:
        - Disc ID typically at offset 0x8373
        - Also check first 1KB for embedded disc ID
        
        Args:
            iso_path: Path to ISO file
            
        Returns:
            Disc ID or None
        """
        try:
            with open(iso_path, 'rb') as f:
                # Try standard offset
                f.seek(0x8373)
                disc_id_bytes = f.read(10)
                
                disc_id = disc_id_bytes.decode('ascii', errors='ignore').strip()
                if self.DISC_ID_PATTERN.match(disc_id):
                    return disc_id.upper().replace('-', '').replace('_', '')
                
                # Try first KB
                f.seek(0x0000)
                first_kb = f.read(1024)
                match = self.DISC_ID_PATTERN.search(
                    first_kb.decode('ascii', errors='ignore')
                )
                if match:
                    disc_id = f"{match.group(1).upper()}{match.group(2)}"
                    return disc_id.replace('-', '').replace('_', '')
                    
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
        # Create backup
        if backup and self.game_map_path.exists():
            backup_path = self.game_map_path.with_suffix('.json.backup')
            import shutil
            shutil.copy2(self.game_map_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
        
        # Save new game map
        self.game_map_path.parent.mkdir(parents=True, exist_ok=True)
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
        
        added = []
        updated = []
        
        for disc_id, iso_path in new_entries.items():
            if disc_id not in existing:
                added.append(disc_id)
            elif existing[disc_id] != iso_path:
                updated.append(disc_id)
            
            existing[disc_id] = iso_path
        
        if added:
            logger.info(f"Added {len(added)} new games: {', '.join(added[:5])}")
        if updated:
            logger.info(f"Updated {len(updated)} paths: {', '.join(updated[:5])}")
        
        return existing
    
    def verify_paths(self) -> Tuple[List[str], List[str]]:
        """
        Verify all paths in game_map.json still exist
        
        Returns:
            Tuple of (valid_disc_ids, missing_disc_ids)
        """
        game_map = self.load_existing_game_map()
        valid = []
        missing = []
        
        for disc_id, iso_path in game_map.items():
            if os.path.exists(iso_path):
                valid.append(disc_id)
            else:
                missing.append(disc_id)
        
        logger.info(f"Verification: {len(valid)} valid, {len(missing)} missing")
        return valid, missing
    
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
        
        # Scan custom paths
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
    print("=" * 60)
    print("SaveHall ISO Scanner")
    print("=" * 60)
    
    scanner = ISOScanner()
    
    print("\nOptions:")
    print("1. Quick scan (PPSSPP recent + common locations)")
    print("2. Scan custom directory")
    print("3. Full scan with custom paths")
    print("4. View current game map")
    print("5. Verify existing paths")
    print("0. Exit")
    
    choice = input("\nSelect option (0-5): ").strip()
    
    if choice == "0":
        print("Exiting scanner.")
        return
    
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
        for disc_id, path in sorted(game_map.items()):
            exists = "✓" if os.path.exists(path) else "✗"
            print(f"  [{exists}] {disc_id}: {path}")
    
    elif choice == "5":
        valid, missing = scanner.verify_paths()
        print(f"\n✓ Valid: {len(valid)}")
        print(f"✗ Missing: {len(missing)}")
        
        if missing:
            print("\nMissing ISOs:")
            game_map = scanner.load_existing_game_map()
            for disc_id in missing[:10]:
                print(f"  ✗ {disc_id}: {game_map[disc_id]}")
            if len(missing) > 10:
                print(f"  ... and {len(missing) - 10} more")
    
    else:
        print("Invalid choice")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    interactive_scan()
