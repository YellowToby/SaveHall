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
from core.config import get_ppsspp_path

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from web dashboard

# Default PSP save directory (configurable)
PSP_SAVEDATA_DIR = os.path.expanduser("~/Documents/PPSSPP/PSP/SAVEDATA")
PSP_SAVESTATE_DIR = os.path.expanduser("~/Documents/PPSSPP/PSP/SYSTEM/savestates")

class LocalAgent:
    """Manages communication between web dashboard and local emulator"""
    
    def __init__(self):
        self.games_cache = []
        self.scan_saves()
    
    def scan_saves(self):
        """Scan PSP save directories and build game library"""
        games = []
        
        if not os.path.exists(PSP_SAVEDATA_DIR):
            return games
        
        for folder in os.listdir(PSP_SAVEDATA_DIR):
            folder_path = os.path.join(PSP_SAVEDATA_DIR, folder)
            if not os.path.isdir(folder_path):
                continue
            
            param_path = os.path.join(folder_path, "PARAM.SFO")
            icon_path = os.path.join(folder_path, "ICON0.PNG")
            
            if os.path.exists(param_path):
                game_info = self._parse_game_info(param_path, folder, icon_path)
                if game_info:
                    # Check for save states
                    game_info['save_states'] = self._get_save_states(game_info['disc_id'])
                    games.append(game_info)
        
        self.games_cache = games
        return games
    
    def _parse_game_info(self, param_path, folder_name, icon_path):
        """Extract game metadata from PARAM.SFO"""
        try:
            with open(param_path, "rb") as f:
                data = f.read()
            
            # Find PSF header
            start = data.find(b'PSF\x01')
            if start == -1:
                return None
            
            data = data[start:]
            import struct
            
            magic, version, key_table_start, data_table_start, entry_count = struct.unpack("<4sHHII", data[:16])
            
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
                
                if dtype == 0x0204:  # UTF-8 string
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
            
            return {
                'disc_id': disc_id,
                'title': entries.get('TITLE', 'Unknown Game'),
                'save_title': entries.get('SAVEDATA_TITLE', ''),
                'icon_path': icon_path if os.path.exists(icon_path) else None,
                'save_path': os.path.dirname(param_path),
                'has_iso': bool(get_iso_for_disc_id(disc_id))
            }
            
        except Exception as e:
            print(f"Error parsing {param_path}: {e}")
            return None
    
    def _get_save_states(self, disc_id):
        """Find save states for a game"""
        save_states = []
        
        if not os.path.exists(PSP_SAVESTATE_DIR):
            return save_states
        
        # PPSSPP names save states like: ULUS10565_1.ppst
        for file in os.listdir(PSP_SAVESTATE_DIR):
            if file.startswith(disc_id) and file.endswith('.ppst'):
                state_path = os.path.join(PSP_SAVESTATE_DIR, file)
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
    return jsonify({
        'status': 'online',
        'ppsspp_configured': bool(get_ppsspp_path()),
        'saves_found': len(agent.games_cache)
    })

@app.route('/api/games', methods=['GET'])
def get_games():
    """Get all available games with saves"""
    agent.scan_saves()  # Refresh cache
    return jsonify({
        'games': agent.games_cache,
        'total': len(agent.games_cache)
    })

@app.route('/api/game/<disc_id>', methods=['GET'])
def get_game_details(disc_id):
    """Get detailed info about a specific game"""
    game = next((g for g in agent.games_cache if g['disc_id'] == disc_id), None)
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
    """Serve game icon image"""
    game = next((g for g in agent.games_cache if g['disc_id'] == disc_id), None)
    if not game or not game.get('icon_path'):
        return '', 404
    
    from flask import send_file
    return send_file(game['icon_path'], mimetype='image/png')

@app.route('/api/refresh', methods=['POST'])
def refresh_library():
    """Manually refresh game library"""
    agent.scan_saves()
    return jsonify({
        'success': True,
        'games_found': len(agent.games_cache)
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
    # Standalone mode
    print("Starting SaveHub Local Agent...")
    print("This enables your web dashboard to control PPSSPP")
    print("API available at: http://127.0.0.1:8765")
    run_server()
