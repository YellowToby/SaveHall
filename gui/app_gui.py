import os
import re
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog,
    QComboBox, QHBoxLayout, QMessageBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.detector import detect_format
from core.identifier import extract_game_name
from controller.converter import convert_save
from core.psp_sfo_parser import parse_param_sfo
from core.config import set_ppsspp_path, get_ppsspp_path
from core.launcher import launch_ppsspp
from core.game_map import get_iso_for_disc_id
#from PyQt5.QtWidgets import QMessageBox
from gui.local_server import start_local_agent_server


# ISO path map
from core.game_map import get_iso_for_disc_id

class SaveTranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SaveNexus - Cross-Platform Save Translator")
        self.setGeometry(100, 100, 600, 380)
        self.file_path = None
        self.disc_id = None
        print("[TEST] Calling path detection before server start...")
        from core.config import get_savedata_dir, get_savestate_dir
        test_save = get_savedata_dir()
        test_state = get_savestate_dir()
        print(f"[TEST] Got SAVEDATA: {test_save}")
        print(f"[TEST] Got SAVESTATE: {test_state}")
        #Start the local agent server in background
        try:
            from gui.local_server import start_local_agent_server
            start_local_agent_server(port=8765)
            print("✓ Local Agent API started on http://127.0.0.1:8765")
        except Exception as e:
            print(f"⚠ Warning: Could not start local agent: {e}")
            import traceback
            traceback.print_exc()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.file_label = QLabel("Selected File: None")
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(64, 64)
        self.icon_label.setStyleSheet("border: 1px solid gray;")
        self.icon_label.setAlignment(Qt.AlignCenter)

        file_btn = QPushButton("Choose Save File or Folder")
        file_btn.clicked.connect(self.choose_file)

        set_path_btn = QPushButton("Set PPSSPP Executable")
        set_path_btn.clicked.connect(self.set_ppsspp_executable)

        launch_btn = QPushButton("Launch Game")
        launch_btn.clicked.connect(self.launch_game)

        self.detect_label = QLabel("Detected Format: Not analyzed")

        self.platform_dropdown = QComboBox()
        self.platform_dropdown.addItems(["Select Target Platform", "PC", "Android", "PSP", "GBA"])

        convert_btn = QPushButton("Convert")
        upload_btn = QPushButton("Upload to Cloud")
        convert_btn.clicked.connect(self.convert_file)
        upload_btn.clicked.connect(self.upload_file)

        file_info_layout = QHBoxLayout()
        file_info_layout.addWidget(self.icon_label)
        file_info_layout.addWidget(self.file_label)
        file_info_layout.addStretch()

        layout.addWidget(file_btn)
        layout.addLayout(file_info_layout)
        layout.addWidget(self.detect_label)
        layout.addWidget(QLabel("Target Platform:"))
        layout.addWidget(self.platform_dropdown)

        button_layout = QHBoxLayout()
        button_layout.addWidget(convert_btn)
        button_layout.addWidget(upload_btn)
        layout.addLayout(button_layout)

        layout.addWidget(set_path_btn)
        layout.addWidget(launch_btn)

        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def choose_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_path = QFileDialog.getExistingDirectory(self, "Select Save Folder", "", options=options)
        if file_path and os.path.isdir(file_path):
            param_path = os.path.join(file_path, "PARAM.SFO")
            icon_path = os.path.join(file_path, "ICON0.PNG")
            if os.path.isfile(param_path):
                self.file_path = os.path.join(file_path, "DATA.BIN")
                self.file_label.setText(f"Selected Folder: {os.path.basename(file_path)}")
                game_name = parse_param_sfo(param_path)
                folder_name = os.path.basename(file_path).upper()
                match = re.match(r"(ULUS|ULES|NPJH|NPUH|NPUG|UCUS|UCES|NPPA|NPEZ)[0-9]{5}", folder_name)
                if match:
                    self.disc_id = match.group(0)
                else:
                    self.disc_id = None
                self.detect_label.setText(f"Detected Format: PSP | Game: {game_name}")
                self.status_label.setText("Status: Folder loaded")
                if os.path.exists(icon_path):
                    pixmap = QPixmap(icon_path).scaled(64, 64, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    self.icon_label.setPixmap(pixmap)
                else:
                    self.icon_label.clear()
                return

        file_path, _ = QFileDialog.getOpenFileName(self, "Select Save File", "", "All Files (*)", options=options)
        if file_path:
            self.file_path = file_path
            self.file_label.setText(f"Selected File: {os.path.basename(file_path)}")
            detected = detect_format(file_path)
            game_name = extract_game_name(file_path)
            self.detect_label.setText(f"Detected Format: {detected} | Game: {game_name}")
            self.status_label.setText("Status: File loaded")
            self.icon_label.clear()

    def set_ppsspp_executable(self):
        exe_path, _ = QFileDialog.getOpenFileName(self, "Select PPSSPP Executable", "", "Executables (*.exe)")
        if exe_path:
            set_ppsspp_path(exe_path)
            self.status_label.setText("Status: PPSSPP path saved")

    def launch_game(self):
        if not self.disc_id:
            self.status_label.setText("Status: No game selected")
            return

        iso_path = get_iso_for_disc_id(self.disc_id)
        if not iso_path or not os.path.exists(iso_path):
            self.status_label.setText(f"Status: ISO not found for {self.disc_id}")
            alert("Missing ISO", f"Could not find ISO for {self.disc_id}")
            return

        try:
            launch_ppsspp(iso_path)
            alert("Launching", f"Running:\n{iso_path}")
            self.status_label.setText("Launching game...")
        except Exception as e:
            alert("Error", str(e))
            self.status_label.setText(f"Error: {str(e)}")


    def convert_file(self):
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
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")

    def upload_file(self):
        self.status_label.setText("Status: Uploading to cloud... (mock)")

def alert(title, msg):
    QMessageBox.information(None, title, msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SaveTranslatorApp()
    window.show()
    sys.exit(app.exec_())
