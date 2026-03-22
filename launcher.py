import os
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QPushButton, QLabel, QListWidget, QSpinBox, QScrollArea,
                             QFormLayout, QSlider, QFrame, QGridLayout, QCheckBox,
                             QLineEdit, QInputDialog, QMessageBox)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QPixmap
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

class PlayerSpriteRow(QFrame):
    """Widget for a player character sprite — checkbox, preview, name, level, HP, AC, size, familiar."""

    # Class-level list of available familiars (populated once by launcher)
    FAMILIAR_CHOICES = []

    def __init__(self, token_data: TokenData, initial_enabled=False,
                 initial_name="", initial_level=1, initial_hp=20, initial_ac=12,
                 initial_size=100, initial_familiar=""):
        super().__init__()
        self.token_data = token_data
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(5, 5, 5, 5)
        outer.setSpacing(6)

        # Checkbox to include this player
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(initial_enabled)
        outer.addWidget(self.enabled_check)

        # Sprite preview thumbnail
        preview = QLabel()
        pix = QPixmap(token_data.path)
        if not pix.isNull():
            preview.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            preview.setText("?")
        preview.setFixedSize(50, 50)
        preview.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
        outer.addWidget(preview)

        # Fields column
        fields = QVBoxLayout()
        fields.setSpacing(2)

        row1 = QHBoxLayout()
        row1.setSpacing(4)
        row1.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        short_name = extract_creature_name(token_data.name)
        self.name_edit.setText(initial_name if initial_name else short_name)
        self.name_edit.setPlaceholderText("Character name")
        row1.addWidget(self.name_edit, 2)

        row1.addWidget(QLabel("Lvl:"))
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 20)
        self.level_spin.setValue(initial_level)
        self.level_spin.setFixedWidth(50)
        row1.addWidget(self.level_spin)
        fields.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(4)
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

        row2.addWidget(QLabel("Size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(20, 400)
        self.size_slider.setValue(initial_size)
        self.size_slider.setMinimumWidth(60)
        row2.addWidget(self.size_slider, 1)
        self.size_label = QLabel(f"{initial_size}%")
        self.size_label.setFixedWidth(35)
        self.size_slider.valueChanged.connect(lambda v: self.size_label.setText(f"{v}%"))
        row2.addWidget(self.size_label)
        fields.addLayout(row2)

        # Row 3: Familiar picker
        row3 = QHBoxLayout()
        row3.setSpacing(4)
        row3.addWidget(QLabel("Familiar:"))
        self.familiar_combo = QComboBox()
        self.familiar_combo.addItem("None", "")
        for fname, fpath in self.FAMILIAR_CHOICES:
            self.familiar_combo.addItem(fname, fpath)
        # Set initial
        if initial_familiar:
            idx = self.familiar_combo.findData(initial_familiar)
            if idx >= 0:
                self.familiar_combo.setCurrentIndex(idx)
        row3.addWidget(self.familiar_combo, 1)
        fields.addLayout(row3)

        outer.addLayout(fields, 1)

    def get_config(self):
        return {
            "enabled": self.enabled_check.isChecked(),
            "name": self.name_edit.text(),
            "level": self.level_spin.value(),
            "hp": self.hp_spin.value(),
            "ac": self.ac_spin.value(),
            "size": self.size_slider.value(),
            "familiar": self.familiar_combo.currentData() or "",
        }


class LauncherWindow(QWidget):
    scanner_updated = Signal()

    def __init__(self, scanner: DNDScanner, on_launch):
        super().__init__()
        self.scanner = scanner
        self.on_launch = on_launch
        self.setWindowTitle("D&D Map Interactive Launcher")
        self.showMaximized()
        
        self._updating = False
        self.token_rows = {} # TokenData -> TokenConfigRow
        self.monster_rows = {} # TokenData -> TokenConfigRow (from monster library)
        self.player_rows = {} # TokenData -> PlayerSpriteRow
        
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

        # 3b. Monster Library (from monster_tokens/ folder)
        main_layout.addWidget(QLabel("<h3>3b. Monster Library</h3>"))
        lib_hint = QLabel("<small>Shared tokens from <b>monster_tokens/</b> folder — set qty > 0 to add</small>")
        lib_hint.setStyleSheet("color: #888;")
        main_layout.addWidget(lib_hint)

        self.monster_scroll = QScrollArea()
        self.monster_scroll.setWidgetResizable(True)
        self.monster_scroll.setMaximumHeight(200)
        self.monster_container = QWidget()
        self.monster_layout = QVBoxLayout(self.monster_container)
        self.monster_layout.setAlignment(Qt.AlignTop)
        self.monster_scroll.setWidget(self.monster_container)
        main_layout.addWidget(self.monster_scroll)

        # 4. Player Characters — Team system
        main_layout.addWidget(QLabel("<h3>4. Player Characters</h3>"))

        # Team picker row
        team_row = QHBoxLayout()
        team_row.addWidget(QLabel("Team:"))
        self.team_combo = QComboBox()
        self.team_combo.setMinimumWidth(150)
        self.team_combo.currentIndexChanged.connect(self._on_team_selected)
        team_row.addWidget(self.team_combo, 1)

        self.save_team_btn = QPushButton("Save Team")
        self.save_team_btn.setStyleSheet("font-weight: bold;")
        self.save_team_btn.clicked.connect(self._save_team)
        team_row.addWidget(self.save_team_btn)

        self.save_as_team_btn = QPushButton("Save As...")
        self.save_as_team_btn.clicked.connect(self._save_team_as)
        team_row.addWidget(self.save_as_team_btn)

        self.delete_team_btn = QPushButton("Delete")
        self.delete_team_btn.clicked.connect(self._delete_team)
        team_row.addWidget(self.delete_team_btn)
        main_layout.addLayout(team_row)

        sprites_hint = QLabel("<small>Sprites from <b>player_sprites/</b> — check to include, configure stats, then Save Team</small>")
        sprites_hint.setStyleSheet("color: #888;")
        main_layout.addWidget(sprites_hint)

        self.player_scroll = QScrollArea()
        self.player_scroll.setWidgetResizable(True)
        self.player_container = QWidget()
        self.player_layout = QVBoxLayout(self.player_container)
        self.player_layout.setAlignment(Qt.AlignTop)
        self.player_scroll.setWidget(self.player_container)
        main_layout.addWidget(self.player_scroll)

        # Launch
        bottom_frame = QFrame()
        bottom_layout = QVBoxLayout(bottom_frame)

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
        self._rebuild_monster_library()
        self._rebuild_player_sprites()
        self._refresh_team_combo()
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
            w = item.widget() if item else None
            if w:
                w.setParent(None)
                w.deleteLater()
        
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

        # 5. Rebuild monster library and player sprites with per-encounter config
        self._rebuild_monster_library()
        self._rebuild_player_sprites()

        # 6. Trigger map config load for the first map
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

    def _rebuild_monster_library(self):
        """Rebuild the monster library from monster_tokens/ folder."""
        while self.monster_layout.count():
            item = self.monster_layout.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.setParent(None)
                w.deleteLater()
        self.monster_rows = {}

        # Load saved monster config from current encounter folder
        saved_monsters = {}
        folder_name = self.folder_combo.currentText().strip()
        if folder_name and folder_name in self.scanner.folders:
            folder_data = self.scanner.folders[folder_name]
            config_path = os.path.join(folder_data.path, "config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        saved_monsters = json.load(f).get("monster_library", {})
                except:
                    pass

        if not self.scanner.monster_tokens:
            empty = QLabel("<i>No monsters. Add PNGs to monster_tokens/ folder.</i>")
            empty.setStyleSheet("color: #666; padding: 10px;")
            self.monster_layout.addWidget(empty)
            return

        for token in self.scanner.monster_tokens:
            cfg = saved_monsters.get(token.name, {"count": 0, "size": 100})
            row = TokenConfigRow(
                token,
                initial_count=cfg.get("count", 0),
                initial_size=cfg.get("size", 100),
                initial_name=cfg.get("name", ""),
                initial_hp=cfg.get("hp", 10),
                initial_ac=cfg.get("ac", 10),
                initial_is_player=False,
            )
            row.count_spin.valueChanged.connect(self._auto_save_config)
            row.size_slider.valueChanged.connect(self._auto_save_config)
            row.name_edit.textChanged.connect(self._auto_save_config)
            row.hp_spin.valueChanged.connect(self._auto_save_config)
            row.ac_spin.valueChanged.connect(self._auto_save_config)
            self.monster_layout.addWidget(row)
            self.monster_rows[token] = row

    def _rebuild_player_sprites(self):
        """Rebuild the player sprites list from scanner."""
        # Clear existing rows
        while self.player_layout.count():
            item = self.player_layout.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.setParent(None)
                w.deleteLater()
        self.player_rows = {}

        # Build familiar choices from summon catalog + token files
        familiar_choices = []
        try:
            from core.summons import SUMMON_CATALOG
            summon_dir = os.path.join(self.scanner.base_path, "summon_tokens")
            for name, data in sorted(SUMMON_CATALOG.items()):
                if data.get("category") in ("Familiar", "Beast"):
                    safe = name.replace(' ', '_').replace('(', '').replace(')', '').replace("'", '')
                    token_path = os.path.join(summon_dir, f"{safe}.png")
                    if not os.path.isfile(token_path):
                        token_path = ""
                    familiar_choices.append((name, token_path))
        except ImportError:
            pass
        PlayerSpriteRow.FAMILIAR_CHOICES = familiar_choices

        # Load saved player config from current encounter folder
        saved_players = {}
        folder_name = self.folder_combo.currentText().strip()
        if folder_name and folder_name in self.scanner.folders:
            folder_data = self.scanner.folders[folder_name]
            config_path = os.path.join(folder_data.path, "config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        saved_players = json.load(f).get("player_sprites", {})
                except:
                    pass

        if not self.scanner.player_sprites:
            empty_label = QLabel("<i>No sprites found. Add PNGs to player_sprites/ folder.</i>")
            empty_label.setStyleSheet("color: #666; padding: 10px;")
            self.player_layout.addWidget(empty_label)
            return

        for sprite in self.scanner.player_sprites:
            cfg = saved_players.get(sprite.name, {})
            row = PlayerSpriteRow(
                sprite,
                initial_enabled=cfg.get("enabled", False),
                initial_name=cfg.get("name", ""),
                initial_level=cfg.get("level", 1),
                initial_hp=cfg.get("hp", 20),
                initial_ac=cfg.get("ac", 12),
                initial_size=cfg.get("size", 100),
                initial_familiar=cfg.get("familiar", ""),
            )
            row.enabled_check.toggled.connect(self._auto_save_config)
            row.name_edit.textChanged.connect(self._auto_save_config)
            row.level_spin.valueChanged.connect(self._auto_save_config)
            row.hp_spin.valueChanged.connect(self._auto_save_config)
            row.ac_spin.valueChanged.connect(self._auto_save_config)
            row.size_slider.valueChanged.connect(self._auto_save_config)
            row.familiar_combo.currentIndexChanged.connect(self._auto_save_config)
            self.player_layout.addWidget(row)
            self.player_rows[sprite] = row

    # -- Team management ---------------------------------------------------

    def _teams_path(self):
        cfg_dir = os.path.join(self.scanner.base_path, "_config")
        os.makedirs(cfg_dir, exist_ok=True)
        return os.path.join(cfg_dir, "teams.json")

    def _load_teams(self):
        """Load all saved teams from teams.json."""
        path = self._teams_path()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_teams(self, teams):
        with open(self._teams_path(), 'w') as f:
            json.dump(teams, f, indent=4)

    def _refresh_team_combo(self):
        """Rebuild team combo from saved teams."""
        self.team_combo.blockSignals(True)
        current = self.team_combo.currentText()
        self.team_combo.clear()
        self.team_combo.addItem("(No team)")
        teams = self._load_teams()
        for name in sorted(teams.keys()):
            self.team_combo.addItem(name)
        if current and self.team_combo.findText(current) >= 0:
            self.team_combo.setCurrentText(current)
        self.team_combo.blockSignals(False)

    def _on_team_selected(self, index):
        """Load a team's config into the player sprite rows."""
        if self._updating:
            return
        team_name = self.team_combo.currentText()
        if team_name == "(No team)" or not team_name:
            return
        teams = self._load_teams()
        team = teams.get(team_name, {})
        if not team:
            return
        # Apply team config to player sprite rows
        self._updating = True
        for sprite, row in self.player_rows.items():
            cfg = team.get(sprite.name, {})
            row.enabled_check.setChecked(cfg.get("enabled", False))
            if cfg.get("name"):
                row.name_edit.setText(cfg["name"])
            row.hp_spin.setValue(cfg.get("hp", 20))
            row.ac_spin.setValue(cfg.get("ac", 12))
            row.size_slider.setValue(cfg.get("size", 100))
        self._updating = False
        self._auto_save_config()

    def _get_current_team_config(self):
        """Get current player sprite config as a team dict."""
        team = {}
        for sprite, row in self.player_rows.items():
            cfg = row.get_config()
            team[sprite.name] = cfg
        return team

    def _save_team(self):
        """Save current config to the currently selected team."""
        team_name = self.team_combo.currentText()
        if team_name == "(No team)" or not team_name:
            self._save_team_as()
            return
        teams = self._load_teams()
        teams[team_name] = self._get_current_team_config()
        self._save_teams(teams)
        QMessageBox.information(self, "Team Saved", f"Team '{team_name}' saved.")

    def _save_team_as(self):
        """Save current config as a new named team."""
        name, ok = QInputDialog.getText(self, "Save Team As", "Team name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        teams = self._load_teams()
        teams[name] = self._get_current_team_config()
        self._save_teams(teams)
        self._refresh_team_combo()
        self.team_combo.setCurrentText(name)
        QMessageBox.information(self, "Team Saved", f"Team '{name}' saved.")

    def _delete_team(self):
        """Delete the currently selected team."""
        team_name = self.team_combo.currentText()
        if team_name == "(No team)" or not team_name:
            return
        reply = QMessageBox.question(
            self, "Delete Team",
            f"Delete team '{team_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            teams = self._load_teams()
            teams.pop(team_name, None)
            self._save_teams(teams)
            self._refresh_team_combo()

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

            # Gather player sprite configs
            player_configs = {}
            for sprite, row in self.player_rows.items():
                player_configs[sprite.name] = row.get_config()

            monster_configs = {}
            for token, row in self.monster_rows.items():
                monster_configs[token.name] = row.get_config()

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
                "tokens": token_configs,
                "monster_library": monster_configs,
                "player_sprites": player_configs,
            }
            # Preserve creatures saved by the viewer
            if "creatures" in existing_cfg:
                full_cfg["creatures"] = existing_cfg["creatures"]
            self.scanner.save_folder_config(folder_data.path, full_cfg)
        except StopIteration: pass

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

            # Add monsters from library (count > 0)
            for t, row in self.monster_rows.items():
                cfg = row.get_config()
                if cfg["count"] > 0:
                    creature_cfg = {
                        "name": cfg.get("name", ""),
                        "hp": cfg.get("hp", 10),
                        "ac": cfg.get("ac", 10),
                        "is_player": False,
                    }
                    tokens_to_add[t] = (cfg["count"], cfg["size"] / 100.0, creature_cfg)

            # Add enabled player sprites (always count=1, is_player=True)
            # Also collect familiars to spawn
            familiars_to_add = []  # (familiar_name, token_path, owner_name)
            for sprite, row in self.player_rows.items():
                cfg = row.get_config()
                if cfg["enabled"]:
                    creature_cfg = {
                        "name": cfg["name"],
                        "hp": cfg["hp"],
                        "ac": cfg["ac"],
                        "is_player": True,
                    }
                    tokens_to_add[sprite] = (1, cfg["size"] / 100.0, creature_cfg)

                    # Check for familiar
                    familiar_path = cfg.get("familiar", "")
                    if familiar_path:
                        # Find familiar name from path
                        familiar_file = os.path.basename(familiar_path)
                        familiar_name = familiar_file.replace('.png', '').replace('_', ' ')
                        familiars_to_add.append((familiar_name, familiar_path, cfg["name"]))

            # Add familiars as summon tokens
            for fam_name, fam_path, owner_name in familiars_to_add:
                if os.path.isfile(fam_path):
                    fam_token = TokenData(path=fam_path, name=os.path.basename(fam_path))
                    creature_cfg = {
                        "name": f"{fam_name} ({owner_name})",
                        "hp": 1,
                        "ac": 11,
                        "is_player": False,
                        "familiar_of": owner_name,
                    }
                    tokens_to_add[fam_token] = (1, 0.5, creature_cfg)

            self._auto_save_config()
            self.on_launch(map_data, tokens_to_add)
        except StopIteration: pass
