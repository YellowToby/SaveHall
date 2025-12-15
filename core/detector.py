
import os

def detect_format(file_path):
    _, ext = os.path.splitext(file_path.lower())

    if ext == ".sav":
        return "GBA"
    elif ext == ".srm":
        return "SNES"
    elif ext == ".bin":
        return "PSP"
    elif ext == ".dat":
        return "Generic Save Format"
    else:
        return "Unknown"
