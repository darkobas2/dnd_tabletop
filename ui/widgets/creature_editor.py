"""Creature editor widget — edit creature stat blocks and pick tokens."""

import os
from glob import glob as globfiles
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QLineEdit, QSpinBox, QComboBox, QFrame,
                                QFormLayout, QCheckBox, QDialog, QDialogButtonBox,
                                QTextEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QIcon
from core.name_utils import extract_creature_name


def _collect_tokens(base_path=None):
    """Collect all tokens from monster_tokens/ and summon_tokens/ folders.
    Returns list of (display_name, full_path) sorted by name.
    """
    tokens = []
    if base_path is None:
        # Try to find the project root by walking up from this file
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    for folder in ("monster_tokens", "summon_tokens", "player_sprites"):
        folder_path = os.path.join(base_path, folder)
        if os.path.isdir(folder_path):
            for png in sorted(globfiles(os.path.join(folder_path, "*.png"))):
                name = os.path.splitext(os.path.basename(png))[0].replace('_', ' ')
                prefix = folder.replace('_tokens', '').replace('_sprites', '').capitalize()
                tokens.append((f"[{prefix}] {name}", png))
    return tokens


class CreatureEditor(QDialog):
    """Dialog for editing a creature's stats."""

    creature_updated = Signal(object)  # Emits updated CreatureState

    def __init__(self, creature=None, parent=None):
        super().__init__(parent)
        self.creature = creature
        self.setWindowTitle("Edit Creature" if creature else "New Creature")
        self.setMinimumWidth(450)
        self._setup_ui()
        if creature:
            self._load_creature()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Creature name")
        form.addRow("Name:", self.name_edit)

        # HP row
        hp_layout = QHBoxLayout()
        self.hp_spin = QSpinBox()
        self.hp_spin.setRange(0, 9999)
        hp_layout.addWidget(self.hp_spin)
        hp_layout.addWidget(QLabel("/"))
        self.hp_max_spin = QSpinBox()
        self.hp_max_spin.setRange(1, 9999)
        self.hp_max_spin.setValue(10)
        hp_layout.addWidget(self.hp_max_spin)
        hp_layout.addWidget(QLabel("Temp:"))
        self.hp_temp_spin = QSpinBox()
        self.hp_temp_spin.setRange(0, 999)
        hp_layout.addWidget(self.hp_temp_spin)
        form.addRow("HP:", hp_layout)

        self.ac_spin = QSpinBox()
        self.ac_spin.setRange(0, 30)
        self.ac_spin.setValue(10)
        form.addRow("AC:", self.ac_spin)

        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(0, 200)
        self.speed_spin.setValue(30)
        self.speed_spin.setSuffix(" ft")
        form.addRow("Speed:", self.speed_spin)

        self.init_mod_spin = QSpinBox()
        self.init_mod_spin.setRange(-10, 20)
        self.init_mod_spin.setValue(0)
        form.addRow("Init Mod:", self.init_mod_spin)

        self.is_player_check = QCheckBox("Player Character")
        form.addRow("", self.is_player_check)

        self.is_visible_check = QCheckBox("Visible to players")
        self.is_visible_check.setChecked(True)
        form.addRow("", self.is_visible_check)

        # Token picker — combo with preview
        token_layout = QHBoxLayout()
        self.token_preview = QLabel()
        self.token_preview.setFixedSize(50, 50)
        self.token_preview.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
        token_layout.addWidget(self.token_preview)

        self.token_combo = QComboBox()
        self.token_combo.setMinimumWidth(250)
        self.token_combo.addItem("(none)", "")
        self._available_tokens = _collect_tokens()
        for display_name, path in self._available_tokens:
            pix = QPixmap(path)
            if not pix.isNull():
                icon = QIcon(pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.token_combo.addItem(icon, display_name, path)
            else:
                self.token_combo.addItem(display_name, path)
        self.token_combo.currentIndexChanged.connect(self._on_token_changed)
        token_layout.addWidget(self.token_combo, 1)
        form.addRow("Token:", token_layout)

        self.token_scale_spin = QSpinBox()
        self.token_scale_spin.setRange(20, 400)
        self.token_scale_spin.setValue(100)
        self.token_scale_spin.setSuffix("%")
        form.addRow("Token Scale:", self.token_scale_spin)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Notes...")
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_token_changed(self, index):
        """Update preview when token selection changes."""
        path = self.token_combo.currentData()
        if path:
            pix = QPixmap(path)
            if not pix.isNull():
                self.token_preview.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        self.token_preview.clear()

    def _load_creature(self):
        c = self.creature
        self.name_edit.setText(c.name)
        self.hp_spin.setValue(c.hp)
        self.hp_max_spin.setValue(c.hp_max)
        self.hp_temp_spin.setValue(c.hp_temp)
        self.ac_spin.setValue(c.ac)
        self.speed_spin.setValue(c.speed)
        self.init_mod_spin.setValue(c.initiative_modifier)
        self.is_player_check.setChecked(c.is_player)
        self.is_visible_check.setChecked(c.is_visible)
        # Select matching token in combo
        if c.token_path:
            idx = self.token_combo.findData(c.token_path)
            if idx >= 0:
                self.token_combo.setCurrentIndex(idx)
            else:
                # Path not in combo — add it as a custom entry
                name = os.path.splitext(os.path.basename(c.token_path))[0].replace('_', ' ')
                pix = QPixmap(c.token_path)
                if not pix.isNull():
                    self.token_combo.addItem(QIcon(pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)),
                                             f"[Custom] {name}", c.token_path)
                else:
                    self.token_combo.addItem(f"[Custom] {name}", c.token_path)
                self.token_combo.setCurrentIndex(self.token_combo.count() - 1)
        self.token_scale_spin.setValue(int(c.token_scale * 100))
        self.notes_edit.setPlainText(c.notes)

    def _apply(self):
        if not self.creature:
            from core.game_state import CreatureState
            self.creature = CreatureState(
                name=self.name_edit.text() or "Unnamed",
                hp=self.hp_spin.value(),
                hp_max=self.hp_max_spin.value(),
            )

        self.creature.name = self.name_edit.text() or "Unnamed"
        self.creature.hp = self.hp_spin.value()
        self.creature.hp_max = self.hp_max_spin.value()
        self.creature.hp_temp = self.hp_temp_spin.value()
        self.creature.ac = self.ac_spin.value()
        self.creature.speed = self.speed_spin.value()
        self.creature.initiative_modifier = self.init_mod_spin.value()
        self.creature.is_player = self.is_player_check.isChecked()
        self.creature.is_visible = self.is_visible_check.isChecked()
        self.creature.token_path = self.token_combo.currentData() or ""
        self.creature.token_scale = self.token_scale_spin.value() / 100.0
        self.creature.notes = self.notes_edit.toPlainText()

        self.creature_updated.emit(self.creature)
        self.accept()

    def get_creature(self):
        return self.creature
