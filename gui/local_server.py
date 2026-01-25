import json
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.launcher import launch_ppsspp
from core.game_map import get_iso_for_disc_id, load_game_map
from core.psp_sfo_parser import parse_param_sfo
from core.snes9x_parser import find_snes9x_saves, get_snes9x_save_states
from core.config import get_ppsspp_path, get_savedata_dir, get_savestate_dir, get_snes9x_path, set_snes9x_path, get_snes9x_save_dir, set_snes9x_save_dir
from core.iso_scanner import ISOScanner

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from web dashboard

class LocalAgent:
    """Manages communication between web dashboard and local emulator"""
    
    def __init__(self):
        try:
            # Store paths as instance variables
            
            # PSP paths
            self.savedata_dir = get_savedata_dir()
            self.savestate_dir = get_savestate_dir()
            
            print(f"[LOCAL SERVER] SAVEDATA: {self.savedata_dir}")
            print(f"[LOCAL SERVER] SAVESTATE: {self.savestate_dir}")
            
            # SNES9x paths             
            self.snes9x_save_dir = get_snes9x_save_dir()       
            print(f"[LOCAL SERVER] SNES9X SAVES: {self.snes9x_save_dir}")

            # Initialize caches for each emulator
            self.psp_games = [] #Will replace games_cache
            self.snes_games = []
            self.dolphin_games = []  # Placeholder
            self.citra_games = []    # Placeholder
            self.games_cache = [] #Embodies all games to display correctly
            # Scan all emulators
            self.scan_all_emulators()

            
            print("[SUCCESS] LocalAgent initialized successfully")
        except Exception as e:
            print(f"[FATAL ERROR] LocalAgent initialization failed: {e}")
            import traceback
            traceback.print_exc()
            # Set defaults
            self.psp_games = []
            self.snes_games = []
            self.dolphin_games = []
            self.citra_games = []
            # Set defaults so server can still start (Can be deleted)
            self.savedata_dir = os.path.expanduser("~/Documents/PPSSPP/PSP/SAVEDATA")
            self.savestate_dir = os.path.expanduser("~/Documents/PPSSPP/PSP/PPSSPP_STATE")
            self.games_cache = []

    def scan_all_emulators(self):
        """Scan all configured emulators"""
        print("[SCAN] Scanning all emulators...")
        self.psp_games = self.scan_psp_saves()
        self.snes_games = self.scan_snes_saves()
        self.all_games = self.get_all_games()   
        # Add more as implemented
        print(f"[SCAN] Total: {len(self.psp_games)} PSP, {len(self.snes_games)} SNES, overall: {len(self.all_games)}")

    def get_all_games(self):
        """Get combined list from all emulators"""
        return self.psp_games + self.snes_games + self.dolphin_games + self.citra_games

    def get_games_by_emulator(self, emulator_id):
        """Get games for specific emulator"""
        emulator_map = {
            'ppsspp': self.psp_games,
            'snes9x': self.snes_games,
            'dolphin': self.dolphin_games,
            'citra': self.citra_games
        }
        return emulator_map.get(emulator_id, [])

    def scan_psp_saves(self):
        """Scan PSP saves - MODIFIED to tag emulator"""
        games = []
        
        if not os.path.exists(self.savedata_dir):
            print(f"[WARNING] SAVEDATA directory not found: {self.savedata_dir}")
            return games
        
        print(f"[SCAN PSP] Scanning: {self.savedata_dir}")
        
        try:
            folders = os.listdir(self.savedata_dir)
            print(f"[SCAN PSP] Found {len(folders)} folders")
        except Exception as e:
            print(f"[ERROR] Failed to list directory: {e}")
            return games
        
        for folder in folders:
            folder_path = os.path.join(self.savedata_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            
            param_path = os.path.join(folder_path, "PARAM.SFO")
            icon_path = os.path.join(folder_path, "ICON0.PNG")
            
            if os.path.exists(param_path):
                print(f"[SCAN] Parsing PARAM.SFO for {folder}...")
                game_info = self._parse_game_info(param_path, folder, icon_path)
                if game_info:
                    # TAG AS PPSSPP - CRITICAL
                    game_info['emulator'] = 'ppsspp'
                    game_info['platform'] = 'PlayStation Portable'
                    
                    game_info['save_states'] = self._get_save_states(game_info['disc_id'])
                    games.append(game_info)
        
        print(f"[SCAN PSP] Completed: {len(games)} games found")
        return games

    def scan_snes_saves(self):
        """Scan SNES9x saves - ADD THIS METHOD"""
        games = []
        
        if not hasattr(self, 'snes9x_save_dir'):
            return games
        
        if not os.path.exists(self.snes9x_save_dir):
            print(f"[WARNING] SNES9x save directory not found: {self.snes9x_save_dir}")
            return games
        
        print(f"[SCAN SNES] Scanning: {self.snes9x_save_dir}")
        
        try:
            files = os.listdir(self.snes9x_save_dir)
            print(f"[SCAN SNES] Found {len(files)} files")
        except Exception as e:
            print(f"[ERROR] Failed to list SNES directory: {e}")
            return games
        
        for file in files:
            if file.endswith('.srm') or file.endswith('.sav'):
                file_path = os.path.join(self.snes9x_save_dir, file)
                game_name = os.path.splitext(file)[0]
                
                # TAG AS SNES9X - CRITICAL
                game_info = {
                    'id': game_name,  # Use 'id' instead of 'disc_id' for SNES
                    'title': game_name,
                    'emulator': 'snes9x',
                    'platform': 'Super Nintendo',
                    'save_path': file_path,
                    'icon_path': None,
                    'has_rom': False,  # Check if ROM exists
                    'save_states': []
                }
                
                games.append(game_info)
        
        print(f"[SCAN SNES] Completed: {len(games)} games found")
        return games


    
    def _parse_game_info(self, param_path, folder_name, icon_path):
        """Extract game metadata from PARAM.SFO"""
        import time
        start = time.time()
        
        try:
            print(f"  [PARSE] Opening {param_path}...")
            open_start = time.time()
            with open(param_path, "rb") as f:
                data = f.read()
            print(f"  [PARSE] File read took {time.time() - open_start:.2f}s")
            
            # Find PSF header
            print(f"  [PARSE] Finding PSF header...")
            start_find = data.find(b'PSF\x01')
            if start_find == -1:
                return None
        
            data = data[start_find:]
            import struct
        
            magic, version, key_table_start, data_table_start, entry_count = struct.unpack("<4s I I I I", data[:20])
        
            entries = {}
            print(f"  [PARSE] Parsing {entry_count} entries...")
            for i in range(entry_count):
                entry_base = 20 + i * 16
                if entry_base + 16 > len(data):
                    continue
                
                kofs, dtype, dlen, dlen_total, dofs = struct.unpack("<HHIII", data[entry_base:entry_base+16])
            
                key_start = key_table_start + kofs
                key_end = data.find(b'\x00', key_start)
                key = data[key_start:key_end].decode('utf-8', errors='ignore')
            
                val_start = data_table_start + dofs
                val_raw = data[val_start:val_start + dlen]
            
                if dtype == 0x0204:
                    value = val_raw.split(b'\x00')[0].decode('utf-8', errors='ignore')
                elif dtype == 0x0404 and dlen == 4:
                    value = struct.unpack("<I", val_raw)[0]
                else:
                    value = val_raw.hex()
            
                entries[key] = value
        
            print(f"  [PARSE] Extracting disc ID...")
            import re
            disc_id_match = re.match(r"(ULUS|ULES|NPJH|NPUH|NPUG|UCUS|UCES|NPPA|NPEZ)[0-9]{5}", folder_name.upper())
            disc_id = disc_id_match.group(0) if disc_id_match else folder_name
        
            print(f"  [PARSE] Checking ISO mapping for {disc_id}...")
            iso_check_start = time.time()
            has_iso = bool(get_iso_for_disc_id(disc_id))
            print(f"  [PARSE] ISO check took {time.time() - iso_check_start:.2f}s")
        
            print(f"  [PARSE] Checking icon existence...")
            icon_check_start = time.time()
            icon_exists = os.path.exists(icon_path)
            print(f"  [PARSE] Icon check took {time.time() - icon_check_start:.2f}s")
        
            elapsed = time.time() - start
            print(f"  [PARSE] Total _parse_game_info took {elapsed:.2f}s")
        
            return {
                'disc_id': disc_id,
                'title': entries.get('TITLE', 'PPSSPP Game'),
                'save_title': entries.get('SAVEDATA_TITLE', ''),
                'icon_path': icon_path if icon_exists else None,
                'save_path': os.path.dirname(param_path),
                'has_iso': has_iso
            }
        
        except Exception as e:
            print(f"Error parsing {param_path}: {e}")
            return None
    
    def _get_save_states(self, disc_id):
        """Find save states for a game"""
        save_states = []
        
        if not os.path.exists(self.savestate_dir):
            return save_states
        
        for file in os.listdir(self.savestate_dir):
            if file.startswith(disc_id) and file.endswith('.ppst'):
                state_path = os.path.join(self.savestate_dir, file)
                save_states.append({
                    'filename': file,
                    'path': state_path,
                    'modified': os.path.getmtime(state_path),
                    'size': os.path.getsize(state_path)
                })
        
        return sorted(save_states, key=lambda x: x['modified'], reverse=True)

# Initialize agent
agent = LocalAgent()

# ===== API ENDPOINTS =====

@app.route('/api/status', methods=['GET'])
def get_status():
    """Check if local agent is running"""
    all_games = agent.get_all_games()
    
    return jsonify({
        'status': 'online',
        'ppsspp_configured': bool(get_ppsspp_path()),
        'total_games': len(all_games),
        'games_by_emulator': {
            'ppsspp': len(agent.psp_games),
            'snes9x': len(agent.snes_games),
            'dolphin': len(agent.dolphin_games),
            'citra': len(agent.citra_games)
        }
    })

@app.route('/api/games', methods=['GET'])
def get_games():
    """Get games from all emulators or filter by specific emulator"""
    emulator = request.args.get('emulator', 'all')
    
    # Rescan if no games found
    if not agent.psp_games and not agent.snes_games:
        agent.scan_all_emulators()
    
    # Filter by emulator
    if emulator == 'all':
        games = agent.get_all_games()
    else:
        games = agent.get_games_by_emulator(emulator)
    
    return jsonify({
        'games': games,
        'total': len(games),
        'by_emulator': {
            'ppsspp': len(agent.psp_games),
            'snes9x': len(agent.snes_games),
            'dolphin': len(agent.dolphin_games),
            'citra': len(agent.citra_games)
        }
    })


@app.route('/api/game/<disc_id>', methods=['GET'])
def get_game_details(disc_id):
    """Get detailed info about a specific game"""
    game = next((g for g in agent.all_games if g['disc_id'] == disc_id), None)
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    return jsonify(game)

@app.route('/api/launch', methods=['POST'])
def launch_game():
    """Launch a game in PPSSPP"""
    data = request.json
    disc_id = data.get('disc_id')
    save_state = data.get('save_state')  # Optional: specific save state to load
    
    if not disc_id:
        return jsonify({'error': 'disc_id required'}), 400
    
    iso_path = get_iso_for_disc_id(disc_id)
    if not iso_path or not os.path.exists(iso_path):
        return jsonify({'error': f'ISO not found for {disc_id}'}), 404
    
    try:
        if save_state:
            # Launch with specific save state
            # PPSSPP CLI: PPSSPPWindows.exe game.iso --state=path/to/state.ppst
            from core.launcher import launch_ppsspp
            # You'll need to modify launcher.py to support save states
            launch_ppsspp(iso_path, save_state=save_state)
        else:
            launch_ppsspp(iso_path)
        
        return jsonify({
            'success': True,
            'message': f'Launched {disc_id}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    """Get or update configuration"""
    if request.method == 'GET':
        from core.config import load_config
        return jsonify(load_config())
    
    elif request.method == 'POST':
        from core.config import save_config
        config = request.json
        save_config(config)
        return jsonify({'success': True})

@app.route('/api/game-map', methods=['GET', 'POST'])
def manage_game_map():
    """Get or update game-to-ISO mappings"""
    if request.method == 'GET':
        return jsonify(load_game_map())
    
    elif request.method == 'POST':
        import json
        game_map_path = os.path.join(os.path.dirname(__file__), '..', 'game_map.json')
        data = request.json
        
        with open(game_map_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        return jsonify({'success': True})

@app.route('/api/icon/<disc_id>', methods=['GET'])
def get_icon(disc_id):
    print(f"[ICON REQ] disc_id = {disc_id}")
    
    try:
        # Try main list first
        game = None
        if hasattr(agent, 'all_games'):
            game = next((g for g in agent.all_games if g.get('disc_id') == disc_id), None)
            print(f"[ICON] Checked all_games → found: {game is not None}")
        
        # Fallback to psp_games (safer right now)
        if not game:
            game = next((g for g in agent.psp_games if g.get('disc_id') == disc_id), None)
            print(f"[ICON] Fallback to psp_games → found: {game is not None}")
        
        if not game:
            print(f"[ICON 404] Game not found for {disc_id}")
            return jsonify({'error': 'Game not found'}), 404
        
        icon_path = game.get('icon_path')
        print(f"[ICON] icon_path from game = {icon_path}")
        
        if not icon_path:
            print("[ICON] No icon_path in game data")
            return '', 404
        
        if not os.path.exists(icon_path):
            print(f"[ICON] File does NOT exist: {icon_path}")
            return jsonify({'error': 'Icon file missing'}), 404
        
        print(f"[ICON] About to serve: {icon_path}")
        print(f"[ICON] File size: {os.path.getsize(icon_path)} bytes")
        
        from flask import send_file
        return send_file(icon_path, mimetype='image/png')
    
    except Exception as e:
        import traceback
        print("[ICON CRASH]")
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/refresh', methods=['POST'])
def refresh_library():
    """Manually refresh game library"""
    agent.scan_all_emulators()
    return jsonify({
        'success': True,
        'games_found': len(agent.all_games)
    })

@app.route('/api/iso-scanner/status', methods=['GET'])
def iso_scanner_status():
    """Get current ISO scan status"""
    scanner = ISOScanner()
    game_map = scanner.load_existing_game_map()
    
    return jsonify({
        'total_mapped': len(game_map),
        'game_map_path': str(scanner.game_map_path),
        'common_locations': ISOScanner.COMMON_ISO_LOCATIONS,
        'mapped_games': list(game_map.keys())
    })

@app.route('/api/iso-scanner/scan', methods=['POST'])
def scan_isos():
    """
    Trigger ISO scan
    
    Request body:
    {
        "scan_common": true,
        "custom_paths": ["/path/to/games", "/another/path"],
        "recursive": true
    }
    """
    data = request.json or {}
    scan_common = data.get('scan_common', True)
    custom_paths = data.get('custom_paths', [])
    recursive = data.get('recursive', True)
    
    scanner = ISOScanner()
    found = {}
    
    try:
        # Scan common locations
        if scan_common:
            found.update(scanner.scan_all_common_locations())
        
        # Scan custom paths
        for path in custom_paths:
            if os.path.exists(path):
                found.update(scanner.scan_directory(path, recursive=recursive))
        
        # Merge and save
        merged = scanner.merge_with_existing(found)
        scanner.save_game_map(merged)
        
        # Reload agent's game cache to show new ISOs
        agent.scan_all_emulators()
        
        return jsonify({
            'success': True,
            'found': len(found),
            'total_mapped': len(merged),
            'new_games': list(found.keys())
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/iso-scanner/add-path', methods=['POST'])
def add_custom_iso_path():
    """
    Add a single ISO file or directory to game map
    
    Request body:
    {
        "path": "/path/to/game.iso"
    }
    or
    {
        "disc_id": "ULUS10565",
        "iso_path": "/path/to/game.iso"
    }
    """
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    scanner = ISOScanner()
    
    try:
        if 'path' in data:
            # Auto-detect disc ID from file
            path = Path(data['path'])
            
            if path.is_file():
                disc_id = scanner._extract_disc_id(path)
                if not disc_id:
                    return jsonify({'error': 'Could not extract disc ID from file'}), 400
                
                game_map = scanner.load_existing_game_map()
                game_map[disc_id] = str(path.absolute())
                scanner.save_game_map(game_map)
                
                return jsonify({
                    'success': True,
                    'disc_id': disc_id,
                    'iso_path': str(path.absolute())
                })
            
            elif path.is_dir():
                # Scan directory
                found = scanner.scan_directory(str(path))
                merged = scanner.merge_with_existing(found)
                scanner.save_game_map(merged)
                
                return jsonify({
                    'success': True,
                    'found': len(found),
                    'games': list(found.keys())
                })
        
        elif 'disc_id' in data and 'iso_path' in data:
            # Manual mapping
            disc_id = data['disc_id'].upper()
            iso_path = data['iso_path']
            
            if not os.path.exists(iso_path):
                return jsonify({'error': 'ISO path does not exist'}), 400
            
            game_map = scanner.load_existing_game_map()
            game_map[disc_id] = iso_path
            scanner.save_game_map(game_map)
            
            return jsonify({
                'success': True,
                'disc_id': disc_id,
                'iso_path': iso_path
            })
        
        else:
            return jsonify({'error': 'Invalid request format'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/iso-scanner/remove', methods=['DELETE'])
def remove_iso_mapping():
    """
    Remove a disc ID from game map
    
    Request body:
    {
        "disc_id": "ULUS10565"
    }
    """
    data = request.json
    disc_id = data.get('disc_id')
    
    if not disc_id:
        return jsonify({'error': 'disc_id required'}), 400
    
    scanner = ISOScanner()
    game_map = scanner.load_existing_game_map()
    
    if disc_id in game_map:
        del game_map[disc_id]
        scanner.save_game_map(game_map)
        
        return jsonify({
            'success': True,
            'removed': disc_id
        })
    else:
        return jsonify({'error': 'Disc ID not found'}), 404

@app.route('/api/iso-scanner/verify', methods=['POST'])
def verify_iso_paths():
    """
    Verify all ISO paths in game_map.json still exist
    Returns list of missing ISOs
    """
    scanner = ISOScanner()
    game_map = scanner.load_existing_game_map()
    
    missing = []
    valid = []
    
    for disc_id, iso_path in game_map.items():
        if os.path.exists(iso_path):
            valid.append(disc_id)
        else:
            missing.append({
                'disc_id': disc_id,
                'path': iso_path
            })
    
    return jsonify({
        'total': len(game_map),
        'valid': len(valid),
        'missing': len(missing),
        'missing_games': missing
    })


@app.route('/api/iso-scanner/export', methods=['GET'])
def export_game_map():
    """Export game_map.json as downloadable file"""
    scanner = ISOScanner()
    game_map = scanner.load_existing_game_map()
    
    from flask import send_file
    import io
    
    # Create in-memory file
    json_str = json.dumps(game_map, indent=4)
    buffer = io.BytesIO(json_str.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/json',
        as_attachment=True,
        download_name='game_map.json'
    )


@app.route('/api/iso-scanner/import', methods=['POST'])
def import_game_map():
    """
    Import game_map.json from upload
    
    Form data:
    - file: game_map.json file
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    try:
        content = file.read().decode('utf-8')
        imported_map = json.loads(content)
        
        scanner = ISOScanner()
        existing_map = scanner.load_existing_game_map()
        
        # Merge imported with existing
        existing_map.update(imported_map)
        scanner.save_game_map(existing_map)
        
        return jsonify({
            'success': True,
            'imported': len(imported_map),
            'total': len(existing_map)
        })
    
    except Exception as e:
        return jsonify({'error': f'Import failed: {str(e)}'}), 500

def run_server(port=8765):
    """Start the Flask server in a separate thread"""
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)

def start_local_agent_server(port=8765):
    """Start server in background thread"""
    server_thread = Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()
    print(f"Local Agent Server running on http://127.0.0.1:{port}")
    return server_thread

if __name__ == '__main__':
    # Standalone mode
    print("Starting SaveHub Local Agent...")
    print("This enables your web dashboard to control PPSSPP")
    print("API available at: http://127.0.0.1:8765")
    run_server()
