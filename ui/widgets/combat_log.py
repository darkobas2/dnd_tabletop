"""Combat log widget — scrolling timestamped log of all game events."""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QTextEdit, QComboBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextCursor, QColor
from datetime import datetime


# Color map for event types
EVENT_COLORS = {
    "combat": "#e94560",
    "damage": "#e74c3c",
    "healing": "#27ae60",
    "dice": "#f39c12",
    "initiative": "#9b59b6",
    "condition": "#3498db",
    "movement": "#1abc9c",
    "death": "#2c3e50",
    "info": "#aaaaaa",
    "turn": "#e94560",
}


class CombatLog(QWidget):
    """Filterable, timestamped combat log."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter = "all"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        title = QLabel("Combat Log")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setStyleSheet("color: #f39c12;")
        header.addWidget(title)

        header.addStretch()

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["all", "combat", "damage", "healing", "dice",
                                     "initiative", "condition", "movement", "death", "info", "turn"])
        self.filter_combo.setFixedWidth(90)
        self.filter_combo.currentTextChanged.connect(self._set_filter)
        header.addWidget(self.filter_combo)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(45)
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0d0d1a;
                color: #cccccc;
                border: 1px solid #2a2a4a;
            }
        """)
        layout.addWidget(self.log_text)

        # Store raw entries for filtering
        self._entries = []

    def add_entry(self, event_type: str, message: str, details: str = ""):
        """Add a log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "type": event_type,
            "message": message,
            "details": details,
        }
        self._entries.append(entry)

        if self._filter == "all" or self._filter == event_type:
            self._append_formatted(entry)

    def _append_formatted(self, entry):
        color = EVENT_COLORS.get(entry["type"], "#aaaaaa")
        type_tag = entry["type"].upper()
        html = (f'<span style="color:#666">[{entry["timestamp"]}]</span> '
                f'<span style="color:{color}; font-weight:bold">[{type_tag}]</span> '
                f'<span style="color:#eee">{entry["message"]}</span>')
        if entry.get("details"):
            html += f' <span style="color:#888">({entry["details"]})</span>'

        self.log_text.append(html)
        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)

    def _set_filter(self, filter_type: str):
        self._filter = filter_type
        self._rebuild_display()

    def _rebuild_display(self):
        self.log_text.clear()
        for entry in self._entries:
            if self._filter == "all" or self._filter == entry["type"]:
                self._append_formatted(entry)

    def clear(self):
        self._entries.clear()
        self.log_text.clear()

    def log_dice_roll(self, result):
        """Log a DiceResult."""
        rolls_str = ""
        for group in result.individual_rolls:
            rolls_str += f"[{', '.join(str(r) for r in group)}] "
        roller = f"{result.roller}: " if result.roller else ""
        self.add_entry("dice", f"{roller}{result.expression} = {result.total}", rolls_str.strip())

    def log_damage(self, creature_name: str, amount: int, new_hp: int, max_hp: int):
        self.add_entry("damage", f"{creature_name} takes {amount} damage ({new_hp}/{max_hp} HP)")

    def log_healing(self, creature_name: str, amount: int, new_hp: int, max_hp: int):
        self.add_entry("healing", f"{creature_name} healed for {amount} ({new_hp}/{max_hp} HP)")

    def log_condition(self, creature_name: str, condition: str, added: bool):
        action = "gained" if added else "lost"
        self.add_entry("condition", f"{creature_name} {action} {condition}")

    def log_turn(self, creature_name: str, round_num: int):
        self.add_entry("turn", f"{creature_name}'s turn (Round {round_num})")

    def log_combat_start(self):
        self.add_entry("combat", "Combat started!")

    def log_combat_end(self):
        self.add_entry("combat", "Combat ended.")

    def log_death(self, creature_name: str):
        self.add_entry("death", f"{creature_name} has died!")

    def log_stable(self, creature_name: str):
        self.add_entry("info", f"{creature_name} has stabilized.")

    def log_initiative(self, creature_name: str, value: float):
        self.add_entry("initiative", f"{creature_name} rolled {value:.0f} initiative")
