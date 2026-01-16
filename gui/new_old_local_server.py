import json
import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from threading import Thread
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.launcher import launch_ppsspp
from core.game_map import get_iso_for_disc_id, load_game_map
from core.psp_sfo_parser import parse_param_sfo
from core.config import get_ppsspp_path, get_savedata_dir, get_savestate_dir

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from web dashboard

class LocalAgent:
    """Manages communication between web dashboard and local emulators"""
    
    def __init__(self):
        try:
            # PSP paths
            self.savedata_dir = get_savedata_dir()
            self.savestate_dir = get_savestate_dir()
            
            print(f"[LOCAL SERVER] PPSSPP SAVEDATA: {self.savedata_dir}")
            print(f"[LOCAL SERVER] PPSSPP SAVESTATE: {self.savestate_dir}")
            
            # Initialize separate caches for each emulator
            self.psp_games = []
            self.snes_games = []
            self.dolphin_games = []
            self.citra_games = []
            
            # Scan all configured emulators
            self.scan_all_emulators()
            
            print("[SUCCESS] LocalAgent initialized successfully")
        except Exception as e:
            print(f"[FATAL ERROR] LocalAgent initialization failed: {e}")
            import traceback
            traceback.print_exc()
            # Set defaults so server can still start
            self.savedata_dir = os.path.expanduser("~/Documents/PPSSPP/PSP/SAVEDATA")
            self.savestate_dir = os.path.expanduser("~/Documents/PPSSPP/PSP/PPSSPP_STATE")
            self.psp_games = []
            self.snes_games = []
            self.dolphin_games = []
            self.citra_games = []
    
    def scan_all_emulators(self):
        """Scan all configured emulators"""
        print("[SCAN] Scanning all emulators...")
        self.psp_games = self.scan_psp_saves()
        # Future emulators will go here:
        # self.snes_games = self.scan_snes_saves()
        # self.dolphin_games = self.scan_dolphin_saves()
        print(f"[SCAN] Total: {len(self.psp_games)} PSP games")
    
    def get_all_games(self):
        """
        Get combined list of games from all emulators
        Returns list with emulator type tagged on each game
        """
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
        """Scan PSP save directories and build game library"""
        games = []
    
        if not os.path.exists(self.savedata_dir):
            print(f"[WARNING] SAVEDATA directory not found: {self.savedata_dir}")
            return games
    
        print(f"[SCAN PSP] Scanning: {self.savedata_dir}")
    
        import time
        start = time.time()
        
        try:
            folders = os.listdir(self.savedata_dir)
            print(f"[SCAN PSP] Found {len(folders)} folders")
        except Exception as e:
            print(f"[ERROR] Failed to list directory: {e}")
            return games
    
        # Process each save folder
        for i, folder in enumerate(folders):
            folder_path = os.path.join(self.savedata_dir, folder)
            if not os.path.isdir(folder_path):
                continue
    
            param_path = os.path.join(folder_path, "PARAM.SFO")
            icon_path = os.path.join(folder_path, "ICON0.PNG")

            if os.path.exists(param_path):
                game_info = self._parse_psp_game(param_path, folder, icon_path)
                if game_info:
                    # Tag this game as belonging to PPSSPP
                    game_info['emulator'] = 'ppsspp'
                    game_info['platform'] = 'PlayStation Portable'
                    
                    # Get save states for this game
                    game_info['save_states'] = self._get_psp_save_states(game_info['disc_id'])
                    
                    games.append(game_info)
        
        elapsed = time.time() - start
        print(f"[SCAN PSP] Completed: {len(games)} games found in {elapsed:.2f}s")
        return games
    
    def _parse_psp_game(self, param_path, folder_name, icon_path):
        """Extract game metadata from PARAM.SFO"""
        try:
            with open(param_path, "rb") as f:
                data = f.read()
            
            # Find PSF header
            start_pos = data.find(b'PSF\x01')
            if start_pos == -1:
                return None
        
            data = data[start_pos:]
            import struct
        
            magic, version, key_table_start, data_table_start, entry_count = struct.unpack("<4s I I I I", data[:20])
        
            entries = {}
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
        
            # Extract disc ID from folder name
            import re
            disc_id_match = re.match(r"(ULUS|ULES|NPJH|NPUH|NPUG|UCUS|UCES|NPPA|NPEZ)[0-9]{5}", folder_name.upper())
            disc_id = disc_id_match.group(0) if disc_id_match else folder_name
        
            # Check if ISO is mapped
            has_iso = bool(get_iso_for_disc_id(disc_id))
            icon_exists = os.path.exists(icon_path)
        
            return {
                'disc_id': disc_id,  # Unique ID for PSP games
                'title': entries.get('TITLE', 'Unknown Game'),
                'save_title': entries.get('SAVEDATA_TITLE', ''),
                'icon_path': icon_path if icon_exists else None,
                'save_path': os.path.dirname(param_path),
                'has_iso': has_iso,
                # Note: 'emulator' and 'platform' will be added by scan_psp_saves()
            }
        
        except Exception as e:
            print(f"[ERROR] Failed to parse {param_path}: {e}")
            return None
    
    def _get_psp_save_states(self, disc_id):
        """Find save states for a PSP game"""
        save_states = []
        
        if not os.path.exists(self.savestate_dir):
            return save_states
        
        # PPSSPP names save states: DISCID_slot.ppst
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
    """
    Get games from all emulators or filter by specific emulator
    Query params:
        ?emulator=ppsspp - Get only PSP games
        ?emulator=all (default) - Get all games
    """
    emulator = request.args.get('emulator', 'all')
    
    # Rescan if no games found
    if not agent.psp_games:
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
    # Search in all emulator caches
    all_games = agent.get_all_games()
    game = next((g for g in all_games if g.get('disc_id') == disc_id), None)
    
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    return jsonify(game)

