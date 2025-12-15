# SaveHall
A personal online save collection that supports multiple emulators 

Runs on python 8.8

How It Works 
Desktop App (PyQt5) runs on your computer with an embedded HTTP server (port 8765) that:
Scans your PSP saves and save states 
Provides REST API endpoints 
Launches PPSSPP with your selected game/save state

Web Dashboard (Flask) runs separately (port 5000) and:
shows your game library in a browser 
Works from any device on your network 
Communicates with the desktop app via API calls

Both interfaces stay in sync and control the same PPSSPP installation. 

