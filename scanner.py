import os
import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image

@dataclass
class MapData:
    path: str
    name: str
    width_squares: int = 30
    height_squares: int = 20
    scale: float = 1.0
    scan_data: dict = field(default_factory=dict)

@dataclass(frozen=True)
class TokenData:
    path: str
    name: str

@dataclass
class FolderData:
    path: str
    name: str
    maps: List[MapData] = field(default_factory=list)
    tokens: List[TokenData] = field(default_factory=list)

SKIP_FOLDERS = {'__pycache__', 'player_sprites', 'core', 'ui', 'viewer', 'net'}

class DNDScanner:
    PLAYER_SPRITES_DIR = "player_sprites"

    def __init__(self, base_path: str):
        self.base_path = base_path
        self.folders: Dict[str, FolderData] = {}
        self.player_sprites: List[TokenData] = []
        self.on_update_callback = None

    def scan_all(self):
        new_folders = {}
        if not os.path.exists(self.base_path):
            self.folders = {}
            self.player_sprites = []
            return

        self.player_sprites = self._scan_player_sprites()

        for folder_name in os.listdir(self.base_path):
            folder_path = os.path.join(self.base_path, folder_name)
            if os.path.isdir(folder_path):
                if folder_name in SKIP_FOLDERS or folder_name.startswith('.'):
                    continue
                new_folders[folder_name] = self.scan_folder(folder_path)
        
        self.folders = new_folders
        if self.on_update_callback:
            self.on_update_callback()

    def scan_folder(self, folder_path: str) -> FolderData:
        folder_name = os.path.basename(folder_path)
        data = FolderData(folder_path, folder_name)
        
        config_path = os.path.join(folder_path, "config.json")
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
            except: pass

        maps_config = config.get("maps", {})

        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file_name in files:
                file_path = os.path.join(root, file_name)
                lower_name = file_name.lower()
                
                if lower_name.endswith(('.jpg', '.jpeg', '.png')):
                    # Check if it's already in config
                    cfg = maps_config.get(file_name)
                    
                    if cfg:
                        # Use config values
                        data.maps.append(MapData(
                            path=file_path,
                            name=file_name,
                            width_squares=cfg.get("w", 30),
                            height_squares=cfg.get("h", 20),
                            scale=cfg.get("scale", 1.0),
                            scan_data=cfg.get("scan_data", {})
                        ))
                    else:
                        # Try to detect if it's a map or token
                        match = re.search(r'(\d+)\s*x\s*(\d+)', file_name)
                        is_map = match or any(x in lower_name for x in ["map", "ambush", "treetops", "floor", "room"])
                        
                        if is_map:
                            if match:
                                w, h = int(match.group(1)), int(match.group(2))
                            else:
                                try:
                                    with Image.open(file_path) as img:
                                        iw, ih = img.size
                                        if iw >= ih:
                                            w, h = 30, max(1, int(30 * (ih / iw)))
                                        else:
                                            h, w = 30, max(1, int(30 * (iw / ih)))
                                except:
                                    w, h = 30, 20
                            
                            data.maps.append(MapData(file_path, file_name, w, h))
                        else:
                            if not file_name.startswith('.'):
                                data.tokens.append(TokenData(file_path, file_name))
        return data

    def _scan_player_sprites(self) -> List[TokenData]:
        """Scan the player_sprites/ folder for character sprite PNGs."""
        sprites_dir = os.path.join(self.base_path, self.PLAYER_SPRITES_DIR)
        if not os.path.isdir(sprites_dir):
            return []
        sprites = []
        for fname in sorted(os.listdir(sprites_dir)):
            if fname.lower().endswith(('.png', '.jpg', '.jpeg')) and not fname.startswith('.'):
                sprites.append(TokenData(
                    path=os.path.join(sprites_dir, fname),
                    name=fname
                ))
        return sprites

    def save_folder_config(self, folder_path: str, config_data: dict):
        config_path = os.path.join(folder_path, "config.json")
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)

class DNDWatchHandler(FileSystemEventHandler):
    def __init__(self, scanner: DNDScanner):
        self.scanner = scanner

    def on_any_event(self, event):
        path = event.src_path.lower()
        if event.is_directory:
            self.scanner.scan_all()
        elif path.endswith(('.jpg', '.jpeg', '.png', '.json')):
            if '__pycache__' not in path and not os.path.basename(path).startswith('.'):
                self.scanner.scan_all()

def start_watching(base_path: str, scanner: DNDScanner):
    observer = Observer()
    handler = DNDWatchHandler(scanner)
    observer.schedule(handler, base_path, recursive=True)
    observer.start()
    return observer
