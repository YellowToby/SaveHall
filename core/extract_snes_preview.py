import struct
import os
import gzip
import io                  # ← fixed here
from PIL import Image
from pathlib import Path

def extract_snes9x_preview(save_state_path: str | Path, output_png: str | Path | None = None) -> bool:
    path = Path(save_state_path)
    if not path.is_file():
        print(f"File not found: {path}")
        return False

    try:
        raw_data = path.read_bytes()

        # Detect & decompress if gzipped
        if raw_data.startswith(b'\x1f\x8b'):
            print("Detected gzip compression → decompressing...")
            with gzip.GzipFile(fileobj=io.BytesIO(raw_data)) as gz:
                data = gz.read()
            print(f"Decompressed size: {len(data):,} bytes")
        else:
            data = raw_data
            print("No gzip detected → using raw data")

        pos = 0

        # Check header
        header = data[pos:pos + 8]
        header_str = header.decode('ascii', errors='ignore')
        print(f"Header preview: {header_str!r}  (first 16 hex: {' '.join(f'{b:02x}' for b in data[:16])})")

        if not header.startswith(b'SNES') or not header.endswith(b'\n'):
            print("Invalid header - not a recognized Snes9x snapshot")
            return False

        pos += len(header)

        found_sho = False

        while pos < len(data):
            block_id_end = data.find(b':', pos)
            if block_id_end == -1:
                break
            block_name_bytes = data[pos:block_id_end]
            try:
                block_name = block_name_bytes.decode('ascii')
            except UnicodeDecodeError:
                break
            pos = block_id_end + 1

            size_str_end = data.find(b':', pos)
            if size_str_end == -1:
                break
            size_str_bytes = data[pos:size_str_end]
            try:
                size_str = size_str_bytes.decode('ascii')
            except UnicodeDecodeError:
                break
            pos = size_str_end + 1

            if size_str == '------':
                if pos + 4 > len(data):
                    break
                size = struct.unpack('>I', data[pos:pos+4])[0]
                pos += 4
            else:
                try:
                    size = int(size_str)
                except ValueError:
                    break

            if block_name == 'SHO':
                found_sho = True
                print(f"Found SHO block! Size: {size:,} bytes")

                if pos + size > len(data):
                    print("Block truncated")
                    return False

                if size < 8:
                    print("SHO block too small")
                    return False

                width, height = struct.unpack_from('<HH', data, pos)
                rgb_offset = pos + 8
                rgb_size = width * height * 3

                if rgb_offset + rgb_size > len(data):
                    print("RGB data truncated")
                    return False

                rgb_data = data[rgb_offset : rgb_offset + rgb_size]

                img = Image.frombytes('RGB', (width, height), rgb_data)

                if output_png is None:
                    output_png = path.with_suffix('.preview.png')

                output_path = Path(output_png)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(output_path)
                print(f"Success! Preview saved to: {output_path}")
                print(f"Image size: {width} × {height}")
                return True

            pos += size

        if not found_sho:
            print("No 'SHO' (screenshot) block found in this save state.")
        return False

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False


# ────────────────────────────────────────────────
if __name__ == "__main__":
    save_file = r"D:\Kurt\GOG Games\SNES\Saves\Super Mario All-Stars + Super Mario World (USA).000"
    success = extract_snes9x_preview(save_file)
    if success:
        print("\nDone! Check for the .preview.png file next to the original.")
    else:
        print("\nExtraction failed — see messages above.")
