"""Token item for the 2D map viewer — with HP bars, conditions, and context menus."""

from PySide6.QtWidgets import (QGraphicsPixmapItem, QGraphicsItem, QGraphicsRectItem,
                                QGraphicsTextItem, QGraphicsEllipseItem, QMenu,
                                QInputDialog, QMessageBox)
from PySide6.QtGui import QPixmap, QColor, QPen, QBrush, QFont, QPainter, QAction
from PySide6.QtCore import Qt, QPointF, QRectF


class TokenItem(QGraphicsPixmapItem):
    """A draggable token on the 2D map with HP bar, name label, and condition icons."""

    def __init__(self, pixmap, name, grid_size, token_scale, creature=None, viewer=None):
        super().__init__(pixmap)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setZValue(5)  # Above effects so tokens are always selectable
        self.grid_size = grid_size
        self.name = name
        self.creature = creature  # Optional CreatureState reference
        self.viewer = viewer  # Reference to MapViewer for callbacks

        # Calculate base size to fit ~80% of a square
        base_size = grid_size * 0.8
        pw = self.pixmap().width()
        ph = self.pixmap().height()
        initial_scale = base_size / max(pw, ph)
        self.setScale(initial_scale * token_scale)

        # Visual overlays (created lazily)
        self._hp_bar_bg = None
        self._hp_bar_fill = None
        self._name_label = None
        self._condition_icons = []
        self._selection_ring = None

        # Build overlays if creature is attached
        if creature:
            self._build_overlays()

    def _build_overlays(self):
        """Create HP bar, name label, and selection ring."""
        if not self.creature:
            return

        pw = self.pixmap().width()
        ph = self.pixmap().height()

        # HP bar background (dark)
        bar_width = pw
        bar_height = max(4, pw * 0.06)
        self._hp_bar_bg = QGraphicsRectItem(0, ph + 2, bar_width, bar_height, self)
        self._hp_bar_bg.setBrush(QBrush(QColor(40, 40, 40, 200)))
        self._hp_bar_bg.setPen(QPen(QColor(0, 0, 0, 150), 1))

        # HP bar fill
        self._hp_bar_fill = QGraphicsRectItem(0, ph + 2, bar_width, bar_height, self)
        self._hp_bar_fill.setPen(QPen(Qt.NoPen))
        self._update_hp_bar()

        # Name label
        self._name_label = QGraphicsTextItem(self.creature.name, self)
        font = QFont("Segoe UI", max(8, int(pw * 0.10)))
        font.setBold(True)
        self._name_label.setFont(font)
        self._name_label.setDefaultTextColor(QColor(255, 255, 255))
        # Center name above token
        text_width = self._name_label.boundingRect().width()
        self._name_label.setPos((pw - text_width) / 2, -self._name_label.boundingRect().height() - 2)

        self._update_conditions_display()

    def _update_hp_bar(self):
        if not self._hp_bar_fill or not self.creature:
            return
        pw = self.pixmap().width()
        ph = self.pixmap().height()
        bar_height = max(4, pw * 0.06)

        ratio = max(0, self.creature.hp / self.creature.hp_max) if self.creature.hp_max > 0 else 0
        fill_width = pw * ratio

        # Color based on HP percentage
        if ratio > 0.5:
            color = QColor("#27ae60")
        elif ratio > 0.25:
            color = QColor("#f39c12")
        else:
            color = QColor("#e74c3c")

        self._hp_bar_fill.setRect(0, ph + 2, fill_width, bar_height)
        self._hp_bar_fill.setBrush(QBrush(color))

    def _update_conditions_display(self):
        """Show condition icons below HP bar."""
        # Clear existing
        for icon in self._condition_icons:
            if icon.scene():
                icon.scene().removeItem(icon)
        self._condition_icons.clear()

        if not self.creature or not self.creature.conditions:
            return

        try:
            from core.conditions import CONDITION_COLORS, CONDITION_ICONS
        except ImportError:
            return

        pw = self.pixmap().width()
        ph = self.pixmap().height()
        bar_height = max(4, pw * 0.06)
        y_start = ph + bar_height + 6
        icon_size = max(12, int(pw * 0.17))

        for i, cond in enumerate(self.creature.conditions[:6]):
            icon_text = CONDITION_ICONS.get(cond, "?")
            color = CONDITION_COLORS.get(cond, "#aaa")

            text_item = QGraphicsTextItem(icon_text, self)
            font = QFont("Segoe UI", max(8, icon_size))
            text_item.setFont(font)
            text_item.setDefaultTextColor(QColor(color))
            text_item.setPos(i * (icon_size + 2), y_start)
            text_item.setToolTip(cond)
            self._condition_icons.append(text_item)

    def _trigger_save(self):
        """Tell the parent viewer to save creature data."""
        if self.viewer and hasattr(self.viewer, 'schedule_save'):
            self.viewer.schedule_save()

    def update_visuals(self):
        """Refresh all visual overlays from creature state."""
        if not self.creature:
            return
        self._update_hp_bar()
        self._update_conditions_display()

        # Update visibility (DM hidden tokens)
        if not self.creature.is_visible:
            self.setOpacity(0.4)
        else:
            self.setOpacity(1.0)

        # Update name if changed
        if self._name_label:
            self._name_label.setPlainText(self.creature.name)

        # Force repaint to update condition overlay
        self.update()

    def paint(self, painter, option, widget=None):
        """Draw the token pixmap, then overlay a condition tint if applicable."""
        super().paint(painter, option, widget)

        if self.creature and self.creature.conditions:
            try:
                from core.conditions import CONDITION_COLORS
                first_cond = self.creature.conditions[0]
                color_hex = CONDITION_COLORS.get(first_cond, "#aaaaaa")
                overlay_color = QColor(color_hex)
                overlay_color.setAlpha(60)
                painter.setBrush(QBrush(overlay_color))
                painter.setPen(QPen(Qt.NoPen))
                pw = self.pixmap().width()
                ph = self.pixmap().height()
                painter.drawEllipse(0, 0, pw, ph)
            except ImportError:
                pass

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            sw = self.pixmap().width() * self.scale()
            sh = self.pixmap().height() * self.scale()

            # Snap: find the grid cell the center of the token falls in
            center_x = new_pos.x() + sw / 2
            center_y = new_pos.y() + sh / 2
            grid_col = int(center_x / self.grid_size) if center_x >= 0 else int(center_x / self.grid_size) - 1
            grid_row = int(center_y / self.grid_size) if center_y >= 0 else int(center_y / self.grid_size) - 1

            # Position so token is centered in the grid cell
            gx = grid_col * self.grid_size + self.grid_size / 2 - sw / 2
            gy = grid_row * self.grid_size + self.grid_size / 2 - sh / 2

            # Update creature position in grid coords
            if self.creature:
                old_pos = self.creature.position
                self.creature.position = (grid_col, grid_row)
                if old_pos != (grid_col, grid_row):
                    self._trigger_save()

            return QPointF(gx, gy)

        if change == QGraphicsItem.ItemSelectedHasChanged:
            self._update_selection_ring(value)

        return super().itemChange(change, value)

    def _update_selection_ring(self, selected):
        if selected:
            if not self._selection_ring:
                pw = self.pixmap().width()
                ph = self.pixmap().height()
                ring_size = max(pw, ph) * 1.1
                offset_x = (pw - ring_size) / 2
                offset_y = (ph - ring_size) / 2
                self._selection_ring = QGraphicsEllipseItem(
                    offset_x, offset_y, ring_size, ring_size, self
                )
                pen = QPen(QColor("#f39c12"), 3)
                self._selection_ring.setPen(pen)
                self._selection_ring.setBrush(QBrush(Qt.NoBrush))
            self._selection_ring.setVisible(True)
        else:
            if self._selection_ring:
                self._selection_ring.setVisible(False)

    def contextMenuEvent(self, event):
        """Right-click context menu for token actions."""
        if not self.creature or not self.viewer:
            return

        menu = QMenu()

        # HP actions
        damage_action = menu.addAction("Damage...")
        heal_action = menu.addAction("Heal...")
        set_hp_action = menu.addAction("Set HP...")
        menu.addSeparator()

        # Conditions submenu
        cond_menu = menu.addMenu("Conditions")
        try:
            from core.conditions import CONDITIONS
            for cond_name in sorted(CONDITIONS.keys()):
                action = cond_menu.addAction(cond_name)
                action.setCheckable(True)
                action.setChecked(cond_name in self.creature.conditions)
        except ImportError:
            pass
        menu.addSeparator()

        # Visibility
        hide_action = menu.addAction("Hide from Players" if self.creature.is_visible else "Show to Players")
        menu.addSeparator()

        # Edit
        edit_action = menu.addAction("Edit Creature...")

        # Character sheet (optional, for player characters)
        sheet_action = None
        if self.creature.is_player:
            sheet_action = menu.addAction("Character Sheet...")
        menu.addSeparator()

        # Remove
        remove_action = menu.addAction("Remove from Map")

        # Execute
        action = menu.exec(event.screenPos())
        if not action:
            return

        if action == damage_action:
            val, ok = QInputDialog.getInt(None, "Damage", f"Damage to {self.creature.name}:", 0, 0, 9999)
            if ok and val > 0:
                self.creature.apply_damage(val)
                self.update_visuals()
                if self.viewer and hasattr(self.viewer, 'combat_log'):
                    self.viewer.combat_log.log_damage(self.creature.name, val, self.creature.hp, self.creature.hp_max)
                self._trigger_save()

        elif action == heal_action:
            val, ok = QInputDialog.getInt(None, "Heal", f"Healing for {self.creature.name}:", 0, 0, 9999)
            if ok and val > 0:
                self.creature.apply_healing(val)
                self.update_visuals()
                if self.viewer and hasattr(self.viewer, 'combat_log'):
                    self.viewer.combat_log.log_healing(self.creature.name, val, self.creature.hp, self.creature.hp_max)
                self._trigger_save()

        elif action == set_hp_action:
            val, ok = QInputDialog.getInt(None, "Set HP", f"Set HP for {self.creature.name}:",
                                          self.creature.hp, 0, self.creature.hp_max)
            if ok:
                self.creature.set_hp(val)
                self.update_visuals()
                self._trigger_save()

        elif action == hide_action:
            self.creature.is_visible = not self.creature.is_visible
            self.update_visuals()
            self._trigger_save()

        elif action == edit_action:
            if self.viewer:
                self.viewer.edit_creature(self.creature)

        elif sheet_action and action == sheet_action:
            try:
                from ui.widgets.character_sheet import CharacterSheetDialog
                dlg = CharacterSheetDialog(self.creature, None)
                if dlg.exec():
                    dlg.get_updated_creature()
                    self.update_visuals()
                    self._trigger_save()
                    if self.viewer and hasattr(self.viewer, 'initiative_panel') and self.viewer.initiative_panel:
                        self.viewer.initiative_panel.refresh()
            except Exception as e:
                print(f"Character sheet error: {e}")

        elif action == remove_action:
            if self.viewer:
                self.viewer.remove_token(self)

        elif action.parent() == cond_menu:
            cond_name = action.text()
            if cond_name in self.creature.conditions:
                self.creature.remove_condition(cond_name)
                if self.viewer and hasattr(self.viewer, 'combat_log'):
                    self.viewer.combat_log.log_condition(self.creature.name, cond_name, False)
            else:
                self.creature.add_condition(cond_name)
                if self.viewer and hasattr(self.viewer, 'combat_log'):
                    self.viewer.combat_log.log_condition(self.creature.name, cond_name, True)
            self.update_visuals()
            self._trigger_save()

    def hoverEnterEvent(self, event):
        if self.creature:
            hp_text = f"HP: {self.creature.hp}/{self.creature.hp_max}"
            if self.creature.hp_temp > 0:
                hp_text += f" (+{self.creature.hp_temp} temp)"
            cond_text = ", ".join(self.creature.conditions) if self.creature.conditions else "None"
            tooltip = f"{self.creature.name}\n{hp_text}\nAC: {self.creature.ac}\nConditions: {cond_text}"
            if self.creature.notes:
                tooltip += f"\nNotes: {self.creature.notes}"
            self.setToolTip(tooltip)
        super().hoverEnterEvent(event)
