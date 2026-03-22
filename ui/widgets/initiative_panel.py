"""Initiative tracker panel widget for the D&D virtual tabletop."""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QListWidget, QListWidgetItem, QFrame,
                                QSpinBox, QInputDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor


class InitiativePanel(QWidget):
    """Displays initiative order, allows advancing turns, rolling initiative."""

    turn_advanced = Signal()       # Emitted when next/prev turn
    combat_started = Signal()      # Emitted when combat begins
    combat_ended = Signal()        # Emitted when combat ends
    creature_selected = Signal(str)  # Emits creature_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._encounter = None
        self._initiative_module = None
        self._setup_ui()

    def set_encounter(self, encounter):
        self._encounter = encounter
        self.refresh()

    def set_initiative_module(self, module):
        """Set the core.initiative module for rolling."""
        self._initiative_module = module

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Title + Round counter
        header = QHBoxLayout()
        title = QLabel("Initiative")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setStyleSheet("color: #f39c12;")
        header.addWidget(title)
        header.addStretch()
        self.round_label = QLabel("Round: --")
        self.round_label.setStyleSheet("color: #aaa;")
        header.addWidget(self.round_label)
        layout.addLayout(header)

        # Initiative list (double-click to edit initiative value)
        self.init_list = QListWidget()
        self.init_list.setMinimumHeight(100)
        self.init_list.itemClicked.connect(self._on_item_clicked)
        self.init_list.itemDoubleClicked.connect(self._edit_initiative_value)
        layout.addWidget(self.init_list)

        # Control buttons
        btn_layout = QGridLayout = QHBoxLayout()

        self.roll_btn = QPushButton("Roll Init")
        self.roll_btn.setStyleSheet("background-color: #9b59b6; color: white;")
        self.roll_btn.clicked.connect(self._roll_initiative)
        btn_layout.addWidget(self.roll_btn)

        self.start_btn = QPushButton("Start")
        self.start_btn.setStyleSheet("background-color: #27ae60; color: white;")
        self.start_btn.clicked.connect(self._start_combat)
        btn_layout.addWidget(self.start_btn)

        layout.addLayout(btn_layout)

        nav_layout = QHBoxLayout()

        self.prev_btn = QPushButton("<< Prev")
        self.prev_btn.clicked.connect(self._prev_turn)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Next >>")
        self.next_btn.setStyleSheet("background-color: #e94560; color: white; font-weight: bold;")
        self.next_btn.clicked.connect(self._next_turn)
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)

        layout.addLayout(nav_layout)

        self.end_btn = QPushButton("End Combat")
        self.end_btn.setStyleSheet("background-color: #7f8c8d; color: white;")
        self.end_btn.clicked.connect(self._end_combat)
        self.end_btn.setEnabled(False)
        layout.addWidget(self.end_btn)

    def _roll_initiative(self):
        if not self._encounter or not self._initiative_module:
            return

        # Auto-roll NPCs, prompt for players
        for creature in self._encounter.creatures:
            if creature.is_player:
                val, ok = QInputDialog.getInt(
                    self, "Player Initiative",
                    f"Initiative roll for {creature.name}:",
                    value=10 + creature.initiative_modifier,
                    min=1, max=30
                )
                if ok:
                    creature.initiative = float(val)
            else:
                self._initiative_module.roll_creature_initiative(creature)

        self._initiative_module.sort_initiative(self._encounter)
        self.refresh()

    def _start_combat(self):
        if not self._encounter or not self._initiative_module:
            return
        # Auto-roll if no one has initiative yet
        if all(c.initiative is None for c in self._encounter.creatures):
            self._roll_initiative()
        self._initiative_module.start_combat(self._encounter)
        self.next_btn.setEnabled(True)
        self.prev_btn.setEnabled(True)
        self.end_btn.setEnabled(True)
        self.combat_started.emit()
        self.refresh()

    def _next_turn(self):
        if not self._encounter or not self._initiative_module:
            return
        self._initiative_module.next_turn(self._encounter)
        self.turn_advanced.emit()
        self.refresh()

    def _prev_turn(self):
        if not self._encounter or not self._initiative_module:
            return
        self._initiative_module.previous_turn(self._encounter)
        self.turn_advanced.emit()
        self.refresh()

    def _end_combat(self):
        if not self._encounter:
            return
        self._encounter.combat_started = False
        self._encounter.round_number = 0
        self._encounter.active_creature_index = -1
        self.next_btn.setEnabled(False)
        self.prev_btn.setEnabled(False)
        self.end_btn.setEnabled(False)
        self.combat_ended.emit()
        self.refresh()

    def _edit_initiative_value(self, item):
        """Double-click a creature to manually set its initiative value."""
        creature_id = item.data(Qt.UserRole)
        if not creature_id or not self._encounter:
            return
        creature = next((c for c in self._encounter.creatures if c.id == creature_id), None)
        if not creature:
            return
        current = int(creature.initiative) if creature.initiative is not None else 10
        val, ok = QInputDialog.getInt(
            self, "Set Initiative",
            f"Initiative for {creature.name}:",
            value=current, min=1, max=30
        )
        if ok:
            creature.initiative = float(val)
            if self._initiative_module:
                self._initiative_module.sort_initiative(self._encounter)
            self.refresh()

    def _on_item_clicked(self, item):
        creature_id = item.data(Qt.UserRole)
        if creature_id:
            self.creature_selected.emit(creature_id)

    def refresh(self):
        self.init_list.clear()
        if not self._encounter:
            self.round_label.setText("Round: --")
            return

        if self._encounter.combat_started:
            self.round_label.setText(f"Round: {self._encounter.round_number}")
        else:
            self.round_label.setText("Round: --")

        order = self._encounter.creatures
        for i, creature in enumerate(order):
            init_val = f"{creature.initiative:.0f}" if creature.initiative is not None else "--"
            hp_text = f"{creature.hp}/{creature.hp_max}"
            ac_text = f"AC{creature.ac}"
            conditions_text = ""
            if creature.conditions:
                conditions_text = " [" + ", ".join(creature.conditions[:3]) + "]"

            text = f"{init_val:>3}  {creature.name}  ({hp_text} {ac_text}){conditions_text}"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, creature.id)

            # Highlight active creature
            is_active = (self._encounter.combat_started and
                        i == self._encounter.active_creature_index)
            if is_active:
                item.setBackground(QColor("#e94560"))
                item.setForeground(QColor("#ffffff"))
            elif "Dead" in creature.conditions:
                item.setForeground(QColor("#666666"))
            elif "Unconscious" in creature.conditions:
                item.setForeground(QColor("#888888"))
            elif creature.is_player:
                item.setForeground(QColor("#3498db"))
            else:
                item.setForeground(QColor("#eeeeee"))

            if not creature.is_visible:
                item.setForeground(QColor("#555555"))
                text = f"{text} (Hidden)"
                item.setText(text)

            self.init_list.addItem(item)
