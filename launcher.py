import os
import json
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QPushButton, QLabel, QListWidget, QSpinBox, QScrollArea,
                             QFormLayout, QSlider, QFrame, QGridLayout, QCheckBox,
                             QLineEdit, QInputDialog, QMessageBox, QTabWidget)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSize
from glob import glob as globfiles
from PySide6.QtGui import QPixmap, QIcon
from scanner import DNDScanner, TokenData
from core.name_utils import extract_creature_name

class TokenConfigRow(QFrame):
    """Widget for a single token type — preview, count, size, name, HP, AC, remove."""
    removed = Signal()  # emitted when Remove is clicked

    def __init__(self, token_data: TokenData, initial_count=0, initial_size=100,
                 initial_name="", initial_hp=10, initial_ac=10, initial_is_player=False):
        super().__init__()
        self.token_data = token_data
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(6)

        # Token preview
        preview = QLabel()
        pix = QPixmap(token_data.path)
        if not pix.isNull():
            preview.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            preview.setText("?")
        preview.setFixedSize(66, 66)
        preview.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
        preview.setToolTip(token_data.name)
        outer.addWidget(preview)

        # Fields column
        fields = QVBoxLayout()
        fields.setSpacing(2)

        # Row 1: Name + Qty + Remove
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        short_name = extract_creature_name(token_data.name)

        row1.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Creature name")
        default_name = initial_name if initial_name else short_name
        self.name_edit.setText(default_name)
        row1.addWidget(self.name_edit, 2)

        row1.addWidget(QLabel("Qty:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(0, 50)
        self.count_spin.setValue(initial_count)
        self.count_spin.setFixedWidth(50)
        row1.addWidget(self.count_spin)

        self.remove_btn = QPushButton("X")
        self.remove_btn.setFixedSize(24, 24)
        self.remove_btn.setToolTip("Remove from encounter")
        self.remove_btn.setStyleSheet("QPushButton { color: #e74c3c; font-weight: bold; border: 1px solid #555; border-radius: 3px; } QPushButton:hover { background: #c0392b; color: white; }")
        self.remove_btn.clicked.connect(lambda: self.removed.emit())
        row1.addWidget(self.remove_btn)
        fields.addLayout(row1)

        # Row 2: HP, AC, Size, PC
        row2 = QHBoxLayout()
        row2.setSpacing(4)

        row2.addWidget(QLabel("HP:"))
        self.hp_spin = QSpinBox()
        self.hp_spin.setRange(1, 9999)
        self.hp_spin.setValue(initial_hp)
        self.hp_spin.setFixedWidth(55)
        row2.addWidget(self.hp_spin)

        row2.addWidget(QLabel("AC:"))
        self.ac_spin = QSpinBox()
        self.ac_spin.setRange(0, 30)
        self.ac_spin.setValue(initial_ac)
        self.ac_spin.setFixedWidth(45)
        row2.addWidget(self.ac_spin)

        row2.addWidget(QLabel("Size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(20, 400)
        self.size_slider.setValue(initial_size)
        row2.addWidget(self.size_slider, 1)
        self.size_value_label = QLabel(f"{initial_size}%")
        self.size_value_label.setFixedWidth(32)
        self.size_slider.valueChanged.connect(lambda v: self.size_value_label.setText(f"{v}%"))
        row2.addWidget(self.size_value_label)

        self.player_check = QCheckBox("PC")
        self.player_check.setChecked(initial_is_player)
        self.player_check.setToolTip("Player Character")
        row2.addWidget(self.player_check)
        fields.addLayout(row2)

        outer.addLayout(fields, 1)

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
    """Widget for an active party member — preview, name, level, HP, AC, size, familiar, remove."""

    # Class-level list of available familiars (populated once by launcher)
    FAMILIAR_CHOICES = []
    removed = Signal()  # emitted when Remove is clicked

    def __init__(self, token_data: TokenData,
                 initial_name="", initial_level=1, initial_hp=20, initial_ac=12,
                 initial_size=100, initial_familiar=""):
        super().__init__()
        self.token_data = token_data
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(6)

        # Sprite preview thumbnail
        self.preview_label = QLabel()
        pix = QPixmap(token_data.path)
        if not pix.isNull():
            self.preview_label.setPixmap(pix.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.preview_label.setText("?")
        self.preview_label.setFixedSize(74, 74)
        self.preview_label.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
        self.preview_label.setToolTip(token_data.name)
        outer.addWidget(self.preview_label)

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

        self.remove_btn = QPushButton("X")
        self.remove_btn.setFixedSize(24, 24)
        self.remove_btn.setToolTip("Remove from party")
        self.remove_btn.setStyleSheet("QPushButton { color: #e74c3c; font-weight: bold; border: 1px solid #555; border-radius: 3px; } QPushButton:hover { background: #c0392b; color: white; }")
        self.remove_btn.clicked.connect(lambda: self.removed.emit())
        row1.addWidget(self.remove_btn)
        fields.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(4)
        row2.addWidget(QLabel("HP:"))
        self.hp_spin = QSpinBox()
        self.hp_spin.setRange(1, 9999)
        self.hp_spin.setValue(initial_hp)
        self.hp_spin.setFixedWidth(55)
        row2.addWidget(self.hp_spin)

        row2.addWidget(QLabel("AC:"))
        self.ac_spin = QSpinBox()
        self.ac_spin.setRange(0, 30)
        self.ac_spin.setValue(initial_ac)
        self.ac_spin.setFixedWidth(45)
        row2.addWidget(self.ac_spin)

        row2.addWidget(QLabel("Size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(20, 400)
        self.size_slider.setValue(initial_size)
        row2.addWidget(self.size_slider, 1)
        self.size_label = QLabel(f"{initial_size}%")
        self.size_label.setFixedWidth(32)
        self.size_slider.valueChanged.connect(lambda v: self.size_label.setText(f"{v}%"))
        row2.addWidget(self.size_label)

        row2.addWidget(QLabel("Fam:"))
        self.familiar_combo = QComboBox()
        self.familiar_combo.addItem("None", "")
        for fname, fpath in self.FAMILIAR_CHOICES:
            self.familiar_combo.addItem(fname, fpath)
        if initial_familiar:
            idx = self.familiar_combo.findData(initial_familiar)
            if idx >= 0:
                self.familiar_combo.setCurrentIndex(idx)
        self.familiar_combo.setMinimumWidth(100)
        row2.addWidget(self.familiar_combo)
        fields.addLayout(row2)

        outer.addLayout(fields, 1)

    def get_config(self):
        return {
            "enabled": True,
            "name": self.name_edit.text(),
            "level": self.level_spin.value(),
            "hp": self.hp_spin.value(),
            "ac": self.ac_spin.value(),
            "size": self.size_slider.value(),
            "familiar": self.familiar_combo.currentData() or "",
        }


# Display names for compound race tokens
_RACE_DISPLAY = {
    "HalfElf": "Half-Elf",
    "HalfOrc": "Half-Orc",
}
# Reverse lookup: display name -> internal key
_RACE_INTERNAL = {v: k for k, v in _RACE_DISPLAY.items()}

# Known D&D classes for identifying single-word sprites like "Artificer.png"
_KNOWN_CLASSES = {
    "Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk",
    "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard", "Artificer",
}


def _race_display_name(raw):
    """Convert internal race key to display name (e.g. HalfElf -> Half-Elf)."""
    return _RACE_DISPLAY.get(raw, raw)


def _parse_sprite_races_classes(sprites):
    """Parse Race_Class.png filenames into a dict of {(race, cls): [TokenData, ...]}.

    Supports variant numbering: Human_Fighter.png, Human_Fighter2.png, Human_Fighter3.png
    are all grouped under (Human, Fighter).
    Single-word class names like Artificer.png are added as a class available for all races.
    Race display names are cleaned up (HalfElf -> Half-Elf, HalfOrc -> Half-Orc).
    """
    import re
    combos = {}
    races = set()
    classes = set()
    standalone_classes = []  # single-word sprites that are class names
    valid_part = re.compile(r'^([A-Za-z]+)\d*$')

    for sprite in sprites:
        base = os.path.splitext(sprite.name)[0]  # e.g. "Human_Fighter2"
        parts = base.split('_')

        if len(parts) == 2:
            race_m = valid_part.match(parts[0])
            cls_m = valid_part.match(parts[1])
            if race_m and cls_m:
                race = race_m.group(1)
                cls = cls_m.group(1)
                races.add(race)
                classes.add(cls)
                combos.setdefault((race, cls), []).append(sprite)
                continue

        if len(parts) == 1 and valid_part.match(parts[0]):
            name = valid_part.match(parts[0]).group(1)
            if name in _KNOWN_CLASSES:
                # Single-word class (e.g. Artificer.png) — add for all races later
                classes.add(name)
                standalone_classes.append((name, sprite))
            else:
                # Single-word race with no class
                races.add(name)
                combos.setdefault((name, ""), []).append(sprite)
            continue

        # Multi-part race name (e.g. Half_Elf_Fighter if someone names it that way)
        if len(parts) >= 2:
            cls_m = valid_part.match(parts[-1])
            if cls_m and all(valid_part.match(p) for p in parts[:-1]):
                race = ''.join(valid_part.match(p).group(1) for p in parts[:-1])
                cls = cls_m.group(1)
                races.add(race)
                classes.add(cls)
                combos.setdefault((race, cls), []).append(sprite)
                continue

    # Add standalone class sprites (like Artificer) to every race that exists
    for cls_name, sprite in standalone_classes:
        for race in races:
            combos.setdefault((race, cls_name), []).append(sprite)

    # Convert race names to display format
    display_races = sorted(_race_display_name(r) for r in races)
    display_combos = {}
    for (race, cls), sprite_list in combos.items():
        display_combos[(_race_display_name(race), cls)] = sprite_list

    return display_combos, display_races, sorted(classes)


class LauncherWindow(QWidget):
    scanner_updated = Signal()

    def __init__(self, scanner: DNDScanner, on_launch):
        super().__init__()
        self.scanner = scanner
        self.on_launch = on_launch
        self.setWindowTitle("D&D Map Interactive Launcher")
        self.showMaximized()

        self._updating = False
        self.token_rows = {}
        self.player_rows = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── Folder + Map selection (always visible at top) ──
        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Adventure:</b>"))
        self.folder_combo = QComboBox()
        self.folder_combo.setMinimumHeight(30)
        self.folder_combo.currentIndexChanged.connect(self.update_folder_selection)
        top.addWidget(self.folder_combo, 1)
        top.addWidget(QLabel("<b>Map:</b>"))
        self.map_list = QComboBox()
        self.map_list.setMinimumHeight(30)
        self.map_list.currentIndexChanged.connect(self.load_map_config)
        top.addWidget(self.map_list, 1)
        root.addLayout(top)

        # Grid config row
        grid_row = QHBoxLayout()
        grid_row.addWidget(QLabel("Cols:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 200)
        self.width_spin.valueChanged.connect(self._auto_save_config)
        grid_row.addWidget(self.width_spin)
        grid_row.addWidget(QLabel("Rows:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 200)
        self.height_spin.valueChanged.connect(self._auto_save_config)
        grid_row.addWidget(self.height_spin)
        grid_row.addWidget(QLabel("Zoom:"))
        self.grid_scale_slider = QSlider(Qt.Horizontal)
        self.grid_scale_slider.setRange(50, 300)
        self.grid_scale_slider.setValue(100)
        self.grid_scale_slider.valueChanged.connect(self._auto_save_config)
        self.grid_scale_label = QLabel("100%")
        self.grid_scale_slider.valueChanged.connect(lambda v: self.grid_scale_label.setText(f"{v}%"))
        grid_row.addWidget(self.grid_scale_slider, 1)
        grid_row.addWidget(self.grid_scale_label)
        root.addLayout(grid_row)

        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { min-width: 120px; padding: 8px 16px; font-weight: bold; }")
        root.addWidget(self.tabs, 1)

        # --- Tab 1: Encounter Tokens ---
        enc_tab = QWidget()
        enc_layout = QVBoxLayout(enc_tab)
        enc_layout.addWidget(QLabel("Tokens from the encounter folder — set Qty > 0 to include:"))
        self.token_scroll = QScrollArea()
        self.token_scroll.setWidgetResizable(True)
        self.token_container = QWidget()
        self.token_layout = QVBoxLayout(self.token_container)
        self.token_layout.setAlignment(Qt.AlignTop)
        self.token_scroll.setWidget(self.token_container)
        enc_layout.addWidget(self.token_scroll)
        self.tabs.addTab(enc_tab, "Encounter Tokens")

        # --- Tab 2: Monster Library ---
        mon_tab = QWidget()
        mon_layout = QVBoxLayout(mon_tab)
        mon_layout.addWidget(QLabel("Click a monster to add it to the <b>Encounter Tokens</b> tab:"))
        self.monster_search = QLineEdit()
        self.monster_search.setPlaceholderText("Search monsters...")
        self.monster_search.textChanged.connect(self._filter_monster_grid)
        mon_layout.addWidget(self.monster_search)
        self.monster_scroll = QScrollArea()
        self.monster_scroll.setWidgetResizable(True)
        self.monster_container = QWidget()
        self.monster_grid = QGridLayout(self.monster_container)
        self.monster_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.monster_grid.setSpacing(8)
        self.monster_scroll.setWidget(self.monster_container)
        mon_layout.addWidget(self.monster_scroll)
        self._monster_grid_widgets = []  # [(wrapper_widget, token_data), ...]
        self.tabs.addTab(mon_tab, "Monster Library")

        # --- Tab 3: Map Library ---
        map_tab = QWidget()
        map_layout = QVBoxLayout(map_tab)

        # Category filter + search
        map_filter_row = QHBoxLayout()
        map_filter_row.addWidget(QLabel("<b>Location:</b>"))
        self.map_category_combo = QComboBox()
        self.map_category_combo.addItem("All")
        self.map_category_combo.setMinimumWidth(120)
        self.map_category_combo.currentIndexChanged.connect(self._filter_map_grid)
        map_filter_row.addWidget(self.map_category_combo)

        self.map_search = QLineEdit()
        self.map_search.setPlaceholderText("Search maps...")
        self.map_search.textChanged.connect(self._filter_map_grid)
        map_filter_row.addWidget(self.map_search, 1)
        map_layout.addLayout(map_filter_row)

        map_layout.addWidget(QLabel("Click a map to use it for the current encounter:"))
        self.map_lib_scroll = QScrollArea()
        self.map_lib_scroll.setWidgetResizable(True)
        self.map_lib_container = QWidget()
        self.map_lib_grid = QGridLayout(self.map_lib_container)
        self.map_lib_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.map_lib_grid.setSpacing(8)
        self.map_lib_scroll.setWidget(self.map_lib_container)
        map_layout.addWidget(self.map_lib_scroll)
        self._map_grid_widgets = []  # [(wrapper, category, name, path), ...]
        self.tabs.addTab(map_tab, "Map Library")

        # --- Tab 4: Party / Teams ---
        party_tab = QWidget()
        party_layout = QVBoxLayout(party_tab)

        # Team picker row
        team_row = QHBoxLayout()
        team_row.addWidget(QLabel("<b>Team:</b>"))
        self.team_combo = QComboBox()
        self.team_combo.setMinimumWidth(150)
        self.team_combo.currentIndexChanged.connect(self._on_team_selected)
        team_row.addWidget(self.team_combo, 1)
        self.save_team_btn = QPushButton("Save")
        self.save_team_btn.clicked.connect(self._save_team)
        team_row.addWidget(self.save_team_btn)
        self.save_as_team_btn = QPushButton("Save As...")
        self.save_as_team_btn.clicked.connect(self._save_team_as)
        team_row.addWidget(self.save_as_team_btn)
        self.delete_team_btn = QPushButton("Delete")
        self.delete_team_btn.clicked.connect(self._delete_team)
        team_row.addWidget(self.delete_team_btn)
        party_layout.addLayout(team_row)

        # ── Race / Class picker ──
        picker_row = QHBoxLayout()
        picker_row.addWidget(QLabel("<b>Race:</b>"))
        self.race_combo = QComboBox()
        self.race_combo.setMinimumWidth(120)
        self.race_combo.currentIndexChanged.connect(self._on_race_changed)
        picker_row.addWidget(self.race_combo)
        picker_row.addWidget(QLabel("<b>Class:</b>"))
        self.class_combo = QComboBox()
        self.class_combo.setMinimumWidth(120)
        self.class_combo.currentIndexChanged.connect(self._update_sprite_preview)
        picker_row.addWidget(self.class_combo)

        self.sprite_preview = QLabel()
        self.sprite_preview.setFixedSize(82, 82)
        self.sprite_preview.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
        self.sprite_preview.setToolTip("Click to cycle sprite variants")
        self.sprite_preview.mousePressEvent = self._on_sprite_preview_clicked
        picker_row.addWidget(self.sprite_preview)

        self.add_player_btn = QPushButton("+ Add to Party")
        self.add_player_btn.setStyleSheet("QPushButton { background: #2980b9; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px; } QPushButton:hover { background: #3498db; }")
        self.add_player_btn.clicked.connect(self._add_player_from_picker)
        picker_row.addWidget(self.add_player_btn)
        picker_row.addStretch()
        party_layout.addLayout(picker_row)

        # ── Active Party list ──
        party_layout.addWidget(QLabel("Active party members:"))
        self.player_scroll = QScrollArea()
        self.player_scroll.setWidgetResizable(True)
        self.player_container = QWidget()
        self.player_layout = QVBoxLayout(self.player_container)
        self.player_layout.setAlignment(Qt.AlignTop)
        self.player_scroll.setWidget(self.player_container)
        party_layout.addWidget(self.player_scroll)
        self.tabs.addTab(party_tab, "Party / Teams")

        # Sprite data cache (populated in _rebuild_player_sprites)
        self._sprite_combos = {}  # (race, cls) -> [TokenData, ...]
        self._sprite_variant_idx = {}  # (race, cls) -> int
        self._sprite_races = []
        self._sprite_classes = []

        # ── Launch button (always visible) ──
        self.launch_btn = QPushButton("LAUNCH SESSION")
        self.launch_btn.clicked.connect(self.handle_launch)
        self.launch_btn.setMinimumHeight(50)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white;
                font-weight: bold; font-size: 15px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        root.addWidget(self.launch_btn)

        # Debounce timer for scanner updates
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.refresh_folders)

        self.scanner_updated.connect(lambda: self.refresh_timer.start(500))
        self.scanner.on_update_callback = lambda: self.scanner_updated.emit()

        # Initial trigger (deferred so window shows first)
        QTimer.singleShot(0, self.refresh_folders)

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
        self._rebuild_map_library()
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

        # 4. Create new rows with saved creature stats (encounter folder tokens)
        encounter_token_names = set()
        for t in folder_data.tokens:
            encounter_token_names.add(t.name)
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
            self._connect_token_row(row, t)
            self.token_layout.addWidget(row)
            self.token_rows[t] = row

        # 4b. Restore saved library monsters (from monster_tokens/) into encounter tab
        for token in self.scanner.monster_tokens:
            if token.name in saved_tokens and token.name not in encounter_token_names:
                cfg = saved_tokens[token.name]
                if cfg.get("count", 0) > 0:
                    row = TokenConfigRow(
                        token,
                        initial_count=cfg.get("count", 0),
                        initial_size=cfg.get("size", 100),
                        initial_name=cfg.get("name", ""),
                        initial_hp=cfg.get("hp", 10),
                        initial_ac=cfg.get("ac", 10),
                        initial_is_player=cfg.get("is_player", False),
                    )
                    self._connect_token_row(row, token)
                    self.token_layout.addWidget(row)
                    self.token_rows[token] = row

        self._updating = False

        # 5. Rebuild monster library grid and player sprites with per-encounter config
        self._rebuild_monster_library()
        self._rebuild_player_sprites()

        # 6. Trigger map config load for the first map
        if self.map_list.count() > 0:
            self.map_list.setCurrentIndex(0)

    @Slot(int)
    def load_map_config(self, index):
        if self._updating or index < 0: return
        
        folder_name = self.folder_combo.currentText().strip()
        if not folder_name or folder_name not in self.scanner.folders: return
            
        map_item = self.map_list.itemText(index) if index >= 0 else None
        if not map_item: return
        
        folder_data = self.scanner.folders[folder_name]
        try:
            map_data = next(m for m in folder_data.maps if m.name == map_item)
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
        """Rebuild the monster library as a searchable grid of clickable thumbnails."""
        # Clear existing grid widgets
        for wrapper, _token in self._monster_grid_widgets:
            wrapper.setParent(None)
            wrapper.deleteLater()
        self._monster_grid_widgets = []

        if not self.scanner.monster_tokens:
            placeholder = QLabel("<i>No monsters. Add PNGs to monster_tokens/ folder.</i>")
            placeholder.setStyleSheet("color: #666; padding: 10px;")
            self.monster_grid.addWidget(placeholder, 0, 0)
            self._monster_grid_widgets.append((placeholder, None))
            return

        cols = 6
        for i, token in enumerate(self.scanner.monster_tokens):
            wrapper = QWidget()
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(2, 2, 2, 2)
            wrapper_layout.setSpacing(2)
            wrapper_layout.setAlignment(Qt.AlignCenter)

            btn = QPushButton()
            pix = QPixmap(token.path)
            if not pix.isNull():
                btn.setIcon(QIcon(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                btn.setIconSize(QSize(64, 64))
            btn.setFixedSize(70, 70)
            btn.setStyleSheet("QPushButton { border: 1px solid #555; border-radius: 4px; } QPushButton:hover { border: 2px solid #2980b9; background: #2c3e50; }")
            btn.setToolTip(f"Click to add {extract_creature_name(token.name)} to encounter")
            btn.clicked.connect(lambda checked=False, t=token: self._add_monster_to_encounter(t))
            wrapper_layout.addWidget(btn)

            name_label = QLabel(extract_creature_name(token.name))
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setWordWrap(True)
            name_label.setFixedWidth(76)
            name_label.setStyleSheet("font-size: 10px;")
            wrapper_layout.addWidget(name_label)

            row_idx = i // cols
            col_idx = i % cols
            self.monster_grid.addWidget(wrapper, row_idx, col_idx)
            self._monster_grid_widgets.append((wrapper, token))

    def _filter_monster_grid(self, text):
        """Show/hide monster grid thumbnails based on search text."""
        text = text.lower().strip()
        for wrapper, token in self._monster_grid_widgets:
            if token is None:
                # Placeholder label
                wrapper.setVisible(not text)
                continue
            name = extract_creature_name(token.name).lower()
            wrapper.setVisible(text in name if text else True)

    def _add_monster_to_encounter(self, token):
        """Add a monster from the library as a TokenConfigRow in the Encounter Tokens tab."""
        # Check if already added (by path, since token_rows keys are TokenData)
        for existing_token in self.token_rows:
            if existing_token.path == token.path:
                # Already exists — just increment count
                self.token_rows[existing_token].count_spin.setValue(
                    self.token_rows[existing_token].count_spin.value() + 1
                )
                self.tabs.setCurrentIndex(0)  # Switch to Encounter Tokens tab
                return

        # Load saved config for this monster if available
        saved_cfg = {}
        folder_name = self.folder_combo.currentText().strip()
        if folder_name and folder_name in self.scanner.folders:
            folder_data = self.scanner.folders[folder_name]
            config_path = os.path.join(folder_data.path, "config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        saved_cfg = json.load(f).get("tokens", {}).get(token.name, {})
                except:
                    pass

        row = TokenConfigRow(
            token,
            initial_count=saved_cfg.get("count", 1),
            initial_size=saved_cfg.get("size", 100),
            initial_name=saved_cfg.get("name", ""),
            initial_hp=saved_cfg.get("hp", 10),
            initial_ac=saved_cfg.get("ac", 10),
            initial_is_player=False,
        )
        self._connect_token_row(row, token)
        self.token_layout.addWidget(row)
        self.token_rows[token] = row
        self.tabs.setCurrentIndex(0)  # Switch to Encounter Tokens tab
        self._auto_save_config()

    def _rebuild_map_library(self):
        """Build the map library grid from map_library/ folder."""
        # Clear existing
        for wrapper, *_ in self._map_grid_widgets:
            wrapper.setParent(None)
            wrapper.deleteLater()
        self._map_grid_widgets = []

        map_lib_path = os.path.join(self.scanner.base_path, "map_library")
        if not os.path.isdir(map_lib_path):
            placeholder = QLabel("<i>No map library. Create a map_library/ folder with subfolders.</i>")
            placeholder.setStyleSheet("color: #666; padding: 10px;")
            self.map_lib_grid.addWidget(placeholder, 0, 0)
            self._map_grid_widgets.append((placeholder, "", "", ""))
            return

        # Collect all maps from subfolders
        categories = set()
        all_maps = []
        for category in sorted(os.listdir(map_lib_path)):
            cat_path = os.path.join(map_lib_path, category)
            if not os.path.isdir(cat_path):
                continue
            categories.add(category)
            for fname in sorted(os.listdir(cat_path)):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                    all_maps.append((category, fname, os.path.join(cat_path, fname)))

        # Populate category filter
        self.map_category_combo.blockSignals(True)
        current_cat = self.map_category_combo.currentText()
        self.map_category_combo.clear()
        self.map_category_combo.addItem("All")
        for cat in sorted(categories):
            self.map_category_combo.addItem(cat)
        if current_cat and self.map_category_combo.findText(current_cat) >= 0:
            self.map_category_combo.setCurrentText(current_cat)
        self.map_category_combo.blockSignals(False)

        if not all_maps:
            placeholder = QLabel("<i>No maps found. Add JPG/PNG files to map_library/ subfolders.</i>")
            placeholder.setStyleSheet("color: #666; padding: 10px;")
            self.map_lib_grid.addWidget(placeholder, 0, 0)
            self._map_grid_widgets.append((placeholder, "", "", ""))
            return

        cols = 4
        for i, (category, fname, full_path) in enumerate(all_maps):
            wrapper = QWidget()
            wl = QVBoxLayout(wrapper)
            wl.setContentsMargins(2, 2, 2, 2)
            wl.setSpacing(2)
            wl.setAlignment(Qt.AlignCenter)

            btn = QPushButton()
            pix = QPixmap(full_path)
            if not pix.isNull():
                btn.setIcon(QIcon(pix.scaled(140, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                btn.setIconSize(QSize(140, 100))
            btn.setFixedSize(148, 108)
            btn.setStyleSheet("QPushButton { border: 1px solid #555; border-radius: 4px; } QPushButton:hover { border: 2px solid #2980b9; background: #2c3e50; }")
            display_name = os.path.splitext(fname)[0]
            btn.setToolTip(f"[{category}] {display_name}\nClick to use this map")
            btn.clicked.connect(lambda checked=False, p=full_path, n=fname: self._use_library_map(p, n))
            wl.addWidget(btn)

            label = QLabel(display_name[:25])
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            label.setFixedWidth(148)
            label.setStyleSheet("font-size: 9px;")
            label.setToolTip(f"[{category}] {display_name}")
            wl.addWidget(label)

            self.map_lib_grid.addWidget(wrapper, i // cols, i % cols)
            self._map_grid_widgets.append((wrapper, category, display_name.lower(), full_path))

    def _filter_map_grid(self, *args):
        """Filter map grid by category and search text."""
        cat = self.map_category_combo.currentText()
        text = self.map_search.text().lower().strip()
        for wrapper, category, name, path in self._map_grid_widgets:
            if not path:  # placeholder
                wrapper.setVisible(not text and cat == "All")
                continue
            cat_match = (cat == "All" or cat == category)
            text_match = (not text or text in name)
            wrapper.setVisible(cat_match and text_match)

    def _use_library_map(self, source_path, filename):
        """Copy a library map to the current encounter folder and select it."""
        folder_name = self.folder_combo.currentText().strip()
        if not folder_name or folder_name not in self.scanner.folders:
            QMessageBox.warning(self, "No Encounter", "Select an encounter folder first.")
            return

        folder_data = self.scanner.folders[folder_name]
        dest_path = os.path.join(folder_data.path, filename)

        if os.path.exists(dest_path):
            # Already exists — just select it
            idx = self.map_list.findText(filename)
            if idx >= 0:
                self.map_list.setCurrentIndex(idx)
            return

        shutil.copy2(source_path, dest_path)
        # Rescan and select the new map
        self.scanner.scan()
        self.refresh_folders()
        QTimer.singleShot(200, lambda: self._select_map(filename))

    def _select_map(self, filename):
        idx = self.map_list.findText(filename)
        if idx >= 0:
            self.map_list.setCurrentIndex(idx)

    def _connect_token_row(self, row, token):
        """Connect auto-save and remove signals for a TokenConfigRow."""
        row.count_spin.valueChanged.connect(self._auto_save_config)
        row.size_slider.valueChanged.connect(self._auto_save_config)
        row.name_edit.textChanged.connect(self._auto_save_config)
        row.hp_spin.valueChanged.connect(self._auto_save_config)
        row.ac_spin.valueChanged.connect(self._auto_save_config)
        row.player_check.toggled.connect(self._auto_save_config)
        row.removed.connect(lambda t=token: self._remove_token_from_encounter(t))

    def _remove_token_from_encounter(self, token):
        """Remove a token row from the Encounter Tokens tab."""
        row = self.token_rows.pop(token, None)
        if row:
            self.token_layout.removeWidget(row)
            row.setParent(None)
            row.deleteLater()
            self._auto_save_config()

    def _rebuild_player_sprites(self):
        """Rebuild the Race/Class picker and active party from scanner."""
        # Clear existing party rows
        while self.player_layout.count():
            item = self.player_layout.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.setParent(None)
                w.deleteLater()
        self.player_rows = {}

        # Build familiar choices from summon_tokens/ folder
        familiar_choices = []
        summon_dir = os.path.join(self.scanner.base_path, "summon_tokens")
        if os.path.isdir(summon_dir):
            for png in sorted(globfiles(os.path.join(summon_dir, "*.png"))):
                fname = os.path.splitext(os.path.basename(png))[0].replace('_', ' ')
                familiar_choices.append((fname, png))
        PlayerSpriteRow.FAMILIAR_CHOICES = familiar_choices

        # Parse sprite filenames into race/class combos
        if self.scanner.player_sprites:
            self._sprite_combos, self._sprite_races, self._sprite_classes = \
                _parse_sprite_races_classes(self.scanner.player_sprites)
        else:
            self._sprite_combos, self._sprite_races, self._sprite_classes = {}, [], []

        # Populate race combo, then class combo filtered by race
        self.race_combo.blockSignals(True)
        self.race_combo.clear()
        for r in self._sprite_races:
            self.race_combo.addItem(r)
        self.race_combo.blockSignals(False)
        self._update_class_combo()
        self._update_sprite_preview()

        # Load saved player config and add enabled players to the party
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

        # Re-add enabled players from saved config
        for sprite_name, cfg in saved_players.items():
            if cfg.get("enabled", False):
                # Find matching TokenData
                sprite = next((s for s in self.scanner.player_sprites if s.name == sprite_name), None)
                if sprite:
                    self._add_player_row(sprite, cfg)

    def _on_race_changed(self):
        """When race changes, update class list and preview."""
        self._update_class_combo()
        self._update_sprite_preview()

    def _update_class_combo(self):
        """Rebuild class combo to only show classes available for the selected race."""
        race = self.race_combo.currentText()
        available_classes = sorted(
            cls for (r, cls) in self._sprite_combos if r == race and cls
        )
        prev_cls = self.class_combo.currentText()
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        for c in available_classes:
            self.class_combo.addItem(c)
        # Restore previous selection if still available
        if prev_cls and self.class_combo.findText(prev_cls) >= 0:
            self.class_combo.setCurrentText(prev_cls)
        self.class_combo.blockSignals(False)

    def _update_sprite_preview(self):
        """Update the preview thumbnail based on current Race/Class selection and variant index."""
        race = self.race_combo.currentText()
        cls = self.class_combo.currentText()
        key = (race, cls)
        sprite_list = self._sprite_combos.get(key, [])
        if sprite_list:
            idx = self._sprite_variant_idx.get(key, 0) % len(sprite_list)
            sprite = sprite_list[idx]
            pix = QPixmap(sprite.path)
            if not pix.isNull():
                self.sprite_preview.setPixmap(pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                variant_info = f" (variant {idx + 1}/{len(sprite_list)})" if len(sprite_list) > 1 else ""
                self.sprite_preview.setToolTip(f"{sprite.name}{variant_info}\nClick to cycle variants")
                return
        self.sprite_preview.clear()
        self.sprite_preview.setText("?")
        self.sprite_preview.setToolTip("No sprite for this combo")

    def _on_sprite_preview_clicked(self, event):
        """Cycle to the next sprite variant when the preview is clicked."""
        race = self.race_combo.currentText()
        cls = self.class_combo.currentText()
        key = (race, cls)
        sprite_list = self._sprite_combos.get(key, [])
        if len(sprite_list) > 1:
            current_idx = self._sprite_variant_idx.get(key, 0)
            self._sprite_variant_idx[key] = (current_idx + 1) % len(sprite_list)
            self._update_sprite_preview()

    def _add_player_from_picker(self):
        """Add the currently selected Race/Class combo to the active party."""
        race = self.race_combo.currentText()
        cls = self.class_combo.currentText()
        key = (race, cls)
        sprite_list = self._sprite_combos.get(key, [])
        if not sprite_list:
            return
        idx = self._sprite_variant_idx.get(key, 0) % len(sprite_list)
        sprite = sprite_list[idx]
        # Don't add duplicates
        if sprite in self.player_rows:
            return
        self._add_player_row(sprite, {})
        self._auto_save_config()

    def _add_player_row(self, sprite, cfg):
        """Add a PlayerSpriteRow for the given sprite with config."""
        row = PlayerSpriteRow(
            sprite,
            initial_name=cfg.get("name", ""),
            initial_level=cfg.get("level", 1),
            initial_hp=cfg.get("hp", 20),
            initial_ac=cfg.get("ac", 12),
            initial_size=cfg.get("size", 100),
            initial_familiar=cfg.get("familiar", ""),
        )
        row.removed.connect(lambda s=sprite: self._remove_player(s))
        row.name_edit.textChanged.connect(self._auto_save_config)
        row.level_spin.valueChanged.connect(self._auto_save_config)
        row.hp_spin.valueChanged.connect(self._auto_save_config)
        row.ac_spin.valueChanged.connect(self._auto_save_config)
        row.size_slider.valueChanged.connect(self._auto_save_config)
        row.familiar_combo.currentIndexChanged.connect(self._auto_save_config)
        self.player_layout.addWidget(row)
        self.player_rows[sprite] = row

    def _remove_player(self, sprite):
        """Remove a player from the active party."""
        row = self.player_rows.pop(sprite, None)
        if row:
            self.player_layout.removeWidget(row)
            row.setParent(None)
            row.deleteLater()
            self._auto_save_config()

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
        """Load a team's config — clear party, add enabled members."""
        if self._updating:
            return
        team_name = self.team_combo.currentText()
        if team_name == "(No team)" or not team_name:
            return
        teams = self._load_teams()
        team = teams.get(team_name, {})
        if not team:
            return
        # Clear current party
        self._updating = True
        for sprite in list(self.player_rows.keys()):
            self._remove_player(sprite)
        # Add team members
        for sprite_name, cfg in team.items():
            if cfg.get("enabled", False):
                sprite = next((s for s in self.scanner.player_sprites if s.name == sprite_name), None)
                if sprite:
                    self._add_player_row(sprite, cfg)
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
        map_item = self.map_list.currentText()
        if not folder_name or not map_item or folder_name not in self.scanner.folders:
            return
            
        folder_data = self.scanner.folders[folder_name]
        map_name = map_item
        
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
                "player_sprites": player_configs,
            }
            # Preserve creatures saved by the viewer
            if "creatures" in existing_cfg:
                full_cfg["creatures"] = existing_cfg["creatures"]
            self.scanner.save_folder_config(folder_data.path, full_cfg)
        except StopIteration: pass

    def handle_launch(self):
        folder_name = self.folder_combo.currentText().strip()
        map_item = self.map_list.currentText()
        
        if not folder_name or not map_item: return
        if folder_name not in self.scanner.folders: return
        folder_data = self.scanner.folders[folder_name]
        
        try:
            map_name = map_item
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
