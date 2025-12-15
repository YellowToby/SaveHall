"""
Enhanced SaveHub Desktop App with Local Server
Integrates HTTP server for web dashboard communication
"""

import os
import re
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog,
    QComboBox, QHBoxLayout, QMessageBox, QListWidget, QListWidgetItem
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.detector import detect_format
from core.identifier import extract_game_name
from controller.converter import convert_save
from core.psp_sfo_parser import parse_param_sfo
from core.config import set_ppsspp_path, get_ppsspp_path
from core.launcher import launch_ppsspp
from core.game_map import get_iso_for_disc_id

# Import local server
try:
    from gui.local_server import start_local_agent_server
    SERVER_AVAILABLE = True
except ImportError:
    SERVER_AVAILABLE = False
    print("Warning: Local server not available")

class SaveTranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SaveHub - Cross-Platform Save Manager")
        self.setGeometry(100, 100, 800, 600)
        self.file_path = None
        self.disc_id = None
        self.current_game_saves = []
        
        # Start local server for web dashboard
        if SERVER_AVAILABLE:
            start_local_agent_server(port=8765)
            print("Web dashboard can connect at: http://127.0.0.1:8765")
        
        self.initUI()
        
        # Auto-refresh save states every 5 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh_saves)
        self.refresh_timer.start(5000)  # 5 seconds

    def initUI(self):
        main_layout = QVBoxLayout()
        
        # ===== Header Section =====
        header = QLabel("SaveHub - Emulator Save Manager")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        main_layout.addWidget(header)
        
        # ===== Server Status =====
        self.server_status = QLabel("🌐 Web Dashboard: http://127.0.0.1:8765")
        self.server_status.setStyleSheet("color: green; padding: 5px;")
        main_layout.addWidget(self.server_status)
        
        # ===== Game Selection Section =====
        file_section = QVBoxLayout()
        
        self.file_label = QLabel("Selected Game: None")
        self.file_label.setStyleSheet("padding: 10px; font-weight: bold;")
        
        # Icon display
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(128, 128)
        self.icon_label.setStyleSheet("border: 2px solid #ccc; border-radius: 8px;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        icon_text_layout = QHBoxLayout()
        icon_text_layout.addWidget(self.icon_label)
        
        info_layout = QVBoxLayout()
        info_layout.addWidget(self.file_label)
        self.detect_label = QLabel("Format: Not analyzed")
        info_layout.addWidget(self.detect_label)
        info_layout.addStretch()
        
        icon_text_layout.addLayout(info_layout)
        icon_text_layout.addStretch()
        
        file_section.addLayout(icon_text_layout)
        
        # File selection buttons
        button_row1 = QHBoxLayout()
        file_btn = QPushButton("📁 Choose Save Folder")
        file_btn.clicked.connect(self.choose_file)
        file_btn.setMinimumHeight(40)
        
        set_path_btn = QPushButton("⚙️ Set PPSSPP Path")
        set_path_btn.clicked.connect(self.set_ppsspp_executable)
        set_path_btn.setMinimumHeight(40)
        
        button_row1.addWidget(file_btn)
        button_row1.addWidget(set_path_btn)
        file_section.addLayout(button_row1)
        
        main_layout.addLayout(file_section)
        
        # ===== Save States Section =====
        saves_label = QLabel("Available Saves & Save States:")
        saves_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(saves_label)
        
        self.saves_list = QListWidget()
        self.saves_list.setMinimumHeight(150)
        self.saves_list.itemDoubleClicked.connect(self.launch_from_list)
        main_layout.addWidget(self.saves_list)
        
        # ===== Launch Controls =====
        launch_section = QHBoxLayout()
        
        launch_btn = QPushButton("🎮 Launch Game")
        launch_btn.clicked.connect(self.launch_game)
        launch_btn.setMinimumHeight(50)
        launch_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        refresh_btn = QPushButton("🔄 Refresh Saves")
        refresh_btn.clicked.connect(self.refresh_saves)
        refresh_btn.setMinimumHeight(50)
        
        launch_section.addWidget(launch_btn, 3)
        launch_section.addWidget(refresh_btn, 1)
        main_layout.addLayout(launch_section)
        
        # ===== Conversion Tools (Optional) =====
        tools_label = QLabel("Conversion Tools (Optional):")
        tools_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(tools_label)
        
        self.platform_dropdown = QComboBox()
        self.platform_dropdown.addItems(["Select Target Platform", "PC", "Android", "PSP", "GBA"])
        main_layout.addWidget(self.platform_dropdown)
        
        button_row2 = QHBoxLayout()
        convert_btn = QPushButton("Convert")
        upload_btn = QPushButton("Upload to Cloud")
        convert_btn.clicked.connect(self.convert_file)
        upload_btn.clicked.connect(self.upload_file)
        button_row2.addWidget(convert_btn)
        button_row2.addWidget(upload_btn)
        main_layout.addLayout(button_row2)
        
        # ===== Status Bar =====
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("padding: 10px; background: #f0f0f0; border-top: 1px solid #ccc;")
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)

    def choose_file(self):
        """Select PSP save folder"""
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_path = QFileDialog.getExistingDirectory(self, "Select PSP Save Folder", "", options=options)
        
        if file_path and os.path.isdir(file_path):
            param_path = os.path.join(file_path, "PARAM.SFO")
            icon_path = os.path.join(file_path, "ICON0.PNG")
            
            if os.path.isfile(param_path):
                self.file_path = file_path
                self.file_label.setText(f"Game: {os.path.basename(file_path)}")
                
                # Parse game info
                game_name = parse_param_sfo(param_path)
                folder_name = os.path.basename(file_path).upper()
                
                # Extract disc ID
                match = re.match(r"(ULUS|ULES|NPJH|NPUH|NPUG|UCUS|UCES|NPPA|NPEZ)[0-9]{5}", folder_name)
                if match:
                    self.disc_id = match.group(0)
                else:
                    self.disc_id = None
                
                self.detect_label.setText(f"Format: PSP\n{game_name}")
                self.status_label.setText("Status: Folder loaded")
                
                # Display icon
                if os.path.exists(icon_path):
                    pixmap = QPixmap(icon_path).scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.icon_label.setPixmap(pixmap)
                else:
                    self.icon_label.clear()
                    self.icon_label.setText("No Icon")
                
                # Load save states
                self.refresh_saves()
                return
        
        self.status_label.setText("Status: No valid save folder selected")

    def refresh_saves(self):
        """Refresh list of save files and save states"""
        if not self.disc_id:
            return
        
        self.saves_list.clear()
        self.current_game_saves = []
        
        # Add main save file
        save_item = QListWidgetItem(f"💾 Main Save File (Resume from in-game save)")
        save_item.setData(Qt.UserRole, {'type': 'save_file', 'disc_id': self.disc_id})
        self.saves_list.addItem(save_item)
        self.current_game_saves.append({'type': 'save_file'})
        
        # Find save states
        savestate_dir = os.path.expanduser("~/Documents/PPSSPP/PSP/SYSTEM/savestates")
        if os.path.exists(savestate_dir):
            for file in os.listdir(savestate_dir):
                if file.startswith(self.disc_id) and file.endswith('.ppst'):
                    state_path = os.path.join(savestate_dir, file)
                    modified = os.path.getmtime(state_path)
                    
                    from datetime import datetime
                    time_str = datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M:%S')
                    
                    state_item = QListWidgetItem(f"⚡ Save State: {file} ({time_str})")
                    state_item.setData(Qt.UserRole, {'type': 'save_state', 'path': state_path})
                    self.saves_list.addItem(state_item)
                    self.current_game_saves.append({'type': 'save_state', 'path': state_path})
        
        self.status_label.setText(f"Status: Found {len(self.current_game_saves)} save(s)")

    def auto_refresh_saves(self):
        """Auto-refresh if a game is selected"""
        if self.disc_id:
            self.refresh_saves()

    def set_ppsspp_executable(self):
        """Set PPSSPP executable path"""
        exe_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select PPSSPP Executable", 
            "", 
            "Executables (*.exe);;All Files (*)"
        )
        if exe_path:
            set_ppsspp_path(exe_path)
            self.status_label.setText(f"Status: PPSSPP path saved: {exe_path}")
            QMessageBox.information(self, "Success", f"PPSSPP path configured:\n{exe_path}")

    def launch_from_list(self, item):
        """Launch game when double-clicking a save in the list"""
        self.launch_game()

    def launch_game(self):
        """Launch game in PPSSPP"""
        if not self.disc_id:
            self.status_label.setText("Status: No game selected")
            QMessageBox.warning(self, "No Game", "Please select a save folder first")
            return
        
        # Check if PPSSPP is configured
        if not get_ppsspp_path():
            QMessageBox.warning(self, "PPSSPP Not Configured", 
                "Please set your PPSSPP executable path first")
            return
        
        # Get ISO path
        iso_path = get_iso_for_disc_id(self.disc_id)
        if not iso_path or not os.path.exists(iso_path):
            self.status_label.setText(f"Status: ISO not found for {self.disc_id}")
            QMessageBox.warning(self, "Missing ISO", 
                f"Could not find ISO for {self.disc_id}\n\nAdd it to game_map.json")
            return
        
        # Check if a save state is selected
        selected_item = self.saves_list.currentItem()
        save_state_path = None
        
        if selected_item:
            data = selected_item.data(Qt.UserRole)
            if data and data.get('type') == 'save_state':
                save_state_path = data.get('path')
        
        try:
            if save_state_path:
                # Launch with save state (you'll need to modify launcher.py)
                QMessageBox.information(self, "Launching", 
                    f"Launching with save state:\n{os.path.basename(save_state_path)}")
                # TODO: Modify launch_ppsspp to accept save_state parameter
                launch_ppsspp(iso_path)
            else:
                launch_ppsspp(iso_path)
                QMessageBox.information(self, "Launching", 
                    f"Launching game:\n{os.path.basename(iso_path)}")
            
            self.status_label.setText("Status: Game launched!")
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", str(e))
            self.status_label.setText(f"Error: {str(e)}")

    def convert_file(self):
        """Convert save file to different platform"""
        if not self.file_path:
            self.status_label.setText("Status: No file selected.")
            return

        target = self.platform_dropdown.currentText()
        if target == "Select Target Platform":
            self.status_label.setText("Status: Please choose a platform")
            return

        try:
            output_path = convert_save(self.file_path, target)
            self.status_label.setText(f"Status: Saved to {output_path}")
            QMessageBox.information(self, "Conversion Complete", 
                f"File converted and saved to:\n{output_path}")
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Conversion Error", str(e))

    def upload_file(self):
        """Upload to cloud (placeholder)"""
        self.status_label.setText("Status: Cloud upload coming soon...")
        QMessageBox.information(self, "Coming Soon", 
            "Cloud sync functionality will be added in Phase 3")

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = SaveTranslatorApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
