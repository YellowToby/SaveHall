
import struct

def parse_param_sfo(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()

        print(f"Reading PARAM.SFO: {file_path}")
        print("Header Bytes:", data[:16].hex())

        # Align to actual header
        start = data.find(b'PSF\x01')
        if start == -1:
            return "Invalid SFO format"
        data = data[start:]

        if len(data) < 20:
            return "PARAM.SFO too small"

        # Corrected variable unpacking
        #magic, version, key_table_start, data_table_start, entry_count = struct.unpack("<4sHHIII", data[:20])
        magic, version, key_table_start, data_table_start, entry_count = struct.unpack("<4sHHII", data[:16])

        
        if magic != b'PSF\x01':
            return "Invalid SFO signature"

        entries = {}
        for i in range(entry_count):
            entry_base = 20 + i * 16
            if entry_base + 16 > len(data):
                continue
            kofs, dtype, dlen, dlen_total, dofs = struct.unpack("<HHIII", data[entry_base:entry_base+16])

            key_start = key_table_start + kofs
            key_end = data.find(b'\x00', key_start)
            key = data[key_start:key_end].decode('utf-8')

            val_start = data_table_start + dofs
            val_raw = data[val_start:val_start + dlen]

            if dtype == 0x0204:  # UTF-8 string
                value = val_raw.split(b'\x00')[0].decode('utf-8')
            elif dtype == 0x0404 and dlen == 4:
                value = struct.unpack("<I", val_raw)[0]
            else:
                value = val_raw.hex()

            entries[key] = value

        game_title = (
            entries.get("TITLE")
            or entries.get("SAVEDATA_TITLE")
            or entries.get("TITLE_ID")
            or "Unknown Game"
        )
        disc_id = entries.get("DISC_ID", "")
        version = entries.get("VERSION", "")
        fw_ver = entries.get("SYSTEM_VER", "")
        save_title = entries.get("SAVEDATA_TITLE", "")
        cat = entries.get("CATEGORY", "")
        parental = entries.get("PARENTAL_LEVEL", "")

        return f"{game_title} ({disc_id})\nVersion: {version}\nSystem Ver: {fw_ver}\nCategory: {cat}\nSave Title: {save_title}\nParental: {parental}"
    except Exception as e:
        return f"Error parsing PARAM.SFO: {e}"
