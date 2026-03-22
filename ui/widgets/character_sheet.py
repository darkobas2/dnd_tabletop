"""Full D&D 5e character sheet editor dialog."""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                                QWidget, QFormLayout, QLabel, QSpinBox, QComboBox,
                                QLineEdit, QCheckBox, QTextEdit, QPushButton,
                                QGridLayout, QGroupBox, QScrollArea, QFrame)
from PySide6.QtCore import Qt

from core.character import (
    ABILITIES, ABILITY_NAMES, SKILLS, CLASSES, RACES,
    ability_modifier, proficiency_bonus, get_spell_slots,
    get_hit_die, get_save_proficiencies, get_casting_ability,
    calc_spell_save_dc, calc_spell_attack, new_character_sheet,
)


class CharacterSheetDialog(QDialog):
    """Tabbed character sheet editor for player characters."""

    def __init__(self, creature, parent=None):
        super().__init__(parent)
        self.creature = creature
        self.sheet = creature.character_sheet or new_character_sheet()
        self.setWindowTitle(f"Character Sheet: {creature.name}")
        self.setMinimumSize(650, 700)

        layout = QVBoxLayout(self)

        # Character name + class/race header
        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Name:</b>"))
        self.name_edit = QLineEdit(creature.name)
        self.name_edit.setMinimumWidth(150)
        header.addWidget(self.name_edit, 1)

        header.addWidget(QLabel("Race:"))
        self.race_combo = QComboBox()
        self.race_combo.addItems(sorted(RACES.keys()))
        self.race_combo.setCurrentText(self.sheet.get("race", "Human"))
        header.addWidget(self.race_combo)

        header.addWidget(QLabel("Class:"))
        self.class_combo = QComboBox()
        self.class_combo.addItems(sorted(CLASSES.keys()))
        self.class_combo.setCurrentText(self.sheet.get("character_class", "Fighter"))
        self.class_combo.currentTextChanged.connect(self._on_class_changed)
        header.addWidget(self.class_combo)

        header.addWidget(QLabel("Level:"))
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 20)
        self.level_spin.setValue(self.sheet.get("level", 1))
        self.level_spin.valueChanged.connect(self._update_derived)
        header.addWidget(self.level_spin)

        layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_stats_tab(), "Ability Scores")
        self.tabs.addTab(self._build_combat_tab(), "Combat")
        self.tabs.addTab(self._build_skills_tab(), "Skills")
        self.tabs.addTab(self._build_spells_tab(), "Spells")
        self.tabs.addTab(self._build_notes_tab(), "Notes & Equipment")
        layout.addWidget(self.tabs)

        # Derived stats display
        self.derived_label = QLabel()
        self.derived_label.setStyleSheet("background: #2a2a3e; color: #ddd; padding: 6px; border-radius: 4px;")
        layout.addWidget(self.derived_label)

        # Buttons
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.setStyleSheet("font-weight: bold; padding: 8px 20px;")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self._update_derived()

    def _build_stats_tab(self):
        """Ability scores tab with 6 stats and modifiers."""
        widget = QWidget()
        layout = QGridLayout(widget)

        scores = self.sheet.get("ability_scores", {})
        self.ability_spins = {}
        self.mod_labels = {}

        for i, ab in enumerate(ABILITIES):
            col = i % 3
            row_base = (i // 3) * 3

            group = QGroupBox(ABILITY_NAMES[ab])
            group.setStyleSheet("QGroupBox { font-weight: bold; }")
            gl = QVBoxLayout(group)

            spin = QSpinBox()
            spin.setRange(1, 30)
            spin.setValue(scores.get(ab, 10))
            spin.setMinimumHeight(35)
            spin.setStyleSheet("font-size: 16px; font-weight: bold;")
            spin.valueChanged.connect(self._update_derived)
            gl.addWidget(spin)

            mod_label = QLabel()
            mod_label.setAlignment(Qt.AlignCenter)
            mod_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #f39c12;")
            gl.addWidget(mod_label)

            self.ability_spins[ab] = spin
            self.mod_labels[ab] = mod_label
            layout.addWidget(group, row_base, col)

        layout.setRowStretch(6, 1)
        return widget

    def _build_combat_tab(self):
        """Combat stats: HP, AC, speed, initiative, saves."""
        widget = QWidget()
        layout = QFormLayout(widget)

        self.hp_spin = QSpinBox()
        self.hp_spin.setRange(1, 9999)
        self.hp_spin.setValue(self.creature.hp)
        layout.addRow("Current HP:", self.hp_spin)

        self.hp_max_spin = QSpinBox()
        self.hp_max_spin.setRange(1, 9999)
        self.hp_max_spin.setValue(self.creature.hp_max)
        layout.addRow("Max HP:", self.hp_max_spin)

        self.ac_spin = QSpinBox()
        self.ac_spin.setRange(0, 30)
        self.ac_spin.setValue(self.creature.ac)
        layout.addRow("Armor Class:", self.ac_spin)

        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(0, 120)
        self.speed_spin.setValue(self.creature.speed)
        self.speed_spin.setSuffix(" ft")
        layout.addRow("Speed:", self.speed_spin)

        self.init_mod_spin = QSpinBox()
        self.init_mod_spin.setRange(-10, 20)
        self.init_mod_spin.setValue(self.creature.initiative_modifier)
        layout.addRow("Initiative Modifier:", self.init_mod_spin)

        # Saving throw proficiencies
        layout.addRow(QLabel("<b>Saving Throw Proficiencies:</b>"))
        saves_group = QHBoxLayout()
        self.save_checks = {}
        current_saves = self.sheet.get("save_proficiencies", [])
        if not current_saves:
            current_saves = get_save_proficiencies(self.sheet.get("character_class", ""))
        for ab in ABILITIES:
            cb = QCheckBox(ab)
            cb.setChecked(ab in current_saves)
            cb.toggled.connect(self._update_derived)
            self.save_checks[ab] = cb
            saves_group.addWidget(cb)
        layout.addRow(saves_group)

        # Hit dice
        self.hit_dice_used_spin = QSpinBox()
        self.hit_dice_used_spin.setRange(0, 20)
        self.hit_dice_used_spin.setValue(self.sheet.get("hit_dice_used", 0))
        layout.addRow("Hit Dice Used:", self.hit_dice_used_spin)

        return widget

    def _build_skills_tab(self):
        """Skills tab with proficiency checkboxes."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QGridLayout(widget)

        self.skill_checks = {}
        current_skills = self.sheet.get("skill_proficiencies", [])

        for i, (skill, ability) in enumerate(sorted(SKILLS.items())):
            row = i
            cb = QCheckBox(f"{skill} ({ability})")
            cb.setChecked(skill in current_skills)
            cb.toggled.connect(self._update_derived)
            self.skill_checks[skill] = cb

            bonus_label = QLabel()
            bonus_label.setFixedWidth(40)
            bonus_label.setAlignment(Qt.AlignCenter)

            layout.addWidget(cb, row, 0)
            layout.addWidget(bonus_label, row, 1)

        self._skill_bonus_labels = {
            skill: layout.itemAtPosition(i, 1).widget()
            for i, (skill, _) in enumerate(sorted(SKILLS.items()))
        }

        layout.setRowStretch(len(SKILLS), 1)
        scroll.setWidget(widget)
        return scroll

    def _build_spells_tab(self):
        """Spell slots tracker."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Spellcasting info
        self.spell_info_label = QLabel()
        self.spell_info_label.setStyleSheet("padding: 4px; background: #2a2a3e; border-radius: 4px; color: #ddd;")
        layout.addWidget(self.spell_info_label)

        # Spell slots grid
        slots_group = QGroupBox("Spell Slots")
        slots_layout = QGridLayout(slots_group)
        slots_layout.addWidget(QLabel("<b>Level</b>"), 0, 0)
        slots_layout.addWidget(QLabel("<b>Total</b>"), 0, 1)
        slots_layout.addWidget(QLabel("<b>Used</b>"), 0, 2)
        slots_layout.addWidget(QLabel("<b>Remaining</b>"), 0, 3)

        self.slot_total_labels = []
        self.slot_used_spins = []
        self.slot_remaining_labels = []
        used = self.sheet.get("spell_slots_used", [0]*9)

        for i in range(9):
            row = i + 1
            lvl_label = QLabel(f"{self._ordinal(i+1)}")
            lvl_label.setStyleSheet("font-weight: bold;")
            slots_layout.addWidget(lvl_label, row, 0)

            total = QLabel("0")
            total.setAlignment(Qt.AlignCenter)
            slots_layout.addWidget(total, row, 1)
            self.slot_total_labels.append(total)

            used_spin = QSpinBox()
            used_spin.setRange(0, 20)
            used_spin.setValue(used[i] if i < len(used) else 0)
            used_spin.valueChanged.connect(self._update_derived)
            slots_layout.addWidget(used_spin, row, 2)
            self.slot_used_spins.append(used_spin)

            remaining = QLabel("0")
            remaining.setAlignment(Qt.AlignCenter)
            remaining.setStyleSheet("font-weight: bold; color: #4ade80;")
            slots_layout.addWidget(remaining, row, 3)
            self.slot_remaining_labels.append(remaining)

        layout.addWidget(slots_group)

        # Long/short rest buttons
        rest_row = QHBoxLayout()
        short_rest_btn = QPushButton("Short Rest")
        short_rest_btn.setToolTip("Recover hit dice (half level, rounded up)")
        short_rest_btn.clicked.connect(self._short_rest)
        rest_row.addWidget(short_rest_btn)

        long_rest_btn = QPushButton("Long Rest")
        long_rest_btn.setToolTip("Recover all HP, all spell slots, half hit dice")
        long_rest_btn.clicked.connect(self._long_rest)
        rest_row.addWidget(long_rest_btn)
        layout.addLayout(rest_row)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def _build_notes_tab(self):
        """Features, equipment, and backstory."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("<b>Features & Traits:</b>"))
        self.features_edit = QTextEdit()
        self.features_edit.setPlaceholderText("Class features, racial traits, feats...")
        self.features_edit.setText(self.sheet.get("features", ""))
        self.features_edit.setMaximumHeight(150)
        layout.addWidget(self.features_edit)

        layout.addWidget(QLabel("<b>Equipment & Inventory:</b>"))
        self.equipment_edit = QTextEdit()
        self.equipment_edit.setPlaceholderText("Weapons, armor, items, gold...")
        self.equipment_edit.setText(self.sheet.get("equipment", ""))
        self.equipment_edit.setMaximumHeight(150)
        layout.addWidget(self.equipment_edit)

        layout.addWidget(QLabel("<b>Backstory & Notes:</b>"))
        self.backstory_edit = QTextEdit()
        self.backstory_edit.setPlaceholderText("Background, personality, bonds, flaws...")
        self.backstory_edit.setText(self.sheet.get("backstory", ""))
        layout.addWidget(self.backstory_edit)

        return widget

    def _on_class_changed(self, cls_name):
        """Update save proficiencies when class changes."""
        saves = get_save_proficiencies(cls_name)
        for ab, cb in self.save_checks.items():
            cb.setChecked(ab in saves)
        self._update_derived()

    def _update_derived(self):
        """Recalculate all derived stats from current values."""
        level = self.level_spin.value()
        cls = self.class_combo.currentText()
        prof = proficiency_bonus(level)
        hit_die = get_hit_die(cls)

        # Update ability modifiers
        scores = {}
        for ab in ABILITIES:
            val = self.ability_spins[ab].value()
            scores[ab] = val
            mod = ability_modifier(val)
            sign = "+" if mod >= 0 else ""
            self.mod_labels[ab].setText(f"{sign}{mod}")

        # Update skill bonuses
        skill_profs = [s for s, cb in self.skill_checks.items() if cb.isChecked()]
        for skill, ability in sorted(SKILLS.items()):
            mod = ability_modifier(scores.get(ability, 10))
            if skill in skill_profs:
                mod += prof
            sign = "+" if mod >= 0 else ""
            label = self._skill_bonus_labels.get(skill)
            if label:
                label.setText(f"{sign}{mod}")
                label.setStyleSheet("font-weight: bold; color: #4ade80;" if skill in skill_profs else "")

        # Update spell slots
        slots = get_spell_slots(cls, level)
        for i in range(9):
            total = slots[i]
            self.slot_total_labels[i].setText(str(total))
            used = self.slot_used_spins[i].value()
            remaining = max(0, total - used)
            self.slot_remaining_labels[i].setText(str(remaining))
            if total == 0:
                self.slot_used_spins[i].setEnabled(False)
                self.slot_remaining_labels[i].setStyleSheet("color: #666;")
            else:
                self.slot_used_spins[i].setEnabled(True)
                self.slot_used_spins[i].setMaximum(total)
                color = "#4ade80" if remaining > 0 else "#f87171"
                self.slot_remaining_labels[i].setStyleSheet(f"font-weight: bold; color: {color};")

        # Spell info
        casting_ab = get_casting_ability(cls)
        if casting_ab:
            temp_sheet = {"ability_scores": scores, "character_class": cls, "level": level}
            dc = calc_spell_save_dc(temp_sheet)
            atk = calc_spell_attack(temp_sheet)
            sign = "+" if atk >= 0 else ""
            self.spell_info_label.setText(
                f"Spellcasting: {casting_ab} | Spell Save DC: {dc} | "
                f"Spell Attack: {sign}{atk} | Proficiency: +{prof}"
            )
        else:
            self.spell_info_label.setText(f"Not a spellcaster | Proficiency: +{prof}")

        # Derived summary
        dex_mod = ability_modifier(scores.get("DEX", 10))
        init_sign = "+" if dex_mod >= 0 else ""
        save_profs = [ab for ab, cb in self.save_checks.items() if cb.isChecked()]
        save_strs = []
        for ab in ABILITIES:
            mod = ability_modifier(scores.get(ab, 10))
            if ab in save_profs:
                mod += prof
            sign = "+" if mod >= 0 else ""
            marker = "*" if ab in save_profs else " "
            save_strs.append(f"{ab}{marker}{sign}{mod}")

        self.derived_label.setText(
            f"Proficiency: +{prof} | Hit Die: d{hit_die} | "
            f"Initiative: {init_sign}{dex_mod} | "
            f"Saves: {' | '.join(save_strs)}"
        )

    def _short_rest(self):
        """Short rest: recover some hit dice."""
        level = self.level_spin.value()
        recoverable = max(1, level // 2)
        used = self.hit_dice_used_spin.value()
        new_used = max(0, used - recoverable)
        self.hit_dice_used_spin.setValue(new_used)

    def _long_rest(self):
        """Long rest: recover all spell slots, half hit dice, full HP."""
        # Reset spell slots
        for spin in self.slot_used_spins:
            spin.setValue(0)
        # Recover half hit dice
        level = self.level_spin.value()
        recoverable = max(1, level // 2)
        used = self.hit_dice_used_spin.value()
        self.hit_dice_used_spin.setValue(max(0, used - recoverable))
        # Full HP
        self.hp_spin.setValue(self.hp_max_spin.value())
        self._update_derived()

    def get_updated_creature(self):
        """Apply dialog values back to the creature and return it."""
        self.creature.name = self.name_edit.text()
        self.creature.hp = self.hp_spin.value()
        self.creature.hp_max = self.hp_max_spin.value()
        self.creature.ac = self.ac_spin.value()
        self.creature.speed = self.speed_spin.value()
        self.creature.initiative_modifier = self.init_mod_spin.value()

        # Build character sheet
        self.creature.character_sheet = {
            "race": self.race_combo.currentText(),
            "character_class": self.class_combo.currentText(),
            "level": self.level_spin.value(),
            "ability_scores": {ab: self.ability_spins[ab].value() for ab in ABILITIES},
            "skill_proficiencies": [s for s, cb in self.skill_checks.items() if cb.isChecked()],
            "save_proficiencies": [ab for ab, cb in self.save_checks.items() if cb.isChecked()],
            "spell_slots_used": [spin.value() for spin in self.slot_used_spins],
            "hit_dice_used": self.hit_dice_used_spin.value(),
            "features": self.features_edit.toPlainText(),
            "equipment": self.equipment_edit.toPlainText(),
            "backstory": self.backstory_edit.toPlainText(),
        }
        return self.creature

    @staticmethod
    def _ordinal(n):
        return f"{n}{'st' if n == 1 else 'nd' if n == 2 else 'rd' if n == 3 else 'th'}"
