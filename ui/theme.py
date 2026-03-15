"""
Dark fantasy theme for the D&D Virtual Tabletop PySide6 application.

Provides a complete QSS stylesheet, color constants, and helper utilities
for consistent dark-themed UI rendering across all widgets.
"""

from PySide6.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------

COLORS = {
    "bg": "#1a1a2e",
    "surface": "#16213e",
    "surface_light": "#1f2b47",
    "accent": "#e94560",
    "accent_hover": "#ff6b81",
    "gold": "#f39c12",
    "gold_dark": "#d68910",
    "text": "#eeeeee",
    "text_muted": "#aaaaaa",
    "success": "#27ae60",
    "danger": "#e74c3c",
    "hp_green": "#27ae60",
    "hp_yellow": "#f39c12",
    "hp_red": "#e74c3c",
    "border": "#2a2a4a",
}


# ---------------------------------------------------------------------------
# HP color helper
# ---------------------------------------------------------------------------

def get_hp_color(current: int, maximum: int) -> str:
    """Return a hex color string reflecting hit-point severity.

    * > 50 %  -> hp_green
    * > 25 %  -> hp_yellow
    * <= 25 % -> hp_red
    """
    if maximum <= 0:
        return COLORS["hp_red"]
    ratio = current / maximum
    if ratio > 0.5:
        return COLORS["hp_green"]
    if ratio > 0.25:
        return COLORS["hp_yellow"]
    return COLORS["hp_red"]


# ---------------------------------------------------------------------------
# Complete QSS stylesheet
# ---------------------------------------------------------------------------

