
def extract_game_name(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read(512)

        text = "".join(chr(b) if 32 <= b <= 126 else '.' for b in data)

        candidates = [w for w in text.split('.') if len(w) > 4 and w.isalnum()]
        if candidates:
            return max(candidates, key=len)

        return "Unknown Game"
    except Exception as e:
        return f"Error reading game name: {e}"
