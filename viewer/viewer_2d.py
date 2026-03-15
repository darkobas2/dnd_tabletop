"""2D Map Viewer with grid overlay, draggable tokens, combat panels, and fog of war."""

from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QMainWindow,
                                QDockWidget, QMenu, QInputDialog, QSplitter,
                                QWidget, QVBoxLayout)
from PySide6.QtGui import QPixmap, QColor, QPen, QKeyEvent, QPainter, QAction
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer

from viewer.token_item import TokenItem


class MapViewer(QMainWindow):
    """Full-featured 2D map viewer with dockable combat panels."""

    def __init__(self, map_path, width_sq, height_sq, tokens_to_add, map_scale=1.0,
                 encounter=None):
        super().__init__()
        self.setWindowTitle("D&D Map Viewer")

        self.encounter = encounter
        self.combat_log = None
        self.dice_panel = None
        self.initiative_panel = None
        self.token_items = []

        # Central widget: the map view
        self.view = _MapGraphicsView(map_path, width_sq, height_sq, tokens_to_add,
                                      map_scale, encounter, self)
        self.setCentralWidget(self.view)

        # Setup dock panels
        self._setup_panels()

        # Keyboard shortcut hints
        self.setStatusBar(None)

    def _setup_panels(self):
        """Create dockable panels for dice, initiative, and combat log."""
        try:
            from core.dice import roll_dice
            from core import initiative as initiative_module
            from ui.widgets.dice_panel import DicePanel
            from ui.widgets.initiative_panel import InitiativePanel
            from ui.widgets.combat_log import CombatLog

            # Right dock: Initiative + Dice
            right_widget = QWidget()
            right_layout = QVBoxLayout(right_widget)
            right_layout.setContentsMargins(0, 0, 0, 0)

            # Initiative panel
            self.initiative_panel = InitiativePanel()
            self.initiative_panel.set_initiative_module(initiative_module)
            if self.encounter:
                self.initiative_panel.set_encounter(self.encounter)
            self.initiative_panel.turn_advanced.connect(self._on_turn_advanced)
            self.initiative_panel.combat_started.connect(self._on_combat_started)
            self.initiative_panel.creature_selected.connect(self._on_creature_selected)
            right_layout.addWidget(self.initiative_panel)

            # Dice panel
            self.dice_panel = DicePanel()
            self.dice_panel.set_roll_function(roll_dice)
            right_layout.addWidget(self.dice_panel)

            right_dock = QDockWidget("Combat Controls", self)
            right_dock.setWidget(right_widget)
            right_dock.setMinimumWidth(250)
            self.addDockWidget(Qt.RightDockWidgetArea, right_dock)

            # Bottom dock: Combat log
            self.combat_log = CombatLog()
            log_dock = QDockWidget("Combat Log", self)
            log_dock.setWidget(self.combat_log)
            log_dock.setMaximumHeight(200)
            self.addDockWidget(Qt.BottomDockWidgetArea, log_dock)

            # Connect dice rolls to combat log
            self.dice_panel.dice_rolled.connect(self.combat_log.log_dice_roll)

            # Pass combat_log to the view for token context menus
            self.view.combat_log = self.combat_log

        except ImportError as e:
            print(f"Warning: Could not load combat panels: {e}")

    def _on_turn_advanced(self):
        if self.encounter and self.combat_log:
            active = self.encounter.creatures[self.encounter.active_creature_index] \
                if 0 <= self.encounter.active_creature_index < len(self.encounter.creatures) else None
            if active:
                self.combat_log.log_turn(active.name, self.encounter.round_number)
            # Highlight active token
            self._highlight_active_token()

    def _on_combat_started(self):
        if self.combat_log:
            self.combat_log.log_combat_start()
        self._highlight_active_token()

    def _on_creature_selected(self, creature_id):
        """Select the token for a creature in the view."""
        for token in self.view.token_items:
            if token.creature and token.creature.id == creature_id:
                self.view.scene().clearSelection()
                token.setSelected(True)
                self.view.centerOn(token)
                break

    def _highlight_active_token(self):
        """Visually highlight the active creature's token."""
        if not self.encounter or not self.encounter.combat_started:
            return
        active = self.encounter.creatures[self.encounter.active_creature_index] \
            if 0 <= self.encounter.active_creature_index < len(self.encounter.creatures) else None
        for token in self.view.token_items:
            if token.creature and active and token.creature.id == active.id:
                token.setSelected(True)
            else:
                token.setSelected(False)

    def edit_creature(self, creature):
        """Open creature editor dialog."""
        try:
            from ui.widgets.creature_editor import CreatureEditor
            dialog = CreatureEditor(creature, self)
            if dialog.exec():
                # Update all token visuals
                for token in self.view.token_items:
                    if token.creature and token.creature.id == creature.id:
                        token.update_visuals()
                if self.initiative_panel:
                    self.initiative_panel.refresh()
        except ImportError:
            pass

    def remove_token(self, token_item):
        """Remove a token from the map."""
        if token_item in self.view.token_items:
            self.view.token_items.remove(token_item)
        if token_item.creature and self.encounter:
            self.encounter.remove_creature(token_item.creature.id)
            if self.initiative_panel:
                self.initiative_panel.refresh()
        self.view.scene().removeItem(token_item)

    def refresh_all_tokens(self):
        for token in self.view.token_items:
            token.update_visuals()
        if self.initiative_panel:
            self.initiative_panel.refresh()

    def keyPressEvent(self, event: QKeyEvent):
        # Forward to the view
        self.view.keyPressEvent(event)


