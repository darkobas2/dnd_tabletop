"""Effect overlay item for the 2D map viewer — renders spell/hazard areas."""

from PySide6.QtWidgets import (QGraphicsItem, QMenu, QInputDialog, QDialog,
                                QHBoxLayout, QLabel, QSpinBox,
                                QPushButton, QFormLayout)
from PySide6.QtGui import QColor, QPen, QBrush, QRadialGradient, QPainter, QPainterPath
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer
import math


class PlaceEffectDialog(QDialog):
    """Dialog for placing an effect — lets DM pick size and shape options."""

    def __init__(self, effect_name, effect_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Place: {effect_name}")
        self.setMinimumWidth(300)

        layout = QFormLayout(self)
        layout.addRow("Effect:", QLabel(f"<b>{effect_name}</b>"))
        layout.addRow("Shape:", QLabel(effect_data["shape"].capitalize()))

        # Radius / size
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(1, 40)
        self.radius_spin.setValue(effect_data.get("radius", 4))
        self.radius_spin.setSuffix(" squares")
        if effect_data["shape"] == "line":
            layout.addRow("Length:", self.radius_spin)
        else:
            layout.addRow("Radius / Size:", self.radius_spin)

        # Rotation (for cone/line)
        if effect_data["shape"] in ("cone", "line"):
            self.rotation_spin = QSpinBox()
            self.rotation_spin.setRange(0, 359)
            self.rotation_spin.setValue(0)
            self.rotation_spin.setSuffix("\u00b0")
            layout.addRow("Direction:", self.rotation_spin)
        else:
            self.rotation_spin = None

        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Place")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def get_radius(self):
        return self.radius_spin.value()

    def get_rotation(self):
        return self.rotation_spin.value() if self.rotation_spin else 0


class EffectItem(QGraphicsItem):
    """A draggable area-effect overlay on the 2D map."""

    def __init__(self, effect, grid_size, viewer=None):
        super().__init__()
        self.effect = effect
        self.grid_size = grid_size
        self.viewer = viewer
        self._anim_phase = 0.0
        self._base_opacity = effect.opacity

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setZValue(5)

        # Position on grid
        gx, gy = effect.position
        self.setPos((gx + 0.5) * grid_size, (gy + 0.5) * grid_size)

        # Animation timer
        if effect.animation:
            self._anim_timer = QTimer()
            self._anim_timer.setInterval(80)
            self._anim_timer.timeout.connect(self._animate)
            self._anim_timer.start()
        else:
            self._anim_timer = None

    def _shape_rect(self):
        """Return the tight visual rect for the effect shape (centered at 0,0)."""
        gs = self.grid_size
        r = self.effect.radius
        shape = self.effect.shape

        if shape == "circle":
            px = r * gs
            return QRectF(-px, -px, px * 2, px * 2)
        elif shape == "cube":
            side = r * gs
            return QRectF(-side / 2, -side / 2, side, side)
        elif shape == "line":
            length = r * gs
            width = gs * 0.8
            # Rotated line — compute axis-aligned bounding box
            angle = math.radians(self.effect.rotation)
            # Four corners of the unrotated rect: (0, -w/2), (len, -w/2), (len, w/2), (0, w/2)
            corners = [
                (0, -width / 2), (length, -width / 2),
                (length, width / 2), (0, width / 2),
            ]
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            xs = [c[0] * cos_a - c[1] * sin_a for c in corners]
            ys = [c[0] * sin_a + c[1] * cos_a for c in corners]
            return QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
        elif shape == "cone":
            px = r * gs
            return QRectF(-px, -px, px * 2, px * 2)
        return QRectF(-50, -50, 100, 100)

    def boundingRect(self):
        r = self._shape_rect()
        label_margin = 30  # space for label above
        # Extra margin for swirl rotation
        if self.effect.animation == "swirl":
            ext = max(r.width(), r.height()) / 2 + 10
            return QRectF(-ext, -ext - label_margin, ext * 2, ext * 2 + label_margin)
        return r.adjusted(-4, -label_margin - 4, 4, 4)

    def shape(self):
        """Return precise shape for mouse hit-testing (not the full bounding rect)."""
        path = QPainterPath()
        path.addRect(self._shape_rect().adjusted(-6, -6, 6, 6))
        return path

    def _animate(self):
        self._anim_phase += 0.1
        if self._anim_phase > 2 * math.pi:
            self._anim_phase -= 2 * math.pi

        if self.effect.animation == "pulse":
            factor = 0.7 + 0.3 * math.sin(self._anim_phase * 0.8)
            self.setOpacity(factor)
        elif self.effect.animation == "flicker":
            import random
            factor = 0.65 + 0.35 * random.random()
            self.setOpacity(factor)
        elif self.effect.animation == "swirl":
            self.prepareGeometryChange()
            self.setRotation(self._anim_phase * 5 % 360)
            self.update()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(self.effect.color)
        gs = self.grid_size

        # Border pen
        border_color = QColor(color)
        border_color.setAlphaF(min(1.0, self._base_opacity + 0.3))
        border_pen = QPen(border_color, 2, Qt.DashLine)

        if self.effect.shape == "circle":
            r = self.effect.radius * gs
            gradient = QRadialGradient(0, 0, r)
            c_center = QColor(color)
            c_center.setAlphaF(self._base_opacity * 0.8)
            c_edge = QColor(color)
            c_edge.setAlphaF(self._base_opacity * 0.15)
            gradient.setColorAt(0, c_center)
            gradient.setColorAt(0.7, c_center)
            gradient.setColorAt(1, c_edge)
            painter.setBrush(QBrush(gradient))
            painter.setPen(border_pen)
            painter.drawEllipse(QPointF(0, 0), r, r)

        elif self.effect.shape == "cube":
            side = self.effect.radius * gs
            fill = QColor(color)
            fill.setAlphaF(self._base_opacity)
            painter.setBrush(QBrush(fill))
            painter.setPen(border_pen)
            painter.drawRect(QRectF(-side / 2, -side / 2, side, side))

        elif self.effect.shape == "cone":
            r = self.effect.radius * gs
            fill = QColor(color)
            fill.setAlphaF(self._base_opacity)
            painter.setBrush(QBrush(fill))
            painter.setPen(border_pen)
            path = QPainterPath()
            path.moveTo(0, 0)
            start_deg = -(self.effect.rotation + 30)
            path.arcTo(-r, -r, 2 * r, 2 * r, start_deg, 60)
            path.closeSubpath()
            painter.drawPath(path)

        elif self.effect.shape == "line":
            length = self.effect.radius * gs
            width = gs * 0.8
            fill = QColor(color)
            fill.setAlphaF(self._base_opacity)
            painter.setBrush(QBrush(fill))
            painter.setPen(border_pen)
            painter.save()
            painter.rotate(self.effect.rotation)
            painter.drawRect(QRectF(0, -width / 2, length, width))
            painter.restore()

        # Selection highlight
        if self.isSelected():
            sel_pen = QPen(QColor("#f39c12"), 3, Qt.SolidLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.NoBrush)
            sr = self._shape_rect()
            painter.drawRect(sr)

        # Name label above — always upright even when item rotates
        painter.save()
        painter.resetTransform()  # undo any swirl rotation for text
        # Map item origin to scene, then to painter coords
        scene_pos = self.scenePos()
        sr = self._shape_rect()
        font = painter.font()
        font_size = max(9, int(gs * 0.22))
        font.setPointSize(font_size)
        font.setBold(True)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text = self.effect.name
        tw = fm.horizontalAdvance(text) + 12
        th = fm.height() + 4
        tx = scene_pos.x() - tw / 2
        ext = max(abs(sr.top()), abs(sr.bottom()), abs(sr.left()), abs(sr.right()))
        ty = scene_pos.y() - ext - th - 4
        # Dark background pill
        painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(tx, ty, tw, th), 4, 4)
        # Text
        painter.setPen(QColor(255, 255, 255, 230))
        painter.drawText(QRectF(tx, ty, tw, th), Qt.AlignCenter, text)
        painter.restore()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            gx = round(new_pos.x() / self.grid_size - 0.5)
            gy = round(new_pos.y() / self.grid_size - 0.5)
            snapped = QPointF((gx + 0.5) * self.grid_size, (gy + 0.5) * self.grid_size)

            old_pos = self.effect.position
            self.effect.position = (gx, gy)
            if old_pos != (gx, gy) and self.viewer:
                self.viewer.schedule_save()

            return snapped

        return super().itemChange(change, value)

    def contextMenuEvent(self, event):
        menu = QMenu()

        resize_action = menu.addAction(f"Resize (current: {self.effect.radius} sq)...")
        if self.effect.shape in ("cone", "line"):
            rotate_action = menu.addAction(f"Rotate ({int(self.effect.rotation)}\u00b0)...")
        else:
            rotate_action = None
        menu.addSeparator()
        hide_action = menu.addAction("Hide from Players" if self.effect.visible else "Show to Players")
        menu.addSeparator()
        remove_action = menu.addAction("Remove Effect")

        action = menu.exec(event.screenPos())
        if not action:
            return

        if action == resize_action:
            label = "Length" if self.effect.shape == "line" else "Radius"
            val, ok = QInputDialog.getInt(
                None, "Resize Effect",
                f"{label} for {self.effect.name} (grid squares):",
                self.effect.radius, 1, 40
            )
            if ok:
                self.effect.radius = val
                self.prepareGeometryChange()
                self.update()

        elif rotate_action and action == rotate_action:
            val, ok = QInputDialog.getInt(
                None, "Rotate Effect",
                f"Direction for {self.effect.name} (degrees):",
                int(self.effect.rotation), 0, 359
            )
            if ok:
                self.effect.rotation = float(val)
                self.prepareGeometryChange()
                self.update()

        elif action == hide_action:
            self.effect.visible = not self.effect.visible
            self.setVisible(self.effect.visible)

        elif action == remove_action:
            if self.viewer:
                self.viewer.remove_effect(self)
                return

        if self.viewer:
            self.viewer.schedule_save()

    def cleanup(self):
        if self._anim_timer:
            self._anim_timer.stop()
            self._anim_timer = None

    def hoverEnterEvent(self, event):
        self.setToolTip(f"{self.effect.name}\nShape: {self.effect.shape}\n"
                        f"Radius: {self.effect.radius} sq\n"
                        f"Drag to move \u2022 Right-click to edit/remove")
        super().hoverEnterEvent(event)
