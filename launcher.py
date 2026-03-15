import os
import json
import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QPushButton, QLabel, QListWidget, QSpinBox, QScrollArea,
                             QFormLayout, QSlider, QFrame, QGridLayout, QCheckBox, QMessageBox,
                             QLineEdit)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from scanner import DNDScanner, TokenData
from core.name_utils import extract_creature_name

class TokenConfigRow(QFrame):
    """Widget for a single token type — count, size, name, HP, AC."""
    def __init__(self, token_data: TokenData, initial_count=0, initial_size=100,
                 initial_name="", initial_hp=10, initial_ac=10, initial_is_player=False):
        super().__init__()
        self.token_data = token_data
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(5, 5, 5, 5)
        outer.setSpacing(3)

        # Row 1: File name + Qty + Size
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        short_name = extract_creature_name(token_data.name)
        file_label = QLabel(f"<small>{short_name}</small>")
        file_label.setMinimumWidth(100)
        file_label.setToolTip(token_data.name)
        row1.addWidget(file_label, 2)

        row1.addWidget(QLabel("Qty:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(0, 50)
        self.count_spin.setValue(initial_count)
        self.count_spin.setFixedWidth(55)
        row1.addWidget(self.count_spin)

        row1.addWidget(QLabel("Size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(20, 400)
        self.size_slider.setValue(initial_size)
        self.size_slider.setMinimumWidth(60)
        row1.addWidget(self.size_slider, 1)
        self.size_value_label = QLabel(f"{initial_size}%")
        self.size_value_label.setFixedWidth(35)
        self.size_slider.valueChanged.connect(lambda v: self.size_value_label.setText(f"{v}%"))
        row1.addWidget(self.size_value_label)
        outer.addLayout(row1)

        # Row 2: Name, HP, AC, Player checkbox
        row2 = QHBoxLayout()
        row2.setSpacing(4)

        row2.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Creature name")
        default_name = initial_name if initial_name else short_name
        self.name_edit.setText(default_name)
        self.name_edit.setMinimumWidth(80)
        row2.addWidget(self.name_edit, 2)

        row2.addWidget(QLabel("HP:"))
        self.hp_spin = QSpinBox()
        self.hp_spin.setRange(1, 9999)
        self.hp_spin.setValue(initial_hp)
        self.hp_spin.setFixedWidth(60)
        row2.addWidget(self.hp_spin)

        row2.addWidget(QLabel("AC:"))
        self.ac_spin = QSpinBox()
        self.ac_spin.setRange(0, 30)
        self.ac_spin.setValue(initial_ac)
        self.ac_spin.setFixedWidth(60)
        row2.addWidget(self.ac_spin)

        self.player_check = QCheckBox("PC")
        self.player_check.setChecked(initial_is_player)
        self.player_check.setToolTip("Player Character")
        row2.addWidget(self.player_check)

        outer.addLayout(row2)

    def get_config(self):
        return {
            "count": self.count_spin.value(),
            "size": self.size_slider.value(),
            "name": self.name_edit.text(),
            "hp": self.hp_spin.value(),
            "ac": self.ac_spin.value(),
            "is_player": self.player_check.isChecked(),
        }

class LauncherWindow(QWidget):
    scanner_updated = Signal()

    def __init__(self, scanner: DNDScanner, on_launch):
        super().__init__()
        self.scanner = scanner
        self.on_launch = on_launch
        self.setWindowTitle("D&D Map Interactive Launcher")
        self.resize(900, 900)
        
        self._updating = False
        self.token_rows = {} # TokenData -> TokenConfigRow
        
        main_layout = QVBoxLayout(self)
        
        # 1. Folder Selection
        main_layout.addWidget(QLabel("<h3>1. Select Adventure Folder</h3>"))
        self.folder_combo = QComboBox()
        self.folder_combo.setMinimumHeight(35)
        self.folder_combo.currentIndexChanged.connect(self.update_folder_selection)
        main_layout.addWidget(self.folder_combo)
        
        # 2. Map Selection
        main_layout.addWidget(QLabel("<h3>2. Select Map</h3>"))
        self.map_list = QListWidget()
        self.map_list.setMinimumHeight(150)
        self.map_list.currentRowChanged.connect(self.load_map_config)
        main_layout.addWidget(self.map_list)

        # Map Overrides Frame
        map_cfg_frame = QFrame()
        map_cfg_frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        map_cfg_layout = QFormLayout(map_cfg_frame)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 200)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 200)
        
        self.grid_scale_slider = QSlider(Qt.Horizontal)
        self.grid_scale_slider.setRange(50, 300)
        self.grid_scale_slider.setValue(100)
        self.grid_scale_label = QLabel("100%")
        self.grid_scale_slider.valueChanged.connect(lambda v: self.grid_scale_label.setText(f"{v}%"))
        
        # Connect auto-save
        self.width_spin.valueChanged.connect(self._auto_save_config)
        self.height_spin.valueChanged.connect(self._auto_save_config)
        self.grid_scale_slider.valueChanged.connect(self._auto_save_config)
        
        map_cfg_layout.addRow("Grid Columns (X):", self.width_spin)
        map_cfg_layout.addRow("Grid Rows (Y):", self.height_spin)
        
        gs_row = QHBoxLayout()
        gs_row.addWidget(self.grid_scale_slider)
        gs_row.addWidget(self.grid_scale_label)
        map_cfg_layout.addRow("Global Map Zoom:", gs_row)
        
        self.ai_scan_btn = QPushButton("AI SCAN (Detect Walls/3D)")
        self.ai_scan_btn.setStyleSheet("background-color: #9b59b6; color: white; font-weight: bold;")
        self.ai_scan_btn.clicked.connect(self.run_ai_scan)
        map_cfg_layout.addRow(self.ai_scan_btn)
        
        main_layout.addWidget(map_cfg_frame)
        
        # 3. Character Setup
        main_layout.addWidget(QLabel("<h3>3. Character Tokens</h3>"))
        
        self.token_scroll = QScrollArea()
        self.token_scroll.setWidgetResizable(True)
        self.token_container = QWidget()
        self.token_layout = QVBoxLayout(self.token_container)
        self.token_layout.setAlignment(Qt.AlignTop)
        self.token_scroll.setWidget(self.token_container)
        main_layout.addWidget(self.token_scroll)
        
        # Mode & Launch
        bottom_frame = QFrame()
        bottom_layout = QVBoxLayout(bottom_frame)
        
        self.mode_3d_check = QCheckBox("Launch in 3D Mode (Experimental Ursina Mode)")
        self.mode_3d_check.setStyleSheet("font-weight: bold; font-size: 13px; color: #2c3e50;")
        bottom_layout.addWidget(self.mode_3d_check)

        self.launch_btn = QPushButton("LAUNCH INTERACTIVE SESSION")
        self.launch_btn.clicked.connect(self.handle_launch)
        self.launch_btn.setMinimumHeight(70)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        bottom_layout.addWidget(self.launch_btn)
        main_layout.addWidget(bottom_frame)
        
        # Debounce timer for scanner updates
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.refresh_folders)
        
        self.scanner_updated.connect(lambda: self.refresh_timer.start(500))
        self.scanner.on_update_callback = lambda: self.scanner_updated.emit()
        
        # Initial trigger
        QTimer.singleShot(100, self.refresh_folders)

    @Slot()
    def refresh_folders(self):
        if self._updating: return
        self._updating = True
        
        current_folder = self.folder_combo.currentText().strip()
        self.folder_combo.clear()
        
        folders = sorted(self.scanner.folders.keys())
        self.folder_combo.addItems(folders)
        
        if current_folder in self.scanner.folders:
            self.folder_combo.setCurrentText(current_folder)
        elif folders:
            self.folder_combo.setCurrentIndex(0)
        
        self._updating = False
        # Use QTimer to ensure the combo box index change signals have fired
        QTimer.singleShot(0, lambda: self.update_folder_selection(self.folder_combo.currentIndex()))

    @Slot(int)
    def update_folder_selection(self, index):
        if self._updating or index < 0: return
        self._updating = True
        
        folder_name = self.folder_combo.currentText().strip()
        if not folder_name or folder_name not in self.scanner.folders:
            self._updating = False
            return
            
        folder_data = self.scanner.folders[folder_name]
        
        # 1. Clear & Update Map List
        self.map_list.clear()
        for m in folder_data.maps:
            self.map_list.addItem(m.name)
            
        # 2. Clear Character List
        while self.token_layout.count():
            item = self.token_layout.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()
        
        self.token_rows = {}
        
        # 3. Load character config
        config_path = os.path.join(folder_data.path, "config.json")
        saved_tokens = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    saved_tokens = json.load(f).get("tokens", {})
            except: pass

        # 4. Create new rows with saved creature stats
        for t in folder_data.tokens:
            cfg = saved_tokens.get(t.name, {"count": 0, "size": 100})
            row = TokenConfigRow(
                t,
                initial_count=cfg.get("count", 0),
                initial_size=cfg.get("size", 100),
                initial_name=cfg.get("name", ""),
                initial_hp=cfg.get("hp", 10),
                initial_ac=cfg.get("ac", 10),
                initial_is_player=cfg.get("is_player", False),
            )
            # Auto-save when any setting changes
            row.count_spin.valueChanged.connect(self._auto_save_config)
            row.size_slider.valueChanged.connect(self._auto_save_config)
            row.name_edit.textChanged.connect(self._auto_save_config)
            row.hp_spin.valueChanged.connect(self._auto_save_config)
            row.ac_spin.valueChanged.connect(self._auto_save_config)
            row.player_check.toggled.connect(self._auto_save_config)
            self.token_layout.addWidget(row)
            self.token_rows[t] = row

        self._updating = False
        
        # 5. Trigger map config load for the first map
        if self.map_list.count() > 0:
            self.map_list.setCurrentRow(0)

    @Slot(int)
    def load_map_config(self, index):
        if self._updating or index < 0: return
        
        folder_name = self.folder_combo.currentText().strip()
        if not folder_name or folder_name not in self.scanner.folders: return
            
        map_item = self.map_list.item(index)
        if not map_item: return
        
        folder_data = self.scanner.folders[folder_name]
        try:
            map_data = next(m for m in folder_data.maps if m.name == map_item.text())
            # Block signals to prevent auto-save loop during load
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.grid_scale_slider.blockSignals(True)
            
            self.width_spin.setValue(map_data.width_squares)
            self.height_spin.setValue(map_data.height_squares)
            self.grid_scale_slider.setValue(int(map_data.scale * 100))
            self.grid_scale_label.setText(f"{self.grid_scale_slider.value()}%")
            
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)
            self.grid_scale_slider.blockSignals(False)
        except StopIteration: pass

    def _auto_save_config(self):
        if self._updating: return
        folder_name = self.folder_combo.currentText().strip()
        map_item = self.map_list.currentItem()
        if not folder_name or not map_item or folder_name not in self.scanner.folders:
            return
            
        folder_data = self.scanner.folders[folder_name]
        map_name = map_item.text()
        
        try:
            map_data = next(m for m in folder_data.maps if m.name == map_name)
            map_data.width_squares = self.width_spin.value()
            map_data.height_squares = self.height_spin.value()
            map_data.scale = self.grid_scale_slider.value() / 100.0
            
            # Gather all current UI state for tokens
            token_configs = {}
            for t, row in self.token_rows.items():
                token_configs[t.name] = row.get_config()
                
            # Read existing config to preserve creature data
            existing_cfg = {}
            config_path = os.path.join(folder_data.path, "config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        existing_cfg = json.load(f)
                except Exception:
                    pass

            full_cfg = {
                "maps": {
                    m.name: {
                        "w": m.width_squares,
                        "h": m.height_squares,
                        "scale": m.scale,
                        "scan_data": m.scan_data
                    }
                    for m in folder_data.maps
                },
                "tokens": token_configs
            }
            # Preserve creatures saved by the viewer
            if "creatures" in existing_cfg:
                full_cfg["creatures"] = existing_cfg["creatures"]
            self.scanner.save_folder_config(folder_data.path, full_cfg)
        except StopIteration: pass

    def run_ai_scan(self):
        """Use computer vision to detect walls, structures, and terrain for 3D rendering."""
        folder_name = self.folder_combo.currentText().strip()
        map_item = self.map_list.currentItem()
        if not folder_name or not map_item:
            return

        folder_data = self.scanner.folders[folder_name]
        try:
            map_data = next(m for m in folder_data.maps if m.name == map_item.text())

            import cv2
            import numpy as np

            img = cv2.imread(map_data.path)
            if img is None:
                print(f"Error: Could not read image {map_data.path}")
                return

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img_h, img_w = img.shape[:2]
            grid_w, grid_h = map_data.width_squares, map_data.height_squares

            def px_to_grid(px_x, px_y):
                """Convert pixel coords to grid coords (Y inverted for 3D Z)."""
                gx = (px_x / img_w) * grid_w
                gz = grid_h - ((px_y / img_h) * grid_h)
                return gx, gz

            # ========== 1. Wall detection (Canny + Hough) ==========
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)
            # Dilate edges to connect nearby segments
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)

            lines = cv2.HoughLinesP(edges, 1, np.pi / 180,
                                     threshold=60, minLineLength=30, maxLineGap=15)

            detected_walls = []
            # Perimeter walls
            for s, e in [([0, 0], [grid_w, 0]), ([0, 0], [0, grid_h]),
                         ([grid_w, 0], [grid_w, grid_h]), ([0, grid_h], [grid_w, grid_h])]:
                detected_walls.append({"start": s, "end": e, "height": 4})

            if lines is not None:
                # Merge nearby parallel line segments
                merged = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    gx1, gz1 = px_to_grid(x1, y1)
                    gx2, gz2 = px_to_grid(x2, y2)
                    dist = math.sqrt((gx2 - gx1) ** 2 + (gz2 - gz1) ** 2)
                    if dist > 1.5:
                        merged.append({"start": [gx1, gz1], "end": [gx2, gz2], "height": 3})
                detected_walls.extend(merged)

            # ========== 2. Structure detection (dark regions = walls/pillars) ==========
            structures = []
            # Threshold dark areas (likely walls/structures in map art)
            _, dark_mask = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)
            dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
            dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

            contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cell_px_w = img_w / grid_w
            cell_px_h = img_h / grid_h
            min_area = cell_px_w * cell_px_h * 0.5  # At least half a grid cell

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_area:
                    continue

                x, y, bw, bh = cv2.boundingRect(cnt)
                gx, gz = px_to_grid(x + bw / 2, y + bh / 2)
                g_size_w = (bw / img_w) * grid_w
                g_size_h = (bh / img_h) * grid_h

                # Classify: small square = pillar, long thin = wall already handled, large = platform
                aspect = max(g_size_w, g_size_h) / max(min(g_size_w, g_size_h), 0.1)
                avg_size = (g_size_w + g_size_h) / 2

                if avg_size < 1.5 and aspect < 2:
                    # Small structure — pillar
                    structures.append({
                        "type": "pillar", "x": gx, "z": gz,
                        "h": 3, "size": avg_size, "color": [80, 75, 70]
                    })
                elif aspect < 3 and avg_size > 2:
                    # Large blocky region — raised platform/rock
                    structures.append({
                        "type": "platform", "x": gx, "z": gz,
                        "h": 1.5, "size": avg_size, "color": [70, 65, 55]
                    })

            # ========== 3. Heightmap from brightness (terrain elevation) ==========
            heightmap = []
            # Divide map into grid cells, analyze average brightness
            for gy in range(grid_h):
                for gx in range(grid_w):
                    # Pixel region for this grid cell
                    px_x1 = int(gx * cell_px_w)
                    px_y1 = int((grid_h - 1 - gy) * cell_px_h)  # Invert Y
                    px_x2 = int(px_x1 + cell_px_w)
                    px_y2 = int(px_y1 + cell_px_h)
                    px_x2 = min(px_x2, img_w)
                    px_y2 = min(px_y2, img_h)

                    cell_region = gray[px_y1:px_y2, px_x1:px_x2]
                    if cell_region.size == 0:
                        continue
                    avg_bright = float(np.mean(cell_region))

                    # Very dark cells -> raised terrain (walls/rocks)
                    if avg_bright < 40:
                        heightmap.append({
                            "x": gx, "z": gy, "w": 1, "d": 1,
                            "h": 2.0, "color": [60, 55, 50]
                        })
                    elif avg_bright < 70:
                        heightmap.append({
                            "x": gx, "z": gy, "w": 1, "d": 1,
                            "h": 0.8, "color": [75, 70, 60]
                        })

            # ========== Save results ==========
            map_data.scan_data = {
                "walls": detected_walls,
                "structures": structures,
                "heightmap": heightmap,
            }
            self._auto_save_config()

            summary = (
                f"3D Scan Complete!\n\n"
                f"Walls: {len(detected_walls)} segments\n"
                f"Structures: {len(structures)} (pillars, platforms)\n"
                f"Terrain blocks: {len(heightmap)} raised cells\n\n"
                f"Launch in 3D mode to see the results."
            )
            QMessageBox.information(self, "AI 3D Scan Complete", summary)

        except Exception as e:
            print(f"DEBUG: Error during AI scan: {e}")
            import traceback; traceback.print_exc()
            QMessageBox.warning(self, "Scan Error", f"CV Analysis failed: {str(e)}")

    def handle_launch(self):
        folder_name = self.folder_combo.currentText().strip()
        map_item = self.map_list.currentItem()
        
        if not folder_name or not map_item: return
        if folder_name not in self.scanner.folders: return
        folder_data = self.scanner.folders[folder_name]
        
        try:
            map_name = map_item.text()
            map_data = next(m for m in folder_data.maps if m.name == map_name)
            
            # Sync UI to data before last save
            map_data.width_squares = self.width_spin.value()
            map_data.height_squares = self.height_spin.value()
            map_data.scale = self.grid_scale_slider.value() / 100.0
            
            tokens_to_add = {}
            for t, row in self.token_rows.items():
                cfg = row.get_config()
                if cfg["count"] > 0:
                    creature_cfg = {
                        "name": cfg.get("name", ""),
                        "hp": cfg.get("hp", 10),
                        "ac": cfg.get("ac", 10),
                        "is_player": cfg.get("is_player", False),
                    }
                    tokens_to_add[t] = (cfg["count"], cfg["size"] / 100.0, creature_cfg)
            
            self._auto_save_config()
            
            use_3d = self.mode_3d_check.isChecked()
            self.on_launch(map_data, tokens_to_add, use_3d)
        except StopIteration: pass
