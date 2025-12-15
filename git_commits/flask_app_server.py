"""
Flask Web Application Server
Serves the web dashboard at http://localhost:5000
Run separately from the PyQt5 desktop app
"""

from flask import Flask, render_template_string, send_from_directory
import os

app = Flask(__name__)

# HTML template (the web dashboard you created)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SaveHub - Emulator Save Manager</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        h1 { color: #667eea; font-size: 2.5em; margin-bottom: 10px; }
        .status-bar { display: flex; gap: 20px; margin-top: 15px; }
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
        }
        .status-online { background: #10b981; color: white; }
        .status-offline { background: #ef4444; color: white; }
        .game-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }
        .game-card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            cursor: pointer;
        }
        .game-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .game-icon {
            width: 100%;
            height: 180px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 3em;
        }
        .game-icon img { width: 100%; height: 100%; object-fit: cover; }
        .game-info { padding: 20px; }
        .game-title {
            font-size: 1.1em;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 8px;
        }
        .game-disc-id { color: #6b7280; font-size: 0.85em; margin-bottom: 12px; }
        .launch-button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
        }
        .loading { text-align: center; padding: 40px; color: white; font-size: 1.2em; }
        .no-games {
            text-align: center;
            padding: 60px 20px;
            background: white;
            border-radius: 15px;
            color: #6b7280;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 15px;
            max-width: 500px;
            width: 90%;
        }
        .save-option {
            padding: 15px;
            margin: 10px 0;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            cursor: pointer;
        }
        .save-option:hover { border-color: #667eea; background: #f9fafb; }
        .save-option.selected { border-color: #667eea; background: #eef2ff; }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            margin: 5px;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-secondary { background: #e5e7eb; color: #4b5563; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>SaveHub</h1>
            <p>Emulator Save Manager - Web Dashboard</p>
            <div class="status-bar">
                <span id="localAgentStatus" class="status-badge status-offline">Local Agent: Checking...</span>
                <span id="gamesCount" class="status-badge" style="background: #3b82f6; color: white;">0 Games</span>
            </div>
        </header>

        <div id="loadingMessage" class="loading">Connecting to local agent...</div>
        <div id="gameLibrary" class="game-grid" style="display: none;"></div>
        <div id="noGames" class="no-games" style="display: none;">
            <h2>No Games Found</h2>
            <p>Make sure your PyQt5 desktop app is running</p>
        </div>
    </div>

    <div id="launchModal" class="modal">
        <div class="modal-content">
            <h2 id="modalGameTitle">Select Save</h2>
            <div id="saveOptions"></div>
            <div>
                <button class="btn btn-secondary" onclick="closeLaunchModal()">Cancel</button>
                <button class="btn btn-primary" onclick="confirmLaunch()">Launch</button>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = 'http://127.0.0.1:8765/api';
        let currentGame = null;
        let selectedSave = null;

        async function checkAgentStatus() {
            try {
                const response = await fetch(`${API_BASE}/status`);
                const data = await response.json();
                
                const statusEl = document.getElementById('localAgentStatus');
                if (data.status === 'online') {
                    statusEl.textContent = 'Local Agent: Online';
                    statusEl.className = 'status-badge status-online';
                    loadGames();
                } else {
                    statusEl.textContent = 'Local Agent: Offline';
                    statusEl.className = 'status-badge status-offline';
                }
            } catch (error) {
                document.getElementById('localAgentStatus').className = 'status-badge status-offline';
                document.getElementById('loadingMessage').textContent = 
                    'Local agent offline. Please start the desktop app.';
            }
        }

        async function loadGames() {
            try {
                const response = await fetch(`${API_BASE}/games`);
                const data = await response.json();
                
                document.getElementById('loadingMessage').style.display = 'none';
                document.getElementById('gamesCount').textContent = `${data.total} Games`;
                
                if (data.games.length === 0) {
                    document.getElementById('noGames').style.display = 'block';
                    return;
                }
                
                displayGames(data.games);
            } catch (error) {
                console.error('Error loading games:', error);
            }
        }

        function displayGames(games) {
            const grid = document.getElementById('gameLibrary');
            grid.style.display = 'grid';
            grid.innerHTML = '';
            
            games.forEach(game => {
                const card = document.createElement('div');
                card.className = 'game-card';
                card.onclick = () => openLaunchModal(game);
                
                card.innerHTML = `
                    <div class="game-icon">🎮</div>
                    <div class="game-info">
                        <div class="game-title">${game.title}</div>
                        <div class="game-disc-id">${game.disc_id}</div>
                        <button class="launch-button">Launch</button>
                    </div>
                `;
                
                grid.appendChild(card);
            });
        }

        function openLaunchModal(game) {
            currentGame = game;
            document.getElementById('modalGameTitle').textContent = game.title;
            document.getElementById('launchModal').classList.add('active');
        }

        function closeLaunchModal() {
            document.getElementById('launchModal').classList.remove('active');
        }

        async function confirmLaunch() {
            const response = await fetch(`${API_BASE}/launch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ disc_id: currentGame.disc_id })
            });
            
            const result = await response.json();
            alert(result.success ? 'Game launched!' : `Error: ${result.error}`);
            closeLaunchModal();
        }

        setInterval(checkAgentStatus, 5000);
        checkAgentStatus();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the web dashboard"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'online', 'service': 'SaveHub Web Dashboard'}

if __name__ == '__main__':
    print("\n" + "="*60)
    print("SaveHub Web Dashboard")
    print("="*60)
    print("\n1. Make sure your PyQt5 desktop app is running")
    print("   (It provides the local agent API on port 8765)")
    print("\n2. Open your browser to: http://localhost:5000")
    print("\n3. The web dashboard will connect to your desktop app")
    print("   and display your game library")
    print("\n" + "="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
