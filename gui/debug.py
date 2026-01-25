"""
Debug script to check emulator separation
Run this to verify games are being tagged correctly
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.local_server import agent

print("=" * 60)
print("EMULATOR SEPARATION DEBUG")
print("=" * 60)

# Force rescan
agent.scan_all_emulators()

print("\n" + "=" * 60)
print("PSP/PPSSPP GAMES")
print("=" * 60)
print(f"Total: {len(agent.psp_games)}")
for i, game in enumerate(agent.psp_games[:20], 1):
    print(f"\n{i}. {game['title']}")
    print(f"   Disc ID: {game.get('disc_id', 'N/A')}")
    print(f"   Emulator: {game.get('emulator', 'MISSING!')}")
    print(f"   Platform: {game.get('platform', 'MISSING!')}")
    print(f"   Has ISO: {game.get('has_iso', False)}")
    print(f"   Has Icon: {game.get('icon_exists')}")

if len(agent.psp_games) > 20:
    print(f"\n... and {len(agent.psp_games) - 5} more")

print("\n" + "=" * 60)
print("SNES9X GAMES")
print("=" * 60)
print(f"Total: {len(agent.snes_games)}")
for i, game in enumerate(agent.snes_games[:5], 1):
    print(f"\n{i}. {game['title']}")
    print(f"   ID: {game.get('id', 'N/A')}")
    print(f"   Emulator: {game.get('emulator', 'MISSING!')}")
    print(f"   Platform: {game.get('platform', 'MISSING!')}")
    print(f"   Has ROM: {game.get('icon_path', False)}")

if len(agent.snes_games) > 5:
    print(f"\n... and {len(agent.snes_games) - 5} more")

print("\n" + "=" * 60)
print("ALL GAMES COMBINED")
print("=" * 60)
all_games = agent.get_all_games()
print(f"Total: {len(all_games)}")

# Count by emulator
emulator_counts = {}
for game in all_games:
    emu = game.get('emulator', 'UNKNOWN')
    emulator_counts[emu] = emulator_counts.get(emu, 0) + 1

print("\nBreakdown by emulator:")
for emu, count in emulator_counts.items():
    print(f"  {emu}: {count}")

print("\n" + "=" * 60)
print("TEST FILTERING")
print("=" * 60)

ppsspp_filtered = agent.get_games_by_emulator('ppsspp')
snes_filtered = agent.get_games_by_emulator('snes9x')

print(f"PPSSPP filter: {len(ppsspp_filtered)} games")
print(f"SNES9x filter: {len(snes_filtered)} games")

# Check for cross-contamination
print("\n" + "=" * 60)
print("CROSS-CONTAMINATION CHECK")
print("=" * 60)

ppsspp_wrong = [g for g in ppsspp_filtered if g.get('emulator') != 'ppsspp']
snes_wrong = [g for g in snes_filtered if g.get('emulator') != 'snes9x']

if ppsspp_wrong:
    print(f"⚠️ WARNING: {len(ppsspp_wrong)} non-PPSSPP games in PPSSPP list:")
    for game in ppsspp_wrong[:3]:
        print(f"   - {game['title']} (emulator={game.get('emulator')})")
else:
    print("✓ PPSSPP filter is clean")

if snes_wrong:
    print(f"⚠️ WARNING: {len(snes_wrong)} non-SNES games in SNES list:")
    for game in snes_wrong[:3]:
        print(f"   - {game['title']} (emulator={game.get('emulator')})")
else:
    print("✓ SNES9x filter is clean")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print(all_games)
print("=" * 60)
