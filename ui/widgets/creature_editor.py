"""Creature editor widget — edit creature stat blocks and manage tokens."""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QLineEdit, QSpinBox, QComboBox, QFrame,
                                QFormLayout, QCheckBox, QDialog, QDialogButtonBox,
                                QTextEdit, QFileDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


SIZE_CATEGORIES = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]


class CreatureEditor(QDialog):
    """Dialog for editing a creature's stats."""

    creature_updated = Signal(object)  # Emits updated CreatureState

    def __init__(self, creature=None, parent=None):
        super().__init__(parent)
        self.creature = creature
        self.setWindowTitle("Edit Creature" if creature else "New Creature")
        self.setMinimumWidth(400)
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

        self.size_combo = QComboBox()
        self.size_combo.addItems(SIZE_CATEGORIES)
        self.size_combo.setCurrentText("Medium")
        form.addRow("Size:", self.size_combo)

        self.is_player_check = QCheckBox("Player Character")
        form.addRow("", self.is_player_check)

        self.is_visible_check = QCheckBox("Visible to players")
        self.is_visible_check.setChecked(True)
        form.addRow("", self.is_visible_check)

        self.token_path_edit = QLineEdit()
        self.token_path_edit.setPlaceholderText("Token image path")
        token_layout = QHBoxLayout()
        token_layout.addWidget(self.token_path_edit)
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(60)
        browse_btn.clicked.connect(self._browse_token)
        token_layout.addWidget(browse_btn)
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

    def _browse_token(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Token Image", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.token_path_edit.setText(path)

    def _load_creature(self):
        c = self.creature
        self.name_edit.setText(c.name)
        self.hp_spin.setValue(c.hp)
        self.hp_max_spin.setValue(c.hp_max)
        self.hp_temp_spin.setValue(c.hp_temp)
        self.ac_spin.setValue(c.ac)
        self.speed_spin.setValue(c.speed)
        self.init_mod_spin.setValue(c.initiative_modifier)
        self.size_combo.setCurrentText(c.size_category)
        self.is_player_check.setChecked(c.is_player)
        self.is_visible_check.setChecked(c.is_visible)
        self.token_path_edit.setText(c.token_path)
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
        self.creature.size_category = self.size_combo.currentText()
        self.creature.is_player = self.is_player_check.isChecked()
        self.creature.is_visible = self.is_visible_check.isChecked()
        self.creature.token_path = self.token_path_edit.text()
        self.creature.token_scale = self.token_scale_spin.value() / 100.0
        self.creature.notes = self.notes_edit.toPlainText()

        self.creature_updated.emit(self.creature)
        self.accept()

    def get_creature(self):
        return self.creature