@app.route('/api/launch', methods=['POST'])
def launch_game():
    """Launch a game in appropriate emulator"""
    data = request.json
    disc_id = data.get('disc_id')
    save_state = data.get('save_state')
    
    if not disc_id:
        return jsonify({'error': 'disc_id required'}), 400
    
    # Find the game to determine which emulator to use
    all_games = agent.get_all_games()
    game = next((g for g in all_games if g.get('disc_id') == disc_id), None)
    
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    emulator = game.get('emulator', 'ppsspp')
    
    try:
        if emulator == 'ppsspp':
            iso_path = get_iso_for_disc_id(disc_id)
            if not iso_path or not os.path.exists(iso_path):
                return jsonify({'error': f'ISO not found for {disc_id}'}), 404
            
            launch_ppsspp(iso_path, save_state=save_state)
            
        # Future emulators will go here:
        # elif emulator == 'snes9x':
        #     launch_snes9x(game['rom_path'], save_state)
        # elif emulator == 'dolphin':
        #     launch_dolphin(game['iso_path'], save_state)
        
        else:
            return jsonify({'error': f'Emulator {emulator} not yet supported'}), 400
        
        return jsonify({
            'success': True,
            'message': f'Launched {disc_id} in {emulator}'
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
        game_map_path = os.path.join(os.path.dirname(__file__), '..', 'game_map.json')
        data = request.json
        
        with open(game_map_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        return jsonify({'success': True})

@app.route('/api/icon/<disc_id>', methods=['GET'])
def get_icon(disc_id):
    """Serve game icon image"""
    # Search in all emulator caches
    all_games = agent.get_all_games()
    game = next((g for g in all_games if g.get('disc_id') == disc_id), None)
    
    if not game or not game.get('icon_path'):
        return '', 404
    
    return send_file(game['icon_path'], mimetype='image/png')

@app.route('/api/refresh', methods=['POST'])
def refresh_library():
    """Manually refresh game library for all emulators"""
    agent.scan_all_emulators()
    all_games = agent.get_all_games()
    
    return jsonify({
        'success': True,
        'total_games': len(all_games),
        'by_emulator': {
            'ppsspp': len(agent.psp_games),
            'snes9x': len(agent.snes_games),
            'dolphin': len(agent.dolphin_games),
            'citra': len(agent.citra_games)
        }
    })

@app.route('/api/emulators', methods=['GET'])
def get_emulators():
    """Get list of supported emulators and their status"""
    return jsonify({
        'emulators': [
            {
                'id': 'ppsspp',
                'name': 'PPSSPP',
                'platform': 'PlayStation Portable',
                'configured': bool(get_ppsspp_path()),
                'game_count': len(agent.psp_games),
                'status': 'active'
            },
            {
                'id': 'snes9x',
                'name': 'Snes9x',
                'platform': 'Super Nintendo',
                'configured': False,
                'game_count': len(agent.snes_games),
                'status': 'coming_soon'
            },
            {
                'id': 'dolphin',
                'name': 'Dolphin',
                'platform': 'GameCube / Wii',
                'configured': False,
                'game_count': len(agent.dolphin_games),
                'status': 'coming_soon'
            },
            {
                'id': 'citra',
                'name': 'Citra',
                'platform': 'Nintendo 3DS',
                'configured': False,
                'game_count': len(agent.citra_games),
                'status': 'coming_soon'
            }
        ]
    })

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
    print("Starting SaveNexus Local Agent...")
    print("Multi-emulator save management system")
    print("API available at: http://127.0.0.1:8765")
    run_server()
