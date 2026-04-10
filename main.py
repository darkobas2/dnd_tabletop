import sys
import os
import json
from PySide6.QtWidgets import QApplication
from scanner import DNDScanner, start_watching
from launcher import LauncherWindow
from viewer.viewer_2d import MapViewer
from core.game_state import EncounterState
from ui.theme import apply_theme

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

class DNDApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        apply_theme(self.app)

        self.scanner = DNDScanner(BASE_PATH)
        self.scanner.scan_all()
        self.observer = start_watching(BASE_PATH, self.scanner)

        self.launcher = LauncherWindow(self.scanner, self.launch_map)
        self.viewer = None

    def run(self):
        self.launcher.show()
        code = self.app.exec()
        # Stop file watcher — keep join short so a stuck watchdog thread
        # can't block shutdown (it's daemonized via the observer anyway).
        try:
            self.observer.stop()
            self.observer.join(timeout=2)
        except Exception:
            pass
        sys.exit(code)

    def _load_encounter(self, folder_path):
        """Load saved encounter state from config.json, or return empty."""
        config_path = os.path.join(folder_path, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                if "creatures" in cfg or "effects" in cfg:
                    load_data = {}
                    if "creatures" in cfg:
                        load_data["creatures"] = cfg["creatures"]
                    if "effects" in cfg:
                        load_data["effects"] = cfg["effects"]
                    return EncounterState.from_dict(load_data)
            except Exception:
                pass
        return EncounterState()

    def launch_map(self, map_data, tokens_to_add):
        folder_path = os.path.dirname(map_data.path)

        # Load saved encounter or create fresh
        encounter = self._load_encounter(folder_path)

        self.viewer = MapViewer(
            map_data.path,
            map_data.width_squares,
            map_data.height_squares,
            tokens_to_add,
            map_data.scale,
            encounter=encounter,
            folder_path=folder_path,
        )
        self.viewer.setWindowTitle(f"D&D Map: {map_data.name}")
        self.viewer.showFullScreen()

if __name__ == "__main__":
    app = DNDApp()
    app.run()