class _MapGraphicsView(QGraphicsView):
    """The actual QGraphicsView that renders the map and tokens."""

    def __init__(self, map_path, width_sq, height_sq, tokens_to_add, map_scale=1.0,
                 encounter=None, parent_viewer=None):
        super().__init__()
        self.setBackgroundBrush(QColor(0, 0, 0))
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.parent_viewer = parent_viewer
        self.combat_log = None
        self.encounter = encounter
        self.token_items = []

        self.base_pixmap = QPixmap(map_path)
        self.map_pixmap = self.base_pixmap.scaled(
            int(self.base_pixmap.width() * map_scale),
            int(self.base_pixmap.height() * map_scale),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        self.map_item = self._scene.addPixmap(self.map_pixmap)
        self._scene.setSceneRect(QRectF(self.map_pixmap.rect()))

        self.width_sq = width_sq
        self.height_sq = height_sq
        self.grid_size = self.map_pixmap.width() / width_sq

        self.grid_visible = True
        self.grid_items = []
        self._draw_grid()

        # Add tokens
        self._add_tokens(tokens_to_add)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        QTimer.singleShot(200, self.fit_to_screen)

    def _add_tokens(self, tokens_to_add):
        """Add tokens to the scene, creating CreatureState objects if encounter exists."""
        col_offset = 0
        for token_data, (count, token_scale) in tokens_to_add.items():
            pixmap = QPixmap(token_data.path)
            for i in range(count):
                creature = None
                if self.encounter:
                    try:
                        from core.game_state import CreatureState
                        # Create a creature for each token
                        base_name = token_data.name.split('.')[0]
                        # Clean up long names
                        if len(base_name) > 20:
                            parts = base_name.split('_')
                            # Try to find meaningful name parts
                            for part in parts:
                                if len(part) > 3 and not part.startswith('token') and not part[0].isdigit():
                                    base_name = part.capitalize()
                                    break
                        display_name = f"{base_name}" if count == 1 else f"{base_name} {i+1}"
                        creature = CreatureState(
                            name=display_name,
                            hp=10, hp_max=10,
                            token_path=token_data.path,
                            token_scale=token_scale,
                            position=(col_offset + i, 0)
                        )
                        self.encounter.add_creature(creature)
                    except ImportError:
                        pass

                token = TokenItem(pixmap, token_data.name, self.grid_size, token_scale,
                                  creature=creature, viewer=self.parent_viewer)
                self._scene.addItem(token)
                token.setPos((col_offset + i) * self.grid_size, 0)
                self.token_items.append(token)
            col_offset += count

    def fit_to_screen(self):
        self._scene.setSceneRect(QRectF(self.map_pixmap.rect()))
        self.fitInView(self.map_item, Qt.KeepAspectRatio)
        self.centerOn(self.map_item)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_to_screen()

    def _draw_grid(self):
        pen = QPen(QColor(255, 255, 255, 50))
        pen.setWidth(1)

        mw = self.map_pixmap.width()
        mh = self.map_pixmap.height()

        for i in range(self.width_sq + 1):
            x = i * self.grid_size
            if x > mw:
                x = mw
            line = self._scene.addLine(x, 0, x, mh, pen)
            self.grid_items.append(line)

        y = 0
        while y <= mh + 0.1:
            line = self._scene.addLine(0, y, mw, y, pen)
            self.grid_items.append(line)
            y += self.grid_size
            if self.grid_size <= 0:
                break

    def toggle_grid(self):
        self.grid_visible = not self.grid_visible
        for item in self.grid_items:
            item.setVisible(self.grid_visible)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_G:
            self.toggle_grid()
        elif event.key() == Qt.Key_Escape:
            window = self.window()
            if window:
                window.close()
        elif event.key() == Qt.Key_F:
            window = self.window()
            if window:
                if window.isFullScreen():
                    window.showNormal()
                else:
                    window.showFullScreen()
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)

    def contextMenuEvent(self, event):
        """Right-click on empty map space."""
        # Check if clicking on a token — let TokenItem handle it
        item = self.itemAt(event.pos())
        if isinstance(item, TokenItem) or (item and item.parentItem() and isinstance(item.parentItem(), TokenItem)):
            super().contextMenuEvent(event)
            return

        menu = QMenu(self)

        add_creature_action = menu.addAction("Add Creature Here...")
        menu.addSeparator()
        grid_action = menu.addAction("Toggle Grid (G)")
        fullscreen_action = menu.addAction("Toggle Fullscreen (F)")

        action = menu.exec(event.globalPos())
        if action == grid_action:
            self.toggle_grid()
        elif action == fullscreen_action:
            window = self.window()
            if window:
                if window.isFullScreen():
                    window.showNormal()
                else:
                    window.showFullScreen()
        elif action == add_creature_action:
            self._add_creature_at(event.pos())

    def _add_creature_at(self, view_pos):
        """Add a new creature at the clicked position."""
        if not self.encounter:
            return
        try:
            from ui.widgets.creature_editor import CreatureEditor
            from core.game_state import CreatureState

            creature = CreatureState(name="New Creature", hp=10, hp_max=10)
            dialog = CreatureEditor(creature, self)
            if dialog.exec():
                creature = dialog.get_creature()
                self.encounter.add_creature(creature)

                # Create token on map
                scene_pos = self.mapToScene(view_pos)
                if creature.token_path:
                    pixmap = QPixmap(creature.token_path)
                else:
                    # Create a colored circle as placeholder
                    pixmap = QPixmap(64, 64)
                    pixmap.fill(QColor("#e94560"))

                token = TokenItem(pixmap, creature.name, self.grid_size,
                                  creature.token_scale, creature=creature,
                                  viewer=self.parent_viewer)
                self._scene.addItem(token)
                token.setPos(scene_pos)
                self.token_items.append(token)

                if self.parent_viewer and self.parent_viewer.initiative_panel:
                    self.parent_viewer.initiative_panel.refresh()
        except ImportError:
            pass
