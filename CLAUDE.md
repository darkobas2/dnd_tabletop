# D&D Interactive Tabletop Simulator

## Project Overview
A real-time D&D tabletop simulator with dual rendering (2D PySide6 + 3D Ursina/Panda3D), automated map/token scanning, AI-powered wall detection, and full combat mechanics (dice, initiative, HP/conditions tracking). The goal is a fully playable virtual tabletop that feels like a physical miniatures game.

## Architecture

### Package Structure
```
core/              — Pure Python game logic (no UI imports)
  game_state.py    — CreatureState, DiceResult, EncounterState (single source of truth)
  dice.py          — Dice expression parser & roller (2d6+3, 1d20adv, 4d6kh3)
  initiative.py    — Initiative rolling, sorting, turn management
  conditions.py    — 5e conditions with colors and icons
ui/                — PySide6 widgets and theme
  theme.py         — Dark fantasy QSS stylesheet and color constants
  widgets/         — Reusable panels
    dice_panel.py       — Quick-roll buttons, custom expressions, roll history
    initiative_panel.py — Initiative order display, turn controls
    combat_log.py       — Timestamped filterable event log
    creature_editor.py  — Stat block editor dialog
viewer/            — 2D map rendering
  viewer_2d.py     — QMainWindow with QGraphicsView, dockable combat panels
  token_item.py    — Draggable tokens with HP bars, conditions, context menus
viewer_3d/         — 3D rendering (placeholder for future split)
net/               — Networking (placeholder for future WebSocket implementation)
main.py            — App orchestrator
scanner.py         — Filesystem scanner + watchdog monitor
launcher.py        — Adventure/map/token selection GUI
ipc_bridge.py      — TCP socket IPC between Qt parent and Ursina 3D subprocess
viewer_3d.py       — 3D Ursina viewer (subprocess, uses IPC bridge)
```

### Data Flow
```
Filesystem → DNDScanner → LauncherWindow → [2D MapViewer | 3D DNDMap3D subprocess]
                ↑                ↓                ↓              ↑
           Watchdog FS     config.json     EncounterState    IPCBridge
                                                ↓
                                          Combat Panels
                                    (Dice, Initiative, Log)
```

### Adventure Folder Structure
Each encounter lives in its own folder:
```
Encounter_Name/
├── config.json          # Grid overrides, token counts/sizes, scan_data
├── *map*.jpg            # Map images (detected by WxH pattern or keywords)
└── *token*.png          # Token images (PNGs without map indicators)
```

## Tech Stack
- **GUI:** PySide6 (Qt6)
- **3D Engine:** Ursina (Panda3D wrapper)
- **Computer Vision:** OpenCV (wall/structure detection)
- **Images:** Pillow
- **File Monitoring:** watchdog
- **Python:** 3.8+

## Key Conventions
- Config is stored per-folder in `config.json` with maps and tokens sections
- 3D viewer runs as a subprocess to avoid Qt/OpenGL conflicts — IPC via TCP socket
- Grid dimensions auto-calculated from image aspect ratio if not in filename
- Token detection: PNGs without `WxH` pattern and without map keywords
- Map detection: files with `WxH` in name OR containing "map", "ambush", "floor", "room"
- All token positioning uses grid-snap (nearest cell center)
- `core/` modules are pure Python with JSON serialization — no PySide6 imports
- EncounterState is created per session and passed to the 2D viewer
- Dark fantasy theme applied globally via `ui.theme.apply_theme(app)`

## Development Guidelines
- Keep 2D and 3D viewers feature-parallel where possible
- Test with the Bandit_Ambush_5 encounter folder as reference
- When adding new features, update config.json schema if persistence is needed
- OpenCV scan results go into `scan_data` field per map in config.json
- Ursina code must remain subprocess-safe (no shared state with Qt)
- Right-click tokens for damage/heal/conditions/visibility context menu
- Combat panels (dice, initiative, log) are QDockWidgets in the 2D viewer

## Subagents
- **ursina-developer** — 3D engine specialist for viewer_3d.py and Ursina/Panda3D work
- **graphic-designer** — Asset creation, UI/UX design, token/map art direction

## Current State
- Single encounter (Bandit_Ambush_5) with 2 map variants and 3 token types
- 2D viewer with grid, draggable tokens, HP bars, condition icons, context menus
- 3D viewer with standee tokens, wall reconstruction, IPC bridge
- Dice engine: parses 2d6+3, 1d20adv, 4d6kh3, complex expressions
- Initiative tracker: roll, sort, advance/rewind turns, skip dead creatures
- Combat log: timestamped, filterable by event type
- Creature editor: full stat block dialog
- Dark fantasy theme applied to all UI
- AI scan implemented but scan_data mostly empty (needs tuning)
- No networking yet (Phase 5), no fog of war painting yet (Phase 3)
- No measurement ruler or AoE templates yet (Phase 2)
