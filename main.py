import sys
import os
import json
import subprocess
import tempfile
from PySide6.QtWidgets import QApplication
from scanner import DNDScanner, start_watching
from launcher import LauncherWindow
from viewer.viewer_2d import MapViewer
from core.game_state import EncounterState
from ui.theme import apply_theme
from ipc_bridge import IPCServer

BASE_PATH = "/home/darkobas/Pictures/DND"

class DNDApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        apply_theme(self.app)

        self.scanner = DNDScanner(BASE_PATH)
        self.scanner.scan_all()
        self.observer = start_watching(BASE_PATH, self.scanner)

        self.launcher = LauncherWindow(self.scanner, self.launch_map)
        self.viewer = None
        self.ipc_server = None

    def run(self):
        self.launcher.show()
        code = self.app.exec()
        self.observer.stop()
        self.observer.join()
        if self.ipc_server:
            self.ipc_server.stop()
        sys.exit(code)

    def launch_map(self, map_data, tokens_to_add, use_3d=False):
        if use_3d:
            # Prepare config for subprocess
            token_cfg = {
                t.name: (count, scale, os.path.abspath(t.path))
                for t, (count, scale) in tokens_to_add.items()
            }

            # Start IPC server for 3D communication
            self.ipc_server = IPCServer(on_message=self._handle_3d_message)
            self.ipc_server.start()

            config = {
                "map_path": os.path.abspath(map_data.path),
                "map_name": map_data.name,
                "width_sq": map_data.width_squares,
                "height_sq": map_data.height_squares,
                "map_scale": map_data.scale,
                "scan_data": map_data.scan_data,
                "tokens": token_cfg,
                "ipc_port": self.ipc_server.port,
            }

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config, f)
                temp_path = f.name

            self.launcher.hide()
            try:
                subprocess.run([sys.executable, "viewer_3d.py", temp_path])
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                if self.ipc_server:
                    self.ipc_server.stop()
                    self.ipc_server = None
                self.launcher.show()
        else:
            # Create encounter state for the 2D session
            encounter = EncounterState()

            self.viewer = MapViewer(
                map_data.path,
                map_data.width_squares,
                map_data.height_squares,
                tokens_to_add,
                map_data.scale,
                encounter=encounter,
            )
            self.viewer.setWindowTitle(f"D&D Map: {map_data.name}")
            self.viewer.showFullScreen()

    def _handle_3d_message(self, msg):
        """Handle messages from the 3D subprocess."""
        msg_type = msg.get("type")
        if msg_type == "ready":
            print("3D viewer connected via IPC")
        elif msg_type == "token_moved":
            print(f"Token moved in 3D: {msg}")

if __name__ == "__main__":
    app = DNDApp()
    app.run()
