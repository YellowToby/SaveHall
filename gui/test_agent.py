import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Test 1: Importing config functions...")
from core.config import get_savedata_dir, get_savestate_dir
print("✓ Import successful")

print("\nTest 2: Calling get_savedata_dir()...")
savedata = get_savedata_dir()
print(f"✓ SAVEDATA: {savedata}")

print("\nTest 3: Calling get_savestate_dir()...")
savestate = get_savestate_dir()
print(f"✓ SAVESTATE: {savestate}")

print("\nTest 4: Creating LocalAgent...")
from gui.local_server import LocalAgent
agent = LocalAgent()
print(f"✓ Agent created, found {len(agent.games_cache)} games")

print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
