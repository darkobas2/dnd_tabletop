"""2D Map Viewer with grid overlay, draggable tokens, combat panels, and fog of war."""

import os
import json

from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QMainWindow,
                                QDockWidget, QMenu, QInputDialog, QSplitter,
                                QWidget, QVBoxLayout, QMenuBar)
from PySide6.QtGui import QPixmap, QColor, QPen, QKeyEvent, QPainter, QAction
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer

from viewer.token_item import TokenItem


class MapViewer(QMainWindow):
    """Full-featured 2D map viewer with dockable combat panels."""

    def __init__(self, map_path, width_sq, height_sq, tokens_to_add, map_scale=1.0,
                 encounter=None, folder_path=None):
        super().__init__()
        self.setWindowTitle("D&D Map Viewer")

        self.encounter = encounter
        self.folder_path = folder_path
        self.combat_log = None
        self.dice_panel = None
        self.initiative_panel = None
        self.token_items = []
        self._right_dock = None
        self._log_dock = None
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(1000)  # Debounce: save 1s after last change
        self._save_timer.timeout.connect(self._save_creatures)

        # If encounter already has creatures (loaded from config), skip auto-creation
        has_saved_creatures = encounter and len(encounter.creatures) > 0

        # Central widget: the map view
        self.view = _MapGraphicsView(map_path, width_sq, height_sq, tokens_to_add,
                                      map_scale, encounter, self,
                                      skip_creature_creation=has_saved_creatures)
        self.setCentralWidget(self.view)

        # If we loaded creatures, create token visuals for them
        if has_saved_creatures:
            self.view._create_tokens_from_encounter(tokens_to_add)

        # Setup dock panels
        self._setup_panels()

        # Setup menu bar
        self._setup_menu()

    def _setup_menu(self):
        """Create menu bar with View menu to restore panels."""
        menubar = self.menuBar()

        # ---- View menu ----
        view_menu = menubar.addMenu("View")

        if self._right_dock:
            self._toggle_combat_action = self._right_dock.toggleViewAction()
            self._toggle_combat_action.setText("Combat Controls")
            view_menu.addAction(self._toggle_combat_action)

        if self._log_dock:
            self._toggle_log_action = self._log_dock.toggleViewAction()
            self._toggle_log_action.setText("Combat Log")
            view_menu.addAction(self._toggle_log_action)

        view_menu.addSeparator()

        grid_action = QAction("Toggle Grid (G)", self)
        grid_action.triggered.connect(self.view.toggle_grid)
        view_menu.addAction(grid_action)

        fullscreen_action = QAction("Toggle Fullscreen (F)", self)
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        # ---- Creatures menu ----
        creatures_menu = menubar.addMenu("Creatures")

        add_action = QAction("Add Creature...", self)
        add_action.triggered.connect(self._add_creature_dialog)
        creatures_menu.addAction(add_action)

        edit_all_action = QAction("Edit All Creatures...", self)
        edit_all_action.triggered.connect(self._edit_all_creatures)
        creatures_menu.addAction(edit_all_action)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _add_creature_dialog(self):
        """Add a new creature via the creature editor."""
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
                # Add token to map
                if creature.token_path:
                    pixmap = QPixmap(creature.token_path)
                else:
                    pixmap = QPixmap(64, 64)
                    pixmap.fill(QColor("#e94560"))
                token = TokenItem(pixmap, creature.name, self.view.grid_size,
                                  creature.token_scale, creature=creature, viewer=self)
                self.view._scene.addItem(token)
                token.setPos(0, 0)
                self.view.token_items.append(token)
                if self.initiative_panel:
                    self.initiative_panel.refresh()
        except ImportError:
            pass

    def _edit_all_creatures(self):
        """Show a list of all creatures to pick one to edit."""
        if not self.encounter or not self.encounter.creatures:
            return
        names = [f"{c.name} ({c.hp}/{c.hp_max} HP)" for c in self.encounter.creatures]
        name, ok = QInputDialog.getItem(self, "Edit Creature", "Select creature:", names, 0, False)
        if ok and name:
            idx = names.index(name)
            creature = self.encounter.creatures[idx]
            self.edit_creature(creature)

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

            self._right_dock = QDockWidget("Combat Controls", self)
            self._right_dock.setWidget(right_widget)
            self._right_dock.setMinimumWidth(250)
            self.addDockWidget(Qt.RightDockWidgetArea, self._right_dock)

            # Bottom dock: Combat log
            self.combat_log = CombatLog()
            self._log_dock = QDockWidget("Combat Log", self)
            self._log_dock.setWidget(self.combat_log)
            self._log_dock.setMaximumHeight(200)
            self.addDockWidget(Qt.BottomDockWidgetArea, self._log_dock)

            # Connect dice rolls to combat log
            self.dice_panel.dice_rolled.connect(self.combat_log.log_dice_roll)

            # Double-click initiative list -> edit creature
            self.initiative_panel.init_list.itemDoubleClicked.connect(self._on_init_double_click)

            # Pass combat_log to the view for token context menus
            self.view.combat_log = self.combat_log

        except ImportError as e:
            print(f"Warning: Could not load combat panels: {e}")

    def _on_init_double_click(self, item):
        """Double-click a creature in the initiative list to edit it."""
        creature_id = item.data(Qt.UserRole)
        if creature_id and self.encounter:
            creature = self.encounter.get_creature(creature_id)
            if creature:
                self.edit_creature(creature)

    def _on_turn_advanced(self):
        if self.encounter and self.combat_log:
            active = self.encounter.creatures[self.encounter.active_creature_index] \
                if 0 <= self.encounter.active_creature_index < len(self.encounter.creatures) else None
            if active:
                self.combat_log.log_turn(active.name, self.encounter.round_number)
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
                for token in self.view.token_items:
                    if token.creature and token.creature.id == creature.id:
                        token.update_visuals()
                if self.initiative_panel:
                    self.initiative_panel.refresh()
                self.schedule_save()
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
        self.schedule_save()

    def refresh_all_tokens(self):
        for token in self.view.token_items:
            token.update_visuals()
        if self.initiative_panel:
            self.initiative_panel.refresh()

    def schedule_save(self):
        """Debounced save — waits 1s after last change to avoid rapid writes."""
        if self.folder_path and self.encounter:
            self._save_timer.start()

    def _save_creatures(self):
        """Persist creature data into the folder's config.json."""
        if not self.folder_path or not self.encounter:
            return
        config_path = os.path.join(self.folder_path, "config.json")
        try:
            cfg = {}
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
            # Save creature list
            cfg["creatures"] = [c.to_dict() for c in self.encounter.creatures]
            with open(config_path, 'w') as f:
                json.dump(cfg, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not save creatures: {e}")

    def keyPressEvent(self, event: QKeyEvent):
        self.view.keyPressEvent(event)


class _MapGraphicsView(QGraphicsView):
    """The actual QGraphicsView that renders the map and tokens."""

    def __init__(self, map_path, width_sq, height_sq, tokens_to_add, map_scale=1.0,
                 encounter=None, parent_viewer=None, skip_creature_creation=False):
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

        # Add tokens (skip creature creation if we loaded from config)
        if not skip_creature_creation:
            self._add_tokens(tokens_to_add)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        QTimer.singleShot(200, self.fit_to_screen)

    def _add_tokens(self, tokens_to_add):
        """Add tokens to the scene, creating new CreatureState objects."""
        col_offset = 0
        for token_data, (count, token_scale) in tokens_to_add.items():
            pixmap = QPixmap(token_data.path)
            for i in range(count):
                creature = None
                if self.encounter:
                    try:
                        from core.game_state import CreatureState
                        base_name = token_data.name.split('.')[0]
                        if len(base_name) > 20:
                            parts = base_name.split('_')
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

        # Auto-save initial creatures
        if self.parent_viewer:
            self.parent_viewer.schedule_save()

    def _create_tokens_from_encounter(self, tokens_to_add):
        """Create token visuals for creatures loaded from config.json."""
        if not self.encounter:
            return

        # Build a lookup: token filename -> (pixmap, scale) from tokens_to_add
        token_lookup = {}
        for token_data, (count, token_scale) in tokens_to_add.items():
            token_lookup[token_data.path] = (QPixmap(token_data.path), token_scale)

        for creature in self.encounter.creatures:
            # Find matching pixmap by token_path
            if creature.token_path and creature.token_path in token_lookup:
                pixmap, _ = token_lookup[creature.token_path]
            elif creature.token_path:
                pixmap = QPixmap(creature.token_path)
            else:
                pixmap = QPixmap(64, 64)
                pixmap.fill(QColor("#e94560"))

            token = TokenItem(pixmap, creature.name, self.grid_size,
                              creature.token_scale, creature=creature,
                              viewer=self.parent_viewer)
            self._scene.addItem(token)
            # Place at saved grid position
            gx, gy = creature.position
            token.setPos(gx * self.grid_size, gy * self.grid_size)
            self.token_items.append(token)

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

                scene_pos = self.mapToScene(view_pos)
                if creature.token_path:
                    pixmap = QPixmap(creature.token_path)
                else:
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
