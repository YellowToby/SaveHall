#!/usr/bin/env python3
"""
SNES9x Recent ROMs → JSON with directories + game filenames
"""

import json
import os
from pathlib import Path
import sys


def find_snes9x_conf(snes9x_dir: str | Path | None = None) -> Path | None:
    candidates = []

    if snes9x_dir:
        base = Path(snes9x_dir).resolve()
        candidates.extend([
            base / "snes9x.conf",
            base / "Snes9x.conf",
            base / ".snes9x" / "snes9x.conf",
        ])

    if snes9x_dir:
        base = Path(snes9x_dir).resolve()
        candidates.extend([
            base.parent / "snes9x.conf",
            base.parent.parent / "snes9x.conf",
        ])

    # OS-specific fallbacks
    home = Path.home()
    if sys.platform == "win32":
        candidates.extend([
            Path(os.getenv("APPDATA", "")) / "Snes9x" / "snes9x.conf",
            Path(os.getenv("LOCALAPPDATA", "")) / "Snes9x" / "snes9x.conf",
        ])
    elif sys.platform.startswith("linux"):
        candidates.extend([
            home / ".snes9x" / "snes9x.conf",
            home / ".config" / "snes9x" / "snes9x.conf",
        ])
    elif sys.platform == "darwin":
        candidates.extend([
            home / "Library" / "Application Support" / "Snes9x" / "snes9x.conf",
        ])

    for path in candidates:
        if path.is_file():
            print(f"Found config: {path}")
            return path

    return None


def parse_recent_roms(conf_path: Path) -> dict[str, list[str]]:
    """
    Manual parse snes9x.conf → returns {directory: [rom_filenames]}
    """
    roms_by_dir: dict[str, list[str]] = {}

    try:
        with open(conf_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue

                key_part, value_part = line.split('=', 1)
                key_part = key_part.strip()
                value = value_part.strip().strip('"\'').strip()

                if not value:
                    continue

                # Match common recent ROM key patterns
                if (key_part.startswith('Rom:RecentGame') or
                    key_part.startswith('RecentRoms') or
                    key_part.startswith('RecentGame')):

                    rom_path = Path(value)
                    if rom_path.is_file():
                        rom_dir = str(rom_path.parent.resolve())
                        filename = rom_path.name

                        if rom_dir not in roms_by_dir:
                            roms_by_dir[rom_dir] = []
                        if filename not in roms_by_dir[rom_dir]:
                            roms_by_dir[rom_dir].append(filename)

    except Exception as e:
        print(f"Parse error: {e}")
        return {}

    # Sort filenames in each directory for nicer output
    for d in roms_by_dir:
        roms_by_dir[d].sort()

    return roms_by_dir


def main():
    print("SNES9x → Recent ROMs JSON Generator\n")

    if len(sys.argv) > 1:
        snes9x_folder = sys.argv[1]
    else:
        default_hint = r"(example: C:\Emulators\Snes9x)" if sys.platform == "win32" else ""
        snes9x_folder = input(
            f"Enter folder containing snes9x.conf (or snes9x executable) {default_hint}:\n> "
        ).strip()

        if not snes9x_folder:
            print("No path provided → trying automatic search...")
            snes9x_folder = None

    conf_path = find_snes9x_conf(snes9x_folder)

    if not conf_path:
        print("\nCould not find snes9x.conf.")
        print("Try playing a ROM in SNES9x first or check common locations.")
        sys.exit(1)

    print(f"\nParsing: {conf_path}\n")

    roms_data = parse_recent_roms(conf_path)

    if not roms_data:
        print("No valid recent ROM paths found in the config.")
        return

    # Output JSON
    output_file = "snes9x_recent_roms.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(roms_data, f, indent=2, ensure_ascii=False)

    print(f"JSON saved to: {output_file}")
    print("\nContent preview:")
    print(json.dumps(roms_data, indent=2))


if __name__ == "__main__":
    main()
