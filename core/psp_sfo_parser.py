import re
from pathlib import Path
import struct

# Expand this over time — add entries when you recognize/play a game
GAME_ID_TO_NAME = {
    # Example: "ULUS10536": "God of War - Chains of Olympus"
    # Keep adding...
}

def parse_param_sfo(folder_name: str) -> str:
    # Find the main TITLE_ID pattern (e.g. ULUS12345, NPJH99999, etc.)
    match = re.search(r"([A-Z]{4}\d{5})(.*)", folder_name.upper())
    if match:
        game_id = match.group(1)
        suffix = match.group(2).strip()  # e.g. "GameData00", "SaveData00", "SYSDATA"
        
        base_name = GAME_ID_TO_NAME.get(game_id, f"{game_id} (unknown)")
        
        if suffix:
            if "SYSDATA" in suffix.upper():
                return f"{base_name} [System/Data]"
            elif "OPTION" in suffix.upper():
                return f"{base_name} [Options/Config]"
            elif any(x in suffix.upper() for x in ["DATA", "SAVE", "PROGRESS"]):
                return f"{base_name} Save {suffix}"
            else:
                return f"{base_name} ({suffix})"
        return base_name
    
    # Ultimate fallback
    return folder_name.replace("SYSDATA", "[System]").replace("Progress", "[Progress]")


def scan_folder(base_path):
    base = Path(base_path)
    print(f"\nScanning PPSSPP SAVEDATA: {base.absolute()}")
    print("-" * 80)

    count = 0
    for folder in sorted(base.iterdir()):
        if not folder.is_dir():
            continue
            
        name = parse_param_sfo(folder.name)
        has_sfo = (folder / "PARAM.SFO").is_file()
        has_icon = (folder / "ICON0.PNG").is_file()
        
        extra = []
        if has_sfo:
            extra.append("SFO")
        if has_icon:
            extra.append("ICON")
        
        line = f"{folder.name:22} → {name}"
        if extra:
            line += f"  [{', '.join(extra)}]"
        
        print(line)
        count += 1

    print("-" * 80)
    print(f"Total folders: {count}")


# Your path
SAVES_DIRECTORY = r"C:\Users\mepla\OneDrive\Documents\PPSSPP\PSP\SAVEDATA"
scan_folder(SAVES_DIRECTORY)