DARK_FANTASY_QSS = f"""
/* ===== Base ===== */
QWidget {{
    background-color: {COLORS["bg"]};
    color: {COLORS["text"]};
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
}}

/* ===== QLabel ===== */
QLabel {{
    color: {COLORS["text"]};
    background-color: transparent;
}}

/* ===== QPushButton ===== */
QPushButton {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 6px 16px;
    min-height: 24px;
}}
QPushButton:hover {{
    background-color: {COLORS["surface_light"]};
    border-color: {COLORS["accent"]};
}}
QPushButton:pressed {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text"]};
}}
QPushButton:disabled {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text_muted"]};
    border-color: {COLORS["border"]};
}}

/* ===== QComboBox ===== */
QComboBox {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 24px;
}}
QComboBox:hover {{
    border-color: {COLORS["accent"]};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid {COLORS["border"]};
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    background-color: {COLORS["surface_light"]};
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS["text_muted"]};
    margin-right: 5px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    selection-background-color: {COLORS["accent"]};
    selection-color: {COLORS["text"]};
    outline: none;
}}

/* ===== QSpinBox ===== */
QSpinBox {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 24px;
}}
QSpinBox:hover {{
    border-color: {COLORS["accent"]};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {COLORS["surface_light"]};
    border: none;
    width: 20px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {COLORS["accent"]};
}}
QSpinBox::up-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {COLORS["text_muted"]};
}}
QSpinBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {COLORS["text_muted"]};
}}

/* ===== QSlider ===== */
QSlider::groove:horizontal {{
    border: none;
    height: 6px;
    background-color: {COLORS["surface_light"]};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background-color: {COLORS["accent"]};
    border: none;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background-color: {COLORS["accent_hover"]};
}}
QSlider::sub-page:horizontal {{
    background-color: {COLORS["accent"]};
    border-radius: 3px;
}}
QSlider::groove:vertical {{
    border: none;
    width: 6px;
    background-color: {COLORS["surface_light"]};
    border-radius: 3px;
}}
QSlider::handle:vertical {{
    background-color: {COLORS["accent"]};
    border: none;
    width: 16px;
    height: 16px;
    margin: 0 -5px;
    border-radius: 8px;
}}
QSlider::handle:vertical:hover {{
    background-color: {COLORS["accent_hover"]};
}}

/* ===== QListWidget ===== */
QListWidget {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 4px 8px;
}}
QListWidget::item:selected {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text"]};
}}
QListWidget::item:hover {{
    background-color: {COLORS["surface_light"]};
}}

/* ===== QScrollArea ===== */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

/* ===== QScrollBar (vertical) ===== */
QScrollBar:vertical {{
    background-color: {COLORS["bg"]};
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background-color: {COLORS["surface_light"]};
    min-height: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {COLORS["accent"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ===== QScrollBar (horizontal) ===== */
QScrollBar:horizontal {{
    background-color: {COLORS["bg"]};
    height: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLORS["surface_light"]};
    min-width: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS["accent"]};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ===== QFrame ===== */
QFrame {{
    border-color: {COLORS["border"]};
}}

/* ===== QCheckBox ===== */
QCheckBox {{
    color: {COLORS["text"]};
    spacing: 8px;
    background-color: transparent;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {COLORS["border"]};
    border-radius: 3px;
    background-color: {COLORS["surface"]};
}}
QCheckBox::indicator:hover {{
    border-color: {COLORS["accent"]};
}}
QCheckBox::indicator:checked {{
    background-color: {COLORS["accent"]};
    border-color: {COLORS["accent"]};
    image: none;
}}

/* ===== QTabWidget ===== */
QTabWidget::pane {{
    border: 1px solid {COLORS["border"]};
    background-color: {COLORS["bg"]};
    border-radius: 4px;
}}
QTabBar::tab {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text_muted"]};
    border: 1px solid {COLORS["border"]};
    padding: 6px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}
QTabBar::tab:selected {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text"]};
    border-color: {COLORS["accent"]};
}}
QTabBar::tab:hover:!selected {{
    background-color: {COLORS["surface_light"]};
    color: {COLORS["text"]};
}}

/* ===== QLineEdit ===== */
QLineEdit {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 24px;
    selection-background-color: {COLORS["accent"]};
}}
QLineEdit:focus {{
    border-color: {COLORS["accent"]};
}}

/* ===== QTextEdit ===== */
QTextEdit {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px;
    selection-background-color: {COLORS["accent"]};
}}
QTextEdit:focus {{
    border-color: {COLORS["accent"]};
}}

/* ===== QGroupBox ===== */
QGroupBox {{
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    background-color: transparent;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    color: {COLORS["accent"]};
    background-color: {COLORS["bg"]};
    border-bottom: 2px solid {COLORS["accent"]};
}}

/* ===== QMenuBar ===== */
QMenuBar {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 2px;
}}
QMenuBar::item {{
    background-color: transparent;
    padding: 4px 12px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text"]};
}}

/* ===== QMenu ===== */
QMenu {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 3px;
}}
QMenu::item:selected {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text"]};
}}
QMenu::separator {{
    height: 1px;
    background-color: {COLORS["border"]};
    margin: 4px 8px;
}}

/* ===== QMessageBox ===== */
QMessageBox {{
    background-color: {COLORS["bg"]};
    color: {COLORS["text"]};
}}
QMessageBox QLabel {{
    color: {COLORS["text"]};
}}
QMessageBox QPushButton {{
    min-width: 80px;
}}

/* ===== QSplitter ===== */
QSplitter::handle {{
    background-color: {COLORS["border"]};
}}
QSplitter::handle:horizontal {{
    width: 2px;
}}
QSplitter::handle:vertical {{
    height: 2px;
}}
QSplitter::handle:hover {{
    background-color: {COLORS["accent"]};
}}

/* ===== QToolTip ===== */
QToolTip {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["gold"]};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}
"""


# ---------------------------------------------------------------------------
# Theme application
# ---------------------------------------------------------------------------

def apply_theme(app: QApplication) -> None:
    """Apply the dark fantasy stylesheet to the given QApplication."""
    app.setStyleSheet(DARK_FANTASY_QSS)
