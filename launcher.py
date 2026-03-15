import os
import json
import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QPushButton, QLabel, QListWidget, QSpinBox, QScrollArea, 
                             QFormLayout, QSlider, QFrame, QGridLayout, QCheckBox, QMessageBox)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from scanner import DNDScanner, TokenData

class TokenConfigRow(QFrame):
    """Dedicated widget for a single character token's configuration."""
    def __init__(self, token_data: TokenData, initial_count=0, initial_size=100):
        super().__init__()
        self.token_data = token_data
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Name
        self.name_label = QLabel(f"<b>{token_data.name}</b>")
        self.name_label.setMinimumWidth(150)
        layout.addWidget(self.name_label, 2)
        
        # Quantity
        layout.addWidget(QLabel("Qty:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(0, 50)
        self.count_spin.setValue(initial_count)
        self.count_spin.setFixedWidth(60)
        layout.addWidget(self.count_spin, 0)
        
        # Size Slider
        layout.addWidget(QLabel("Size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(20, 400)
        self.size_slider.setValue(initial_size)
        self.size_slider.setMinimumWidth(100)
        layout.addWidget(self.size_slider, 2)
        
        # Size Label
        self.size_value_label = QLabel(f"{initial_size}%")
        self.size_value_label.setFixedWidth(40)
        self.size_slider.valueChanged.connect(self._update_size_label)
        layout.addWidget(self.size_value_label, 0)

    def _update_size_label(self, value):
        self.size_value_label.setText(f"{value}%")
    
    def get_config(self):
        return {
            "count": self.count_spin.value(),
            "size": self.size_slider.value()
        }

class LauncherWindow(QWidget):
    scanner_updated = Signal()

    def __init__(self, scanner: DNDScanner, on_launch):
        super().__init__()
        self.scanner = scanner
        self.on_launch = on_launch
        self.setWindowTitle("D&D Map Interactive Launcher")
        self.resize(800, 900)
        
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

        # 4. Create new rows
        for t in folder_data.tokens:
            cfg = saved_tokens.get(t.name, {"count": 0, "size": 100})
            row = TokenConfigRow(t, cfg.get("count", 0), cfg.get("size", 100))
            # Auto-save when token settings change
            row.count_spin.valueChanged.connect(self._auto_save_config)
            row.size_slider.valueChanged.connect(self._auto_save_config)
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
            self.scanner.save_folder_config(folder_data.path, full_cfg)
        except StopIteration: pass

    def run_ai_scan(self):
        """Use computer vision to detect walls and 3D assets."""
        folder_name = self.folder_combo.currentText().strip()
        map_item = self.map_list.currentItem()
        if not folder_name or not map_item: return
        
        folder_data = self.scanner.folders[folder_name]
        try:
            map_data = next(m for m in folder_data.maps if m.name == map_item.text())
            
            import cv2
            import numpy as np
            
            # Load map for analysis
            img = cv2.imread(map_data.path)
            if img is None:
                print(f"Error: Could not read image {map_data.path}")
                return
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Use adaptive thresholding to better handle varied lighting/styles
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            
            # Detect lines (Hough Transform) with stricter length requirements
            lines = cv2.HoughLinesP(thresh, 1, np.pi/180, threshold=80, minLineLength=40, maxLineGap=20)
            
            detected_walls = []
            # Base Perimeter
            grid_w, grid_h = map_data.width_squares, map_data.height_squares
            detected_walls.append({"start": [0, 0], "end": [grid_w, 0], "height": 4})
            detected_walls.append({"start": [0, 0], "end": [0, grid_h], "height": 4})
            detected_walls.append({"start": [grid_w, 0], "end": [grid_w, grid_h], "height": 4})
            detected_walls.append({"start": [0, grid_h], "end": [grid_w, grid_h], "height": 4})

            if lines is not None:
                # Convert pixel lines to grid lines
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    # Map to grid coords
                    gx1 = (x1 / w) * grid_w
                    gz1 = grid_h - ((y1 / h) * grid_h) # Invert Y to Z
                    gx2 = (x2 / w) * grid_w
                    gz2 = grid_h - ((y2 / h) * grid_h) # Invert Y to Z

                    # Filter out very short segments that aren't structural
                    grid_dist = math.sqrt((gx2-gx1)**2 + (gz2-gz1)**2)
                    if grid_dist > 1.5: 
                        detected_walls.append({
                            "start": [gx1, gz1], 
                            "end": [gx2, gz2], 
                            "height": 3
                        })
            
            map_data.scan_data = {"walls": detected_walls}
            self._auto_save_config()
            QMessageBox.information(self, "AI Scan Complete", 
                f"Detected {len(detected_walls)} wall segments using CV analysis.\nLaunch in 3D mode to see results.")
            
        except Exception as e:
            print(f"DEBUG: Error during AI scan: {e}")
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
                    tokens_to_add[t] = (cfg["count"], cfg["size"] / 100.0)
            
            self._auto_save_config()
            
            use_3d = self.mode_3d_check.isChecked()
            self.on_launch(map_data, tokens_to_add, use_3d)
        except StopIteration: pass
