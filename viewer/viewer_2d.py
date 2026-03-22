"""2D Map Viewer with grid overlay, draggable tokens, combat panels, and fog of war."""

import os
import json

from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QMainWindow,
                                QDockWidget, QMenu, QInputDialog, QSplitter,
                                QWidget, QVBoxLayout, QMenuBar, QLabel)
from PySide6.QtGui import QPixmap, QColor, QPen, QBrush, QKeyEvent, QPainter, QAction
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal

from viewer.token_item import TokenItem
from viewer.effect_item import EffectItem, PlaceEffectDialog


class MapViewer(QMainWindow):
    """Full-featured 2D map viewer with dockable combat panels."""

    # Signal for cross-thread token moves from player view server
    _player_move_signal = Signal(str, int, int)

    def __init__(self, map_path, width_sq, height_sq, tokens_to_add, map_scale=1.0,
                 encounter=None, folder_path=None):
        super().__init__()
        self._player_move_signal.connect(self._apply_player_move)
        self.setWindowTitle("D&D Map Viewer")

        self.encounter = encounter
        self.folder_path = folder_path
        self.combat_log = None
        self.dice_panel = None
        self.initiative_panel = None
        self.token_items = []
        self.effect_items = []
        self._right_dock = None
        self._log_dock = None
        self._map_path = map_path
        self._server = None
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(1000)  # Debounce: save 1s after last change
        self._save_timer.timeout.connect(self._save_creatures)

        # Merge saved creatures with launcher token config:
        # Use launcher's counts but preserve saved creature stats (name, HP, AC, etc.)
        saved_creatures = list(encounter.creatures) if encounter else []
        encounter.creatures.clear()

        # Central widget: the map view (always creates fresh from launcher config)
        self.view = _MapGraphicsView(map_path, width_sq, height_sq, tokens_to_add,
                                      map_scale, encounter, self,
                                      saved_creatures=saved_creatures)
        self.setCentralWidget(self.view)

        # Setup dock panels
        self._setup_panels()

        # Setup menu bar
        self._setup_menu()

        # Load saved effects
        self._load_saved_effects()

        # Floating exit button (visible in fullscreen)
        from PySide6.QtWidgets import QPushButton
        self._exit_btn = QPushButton("Exit", self)
        self._exit_btn.setFixedSize(70, 30)
        self._exit_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(180, 40, 40, 180);
                color: white; font-weight: bold; font-size: 12px;
                border: 1px solid #888; border-radius: 4px;
            }
            QPushButton:hover { background-color: rgba(220, 50, 50, 220); }
        """)
        self._exit_btn.clicked.connect(self.close)
        self._exit_btn.raise_()

        # Copyright notice
        self._credit_label = QLabel("Token art \u00a9 2minutetabletop.com", self)
        self._credit_label.setStyleSheet("color: rgba(255,255,255,80); font-size: 9px; background: transparent;")
        self._credit_label.setFixedHeight(14)

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

        view_menu.addSeparator()
        exit_action = QAction("Exit to Launcher (Esc)", self)
        exit_action.triggered.connect(self.close)
        view_menu.addAction(exit_action)

        # ---- Creatures menu ----
        creatures_menu = menubar.addMenu("Creatures")

        add_action = QAction("Add Creature...", self)
        add_action.triggered.connect(self._add_creature_dialog)
        creatures_menu.addAction(add_action)

        edit_all_action = QAction("Edit All Creatures...", self)
        edit_all_action.triggered.connect(self._edit_all_creatures)
        creatures_menu.addAction(edit_all_action)

        # ---- Summons menu ----
        summons_menu = menubar.addMenu("Summons")
        self._build_summons_menu(summons_menu)

        # ---- Effects menu ----
        effects_menu = menubar.addMenu("Effects")
        self._build_effects_menu(effects_menu)

        # ---- Network menu ----
        net_menu = menubar.addMenu("Network")

        self._host_action = QAction("Host Player View...", self)
        self._host_action.triggered.connect(self._toggle_host)
        net_menu.addAction(self._host_action)

        self._show_qr_action = QAction("Show QR Code", self)
        self._show_qr_action.triggered.connect(self._show_qr)
        self._show_qr_action.setEnabled(False)
        net_menu.addAction(self._show_qr_action)

    def _toggle_host(self):
        """Start or stop the player view server."""
        if hasattr(self, '_server') and self._server:
            self._server.stop()
            self._server = None
            self._host_action.setText("Host Player View...")
            self._show_qr_action.setEnabled(False)
            if self.combat_log:
                self.combat_log.add_entry("info", "Player view server stopped")
            return

        try:
            from net.server import PlayerViewServer
            self._server = PlayerViewServer(port=8080, on_token_moved=self._on_player_token_moved)
            if self.encounter:
                map_path = ""
                if self.view.base_pixmap:
                    # Get the original map path from the view
                    map_path = getattr(self, '_map_path', '')
                self._server.set_encounter(
                    self.encounter, map_path,
                    self.view.width_sq, self.view.height_sq
                )
            self._server.start()
            url = self._server.get_url()
            self._host_action.setText(f"Stop Hosting ({url})")
            self._show_qr_action.setEnabled(True)
            if self.combat_log:
                self.combat_log.add_entry("info", f"Player view live at {url}")

            # Start broadcasting state periodically
            self._broadcast_timer = QTimer(self)
            self._broadcast_timer.setInterval(2000)
            self._broadcast_timer.timeout.connect(self._broadcast_to_players)
            self._broadcast_timer.start()

        except Exception as e:
            if self.combat_log:
                self.combat_log.add_entry("info", f"Server error: {e}")
            print(f"Server error: {e}")
            import traceback; traceback.print_exc()

    def _broadcast_to_players(self):
        if hasattr(self, '_server') and self._server:
            if self.encounter:
                map_path = getattr(self, '_map_path', '')
                self._server.set_encounter(
                    self.encounter, map_path,
                    self.view.width_sq, self.view.height_sq
                )
            self._server.broadcast_state()

    def _on_player_token_moved(self, creature_id, gx, gy):
        """Called from server thread when a player moves their token via web view."""
        # Emit signal to safely cross from server thread to Qt main thread
        self._player_move_signal.emit(creature_id, gx, gy)

    def _apply_player_move(self, creature_id, gx, gy):
        """Apply a player's token move to the 2D view (main thread)."""
        print(f"[DM View] Applying player move: {creature_id} -> ({gx}, {gy})")
        found = False
        for token in self.view.token_items:
            if token.creature and token.creature.id == creature_id:
                token.creature.position = (gx, gy)
                token.setPos(gx * self.view.grid_size, gy * self.view.grid_size)
                found = True
                print(f"[DM View] Token updated: {token.creature.name}")
                break
        if not found:
            print(f"[DM View] WARNING: No token found for creature {creature_id}")
        self.schedule_save()

    def _show_qr(self):
        """Show QR code in a dialog."""
        if not hasattr(self, '_server') or not self._server:
            return
        try:
            qr_path = self._server.get_qr_code_path()
            if qr_path:
                from PySide6.QtWidgets import QDialog, QLabel
                dlg = QDialog(self)
                dlg.setWindowTitle("Player Connection QR Code")
                dlg.setMinimumSize(350, 400)
                layout = QVBoxLayout(dlg)

                url = self._server.get_url()
                url_label = QLabel(f'<h3>Players connect to:</h3><h2 style="color:#f39c12">{url}</h2>')
                url_label.setAlignment(Qt.AlignCenter)
                url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                layout.addWidget(url_label)

                qr_label = QLabel()
                qr_pixmap = QPixmap(qr_path)
                qr_label.setPixmap(qr_pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                qr_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(qr_label)

                hint = QLabel("Scan with phone camera to open player view")
                hint.setAlignment(Qt.AlignCenter)
                hint.setStyleSheet("color: #aaa;")
                layout.addWidget(hint)

                dlg.exec()
        except Exception as e:
            print(f"QR error: {e}")

    def _build_effects_menu(self, menu):
        """Build the Effects menu with categorized spell/hazard effects."""
        try:
            from core.effects import get_effects_by_category, EFFECT_CATALOG

            by_cat = get_effects_by_category()
            for cat in sorted(by_cat.keys()):
                sub = menu.addMenu(cat)
                for name in by_cat[cat]:
                    action = QAction(name, self)
                    effect_data = EFFECT_CATALOG[name]
                    action.triggered.connect(
                        lambda checked, n=name, d=effect_data: self._place_effect_center(n, d)
                    )
                    sub.addAction(action)

            menu.addSeparator()
            clear_action = QAction("Clear All Effects", self)
            clear_action.triggered.connect(self._clear_all_effects)
            menu.addAction(clear_action)
        except ImportError:
            pass

    def _place_effect_center(self, name, effect_data):
        """Place an effect at the center of the current view (from menu bar)."""
        center = self.view.mapToScene(self.view.viewport().rect().center())
        gx = int(center.x() / self.view.grid_size)
        gy = int(center.y() / self.view.grid_size)
        self._add_effect_at(name, effect_data, gx, gy)

    def _add_effect_at(self, name, effect_data, gx, gy):
        """Show placement dialog, then create a MapEffect and add it to the scene."""
        dialog = PlaceEffectDialog(name, effect_data, self)
        if not dialog.exec():
            return

        from core.game_state import MapEffect
        effect = MapEffect(
            name=name,
            shape=effect_data["shape"],
            position=(gx, gy),
            radius=dialog.get_radius(),
            color=effect_data["color"],
            opacity=effect_data["opacity"],
            animation=effect_data.get("animation"),
            rotation=float(dialog.get_rotation()),
        )
        if self.encounter:
            self.encounter.add_effect(effect)

        item = EffectItem(effect, self.view.grid_size, viewer=self)
        self.view._scene.addItem(item)
        self.effect_items.append(item)
        self.schedule_save()

        if self.combat_log:
            self.combat_log.add_entry("effect", f"{name} ({effect.radius} sq) placed at ({gx}, {gy})")

    def remove_effect(self, effect_item):
        """Remove an effect from the map."""
        effect_item.cleanup()
        if effect_item in self.effect_items:
            self.effect_items.remove(effect_item)
        if effect_item.effect and self.encounter:
            self.encounter.remove_effect(effect_item.effect.id)
        self.view._scene.removeItem(effect_item)
        self.schedule_save()

    def _clear_all_effects(self):
        """Remove all effects from the map."""
        for item in list(self.effect_items):
            self.remove_effect(item)

    def _load_saved_effects(self):
        """Restore effects from saved encounter state."""
        if not self.encounter:
            return
        for effect in self.encounter.effects:
            item = EffectItem(effect, self.view.grid_size, viewer=self)
            self.view._scene.addItem(item)
            self.effect_items.append(item)

    # -- Summons -----------------------------------------------------------

    def _build_summons_menu(self, menu):
        """Build the Summons menu with categorized summonables."""
        try:
            from core.summons import get_summons_by_category, SUMMON_CATALOG

            by_cat = get_summons_by_category()
            for cat in sorted(by_cat.keys()):
                sub = menu.addMenu(cat)
                for name in by_cat[cat]:
                    action = QAction(name, self)
                    sdata = SUMMON_CATALOG[name]
                    action.triggered.connect(
                        lambda checked, n=name, d=sdata: self._place_summon_center(n, d)
                    )
                    sub.addAction(action)
        except ImportError:
            pass

    def _place_summon_center(self, name, sdata):
        """Place a summon at the center of the current view (from menu bar)."""
        center = self.view.mapToScene(self.view.viewport().rect().center())
        gx = int(center.x() / self.view.grid_size)
        gy = int(center.y() / self.view.grid_size)
        self._add_summon_at(name, sdata, gx, gy)

    def _add_summon_at(self, name, sdata, gx, gy):
        """Show dialog, then create a summoned creature and add it to the map."""
        from PySide6.QtWidgets import (QDialog, QFormLayout, QSpinBox,
                                        QComboBox, QPushButton, QHBoxLayout)
        from core.summons import SIZE_SCALES

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Summon: {name}")
        dlg.setMinimumWidth(320)
        form = QFormLayout(dlg)

        form.addRow("Creature:", QLabel(f"<b>{name}</b>"))

        hp_spin = QSpinBox()
        hp_spin.setRange(1, 9999)
        hp_spin.setValue(sdata["hp"])
        form.addRow("HP:", hp_spin)

        ac_spin = QSpinBox()
        ac_spin.setRange(0, 30)
        ac_spin.setValue(sdata["ac"])
        form.addRow("AC:", ac_spin)

        # Summoner picker — list of player characters
        summoner_combo = QComboBox()
        summoner_combo.addItem("(No owner)", "")
        if self.encounter:
            for c in self.encounter.creatures:
                if c.is_player:
                    summoner_combo.addItem(c.name, c.id)
        form.addRow("Summoner:", summoner_combo)

        # Buttons
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Summon")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        form.addRow(btn_row)

        if not dlg.exec():
            return

        from core.game_state import CreatureState

        summoner_id = summoner_combo.currentData() or ""
        # Determine glow color from summoner or summon data
        summon_color = sdata.get("color", "#ffd700")

        size = sdata.get("size", "Medium")
        scale = SIZE_SCALES.get(size, 1.0)

        creature = CreatureState(
            name=name,
            hp=hp_spin.value(),
            hp_max=hp_spin.value(),
            ac=ac_spin.value(),
            speed=sdata.get("speed", 30),
            size_category=size,
            position=(gx, gy),
            token_scale=scale,
            summoned_by=summoner_id,
            summon_color=summon_color,
            notes=sdata.get("notes", ""),
        )
        self.encounter.add_creature(creature)

        # Look for token image in summon_tokens/ folder
        import os as _os
        base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        safe_name = name.replace(' ', '_').replace('(', '').replace(')', '').replace("'", '')
        token_path = _os.path.join(base, 'summon_tokens', f'{safe_name}.png')

        if _os.path.isfile(token_path):
            pixmap = QPixmap(token_path)
            creature.token_path = token_path
        else:
            # Fallback: colored circle with initial
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.transparent)
            from PySide6.QtGui import QPainter as _P
            p = _P(pixmap)
            p.setRenderHint(_P.Antialiasing)
            color = QColor(summon_color)
            color.setAlpha(200)
            p.setBrush(QBrush(color))
            p.setPen(QPen(QColor(255, 255, 255, 180), 2))
            p.drawEllipse(4, 4, 56, 56)
            font = p.font()
            font.setPointSize(24)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor(255, 255, 255))
            p.drawText(QRectF(0, 0, 64, 64), Qt.AlignCenter, name[0].upper())
            p.end()

        token = TokenItem(pixmap, name, self.view.grid_size, scale,
                          creature=creature, viewer=self)
        self.view._scene.addItem(token)
        token.setPos(gx * self.view.grid_size, gy * self.view.grid_size)
        self.view.token_items.append(token)

        if self.initiative_panel:
            self.initiative_panel.refresh()
        self.schedule_save()

        if self.combat_log:
            summoner_name = summoner_combo.currentText()
            if summoner_id:
                self.combat_log.add_entry("summon", f"{summoner_name} summoned {name}")
            else:
                self.combat_log.add_entry("summon", f"{name} summoned")

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
            # Save creature list and effects
            cfg["creatures"] = [c.to_dict() for c in self.encounter.creatures]
            cfg["effects"] = [e.to_dict() for e in self.encounter.effects]
            with open(config_path, 'w') as f:
                json.dump(cfg, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not save creatures: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_exit_btn'):
            self._exit_btn.move(self.width() - self._exit_btn.width() - 10, 8)
            self._exit_btn.raise_()
        if hasattr(self, '_credit_label'):
            self._credit_label.move(self.width() - 180, self.height() - 18)

    def closeEvent(self, event):
        """Clean up server and effects on close."""
        if hasattr(self, '_server') and self._server:
            self._server.stop()
        if hasattr(self, '_broadcast_timer') and self._broadcast_timer:
            self._broadcast_timer.stop()
        # Stop effect animations
        for item in self.effect_items:
            item.cleanup()
        # Final save
        self._save_creatures()
        super().closeEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        self.view.keyPressEvent(event)


class _MapGraphicsView(QGraphicsView):
    """The actual QGraphicsView that renders the map and tokens."""

    def __init__(self, map_path, width_sq, height_sq, tokens_to_add, map_scale=1.0,
                 encounter=None, parent_viewer=None, saved_creatures=None):
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

        # Add tokens, merging with any saved creature data
        self._saved_creatures = saved_creatures or []
        self._add_tokens(tokens_to_add)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        QTimer.singleShot(200, self.fit_to_screen)

    def _add_tokens(self, tokens_to_add):
        """Add tokens to the scene. Merges saved creature stats when available."""
        # Build lookup of saved creatures by token_path for merging
        saved_by_path = {}
        for sc in self._saved_creatures:
            saved_by_path.setdefault(sc.token_path, []).append(sc)

        col_offset = 0
        for token_data, token_cfg in tokens_to_add.items():
            if len(token_cfg) == 3:
                count, token_scale, creature_cfg = token_cfg
            else:
                count, token_scale = token_cfg[0], token_cfg[1]
                creature_cfg = {}

            pixmap = QPixmap(token_data.path)
            saved_list = saved_by_path.get(token_data.path, [])

            for i in range(count):
                creature = None
                if self.encounter:
                    try:
                        from core.game_state import CreatureState
                        from core.name_utils import extract_creature_name

                        if i < len(saved_list):
                            # Reuse saved creature (preserves name, HP, AC, conditions, etc.)
                            creature = saved_list[i]
                            creature.token_scale = token_scale
                        else:
                            # Create new creature from launcher config
                            base_name = creature_cfg.get("name", "")
                            if not base_name:
                                base_name = extract_creature_name(token_data.name)
                            display_name = f"{base_name}" if count == 1 else f"{base_name} {i+1}"
                            hp = creature_cfg.get("hp", 10)
                            ac = creature_cfg.get("ac", 10)
                            is_player = creature_cfg.get("is_player", False)
                            creature = CreatureState(
                                name=display_name,
                                hp=hp, hp_max=hp, ac=ac,
                                is_player=is_player,
                                token_path=token_data.path,
                                token_scale=token_scale,
                                position=(col_offset + i, 0)
                            )
                            # Link familiar to owner
                            familiar_of = creature_cfg.get("familiar_of", "")
                            if familiar_of:
                                for c in self.encounter.creatures:
                                    if c.name == familiar_of and c.is_player:
                                        creature.summoned_by = c.id
                                        creature.summon_color = "#d2b48c"
                                        break
                        self.encounter.add_creature(creature)
                    except ImportError:
                        pass

                token = TokenItem(pixmap, token_data.name, self.grid_size, token_scale,
                                  creature=creature, viewer=self.parent_viewer)
                self._scene.addItem(token)
                # Use saved position if available, otherwise default
                if creature and creature.position != (0, 0):
                    gx, gy = creature.position
                    token.setPos(gx * self.grid_size, gy * self.grid_size)
                else:
                    token.setPos((col_offset + i) * self.grid_size, 0)
                self.token_items.append(token)
            col_offset += count

        # Auto-save
        if self.parent_viewer:
            self.parent_viewer.schedule_save()

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
        # Let TokenItem and EffectItem handle their own context menus
        if isinstance(item, TokenItem) or (item and item.parentItem() and isinstance(item.parentItem(), TokenItem)):
            super().contextMenuEvent(event)
            return
        if isinstance(item, EffectItem):
            super().contextMenuEvent(event)
            return

        menu = QMenu(self)
        add_creature_action = menu.addAction("Add Creature Here...")

        # Effects submenu in context menu
        effects_sub = menu.addMenu("Place Effect Here...")
        self._build_context_effects_menu(effects_sub, event.pos())

        # Summons submenu in context menu
        summons_sub = menu.addMenu("Summon Here...")
        self._build_context_summons_menu(summons_sub, event.pos())

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

    def _build_context_effects_menu(self, menu, view_pos):
        """Build categorized effects submenu for right-click placement."""
        try:
            from core.effects import get_effects_by_category, EFFECT_CATALOG

            scene_pos = self.mapToScene(view_pos)
            gx = int(scene_pos.x() / self.grid_size)
            gy = int(scene_pos.y() / self.grid_size)

            by_cat = get_effects_by_category()
            for cat in sorted(by_cat.keys()):
                sub = menu.addMenu(cat)
                for name in by_cat[cat]:
                    action = sub.addAction(name)
                    effect_data = EFFECT_CATALOG[name]
                    action.triggered.connect(
                        lambda checked, n=name, d=effect_data, x=gx, y=gy:
                            self.parent_viewer._add_effect_at(n, d, x, y)
                            if self.parent_viewer else None
                    )
        except ImportError:
            pass

    def _build_context_summons_menu(self, menu, view_pos):
        """Build categorized summons submenu for right-click placement."""
        try:
            from core.summons import get_summons_by_category, SUMMON_CATALOG

            scene_pos = self.mapToScene(view_pos)
            gx = int(scene_pos.x() / self.grid_size)
            gy = int(scene_pos.y() / self.grid_size)

            by_cat = get_summons_by_category()
            for cat in sorted(by_cat.keys()):
                sub = menu.addMenu(cat)
                for name in by_cat[cat]:
                    action = sub.addAction(name)
                    sdata = SUMMON_CATALOG[name]
                    action.triggered.connect(
                        lambda checked, n=name, d=sdata, x=gx, y=gy:
                            self.parent_viewer._add_summon_at(n, d, x, y)
                            if self.parent_viewer else None
                    )
        except ImportError:
            pass
