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

class DNDScanner:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.folders: Dict[str, FolderData] = {}
        self.on_update_callback = None

    def scan_all(self):
        new_folders = {}
        if not os.path.exists(self.base_path):
            self.folders = {}
            return
            
        for folder_name in os.listdir(self.base_path):
            folder_path = os.path.join(self.base_path, folder_name)
            if os.path.isdir(folder_path):
                if folder_name == '__pycache__' or folder_name.startswith('.'):
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

        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file_name in files:
                file_path = os.path.join(root, file_name)
                lower_name = file_name.lower()
                
                if lower_name.endswith(('.jpg', '.jpeg', '.png')):
                    match = re.search(r'(\d+)\s*x\s*(\d+)', file_name)
                    
                    if match:
                        w, h = int(match.group(1)), int(match.group(2))
                    else:
                        # Attempt to calculate sane defaults based on pixels
                        try:
                            with Image.open(file_path) as img:
                                img_w, img_h = img.size
                                # Aim for 30 squares on the longest side
                                if img_w >= img_h:
                                    w = 30
                                    h = max(1, int(30 * (img_h / img_w)))
                                else:
                                    h = 30
                                    w = max(1, int(30 * (img_w / img_h)))
                        except:
                            w, h = 30, 20

                    # Check if map or token (tokens usually don't have dimensions in name)
                    # For safety, if it's very small or named as token, treat as token
                    if match or "map" in lower_name or "ambush" in lower_name or "treetops" in lower_name:
                        cfg = config.get("maps", {}).get(file_name, {})
                        data.maps.append(MapData(
                            file_path, file_name, 
                            cfg.get("w", w), cfg.get("h", h),
                            cfg.get("scale", cfg.get("scale", 1.0))
                        ))
                    else:
                        if not file_name.startswith('.'):
                            data.tokens.append(TokenData(file_path, file_name))
        return data

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
