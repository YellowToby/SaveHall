import subprocess
import os
from core.config import get_ppsspp_path

def launch_ppsspp(iso_path):
    exe_path = get_ppsspp_path()

    with open("launch.log", "a") as log:
        log.write(f"[DEBUG] Executable: {exe_path}\n")
        log.write(f"[DEBUG] ISO: {iso_path}\n")

    if not exe_path or not os.path.exists(exe_path):
        raise FileNotFoundError("PPSSPP executable path not set or does not exist.")

    if not iso_path or not os.path.exists(iso_path):
        raise FileNotFoundError("Game ISO path is invalid or does not exist.")

    args = [exe_path, iso_path]
    try:
        subprocess.Popen(args, shell=False)
        with open("launch.log", "a") as log:
            log.write("[DEBUG] Launched successfully.\n")
    except Exception as e:
        with open("launch.log", "a") as log:
            log.write(f"[ERROR] Failed to launch: {e}\n")
        raise RuntimeError(f"Failed to launch PPSSPP: {e}")
