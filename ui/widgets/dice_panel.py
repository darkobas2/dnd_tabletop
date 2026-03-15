"""Dice rolling panel widget for the D&D virtual tabletop."""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QLineEdit, QScrollArea, QFrame, QGridLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class DicePanel(QWidget):
    """Panel with quick-roll buttons, custom expression input, and roll history."""

    dice_rolled = Signal(object)  # Emits DiceResult

    def __init__(self, parent=None):
        super().__init__(parent)
        self._roll_func = None  # Set via set_roll_function
        self._history = []
        self._setup_ui()

    def set_roll_function(self, roll_func):
        """Set the dice rolling function (core.dice.roll_dice)."""
        self._roll_func = roll_func

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Title
        title = QLabel("Dice Roller")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setStyleSheet("color: #f39c12;")
        layout.addWidget(title)

        # Quick roll buttons
        quick_frame = QFrame()
        quick_layout = QGridLayout(quick_frame)
        quick_layout.setSpacing(3)
        quick_layout.setContentsMargins(0, 0, 0, 0)

        dice_types = [
            ("d4", "1d4"), ("d6", "1d6"), ("d8", "1d8"),
            ("d10", "1d10"), ("d12", "1d12"), ("d20", "1d20"),
            ("d100", "1d100"), ("2d6", "2d6"), ("Adv", "1d20adv"),
            ("Dis", "1d20dis"), ("4d6kh3", "4d6kh3"), ("2d20", "2d20"),
        ]

        for i, (label, expr) in enumerate(dice_types):
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setMinimumWidth(50)
            btn.clicked.connect(lambda checked, e=expr: self._do_roll(e))
            quick_layout.addWidget(btn, i // 4, i % 4)

        layout.addWidget(quick_frame)

        # Custom expression input
        expr_layout = QHBoxLayout()
        self.expr_input = QLineEdit()
        self.expr_input.setPlaceholderText("e.g. 2d6+3, 1d20+5")
        self.expr_input.returnPressed.connect(self._roll_custom)
        expr_layout.addWidget(self.expr_input)

        roll_btn = QPushButton("Roll")
        roll_btn.setFixedWidth(50)
        roll_btn.setStyleSheet("background-color: #e94560; color: white; font-weight: bold;")
        roll_btn.clicked.connect(self._roll_custom)
        expr_layout.addWidget(roll_btn)
        layout.addLayout(expr_layout)

        # Last result display
        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.result_label.setStyleSheet("color: #f39c12; padding: 4px;")
        self.result_label.setMinimumHeight(40)
        layout.addWidget(self.result_label)

        # Roll history (scrollable)
        history_label = QLabel("History")
        history_label.setStyleSheet("color: #aaa; font-size: 10px;")
        layout.addWidget(history_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(120)
        self.history_widget = QWidget()
        self.history_layout = QVBoxLayout(self.history_widget)
        self.history_layout.setAlignment(Qt.AlignTop)
        self.history_layout.setSpacing(1)
        self.history_layout.setContentsMargins(2, 2, 2, 2)
        scroll.setWidget(self.history_widget)
        layout.addWidget(scroll)

    def _do_roll(self, expression: str):
        if not self._roll_func:
            return
        try:
            result = self._roll_func(expression)
            self._show_result(result)
            self.dice_rolled.emit(result)
        except Exception as e:
            self.result_label.setText(f"Error: {e}")
            self.result_label.setStyleSheet("color: #e74c3c; padding: 4px;")

    def _roll_custom(self):
        expr = self.expr_input.text().strip()
        if expr:
            self._do_roll(expr)

    def _show_result(self, result):
        # Show big total
        self.result_label.setText(str(result.total))
        self.result_label.setStyleSheet("color: #f39c12; padding: 4px; font-size: 18px;")

        # Format rolls detail
        rolls_str = ""
        for group in result.individual_rolls:
            rolls_str += f"[{', '.join(str(r) for r in group)}] "

        # Add to history
        detail = f"{result.expression} = {result.total}  ({rolls_str.strip()})"
        if result.roller:
            detail = f"{result.roller}: {detail}"

        history_entry = QLabel(detail)
        history_entry.setStyleSheet("color: #ccc; font-size: 10px; padding: 1px;")
        history_entry.setWordWrap(True)
        self.history_layout.insertWidget(0, history_entry)

        self._history.append(result)
        # Keep max 50 entries
        if self.history_layout.count() > 50:
            item = self.history_layout.takeAt(self.history_layout.count() - 1)
            if item and item.widget():
                item.widget().deleteLater()

    def clear_history(self):
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._history.clear()
