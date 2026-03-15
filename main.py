import sys
import os
import json
import subprocess
import tempfile
from PySide6.QtWidgets import QApplication
from scanner import DNDScanner, start_watching
from launcher import LauncherWindow
from viewer import MapViewer

BASE_PATH = "/home/darkobas/Pictures/DND"

class DNDApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        
        self.scanner = DNDScanner(BASE_PATH)
        self.scanner.scan_all()
        self.observer = start_watching(BASE_PATH, self.scanner)
        
        self.launcher = LauncherWindow(self.scanner, self.launch_map)
        self.viewer = None
        
    def run(self):
        self.launcher.show()
        code = self.app.exec()
        self.observer.stop()
        self.observer.join()
        sys.exit(code)
        
    def launch_map(self, map_data, tokens_to_add, use_3d=False):
        if use_3d:
            # Prepare config for subprocess
            token_cfg = {
                t.name: (count, scale, os.path.abspath(t.path)) 
                for t, (count, scale) in tokens_to_add.items()
            }
            config = {
                "map_path": os.path.abspath(map_data.path),
                "map_name": map_data.name,
                "width_sq": map_data.width_squares,
                "height_sq": map_data.height_squares,
                "map_scale": map_data.scale,
                "tokens": token_cfg
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config, f)
                temp_path = f.name

            # Launch standalone 3D process to avoid segfault/context conflicts
            self.launcher.hide()
            try:
                subprocess.run([sys.executable, "viewer_3d.py", temp_path])
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                self.launcher.show()
        else:
            self.viewer = MapViewer(
                map_data.path, 
                map_data.width_squares, 
                map_data.height_squares, 
                tokens_to_add,
                map_data.scale
            )
            self.viewer.setWindowTitle(f"D&D Map: {map_data.name}")
            self.viewer.showFullScreen()

if __name__ == "__main__":
    app = DNDApp()
    app.run()
