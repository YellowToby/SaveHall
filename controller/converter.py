
import os

def convert_save(input_path, target_platform, output_dir="converted"):
    os.makedirs(output_dir, exist_ok=True)

    with open(input_path, "rb") as f:
        original_data = f.read()

    if target_platform == "PSP":
        converted_data = b"PSPHEADER" + original_data
        new_ext = ".bin"
    elif target_platform == "GBA":
        converted_data = original_data[:128]
        new_ext = ".sav"
    elif target_platform == "PC":
        converted_data = original_data[::-1]
        new_ext = ".dat"
    elif target_platform == "Android":
        converted_data = original_data + b"ANDROIDFOOTER"
        new_ext = ".droid"
    else:
        raise ValueError("Unsupported target platform")

    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, base + new_ext)

    with open(output_path, "wb") as f:
        f.write(converted_data)

    return output_path
