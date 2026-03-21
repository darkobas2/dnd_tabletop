# D&D Interactive Tabletop Simulator

## Project Overview
A real-time D&D tabletop simulator with 2D PySide6 rendering, automated map/token scanning, interactive web-based player view, and full combat mechanics (dice, initiative, HP/conditions tracking). The goal is a fully playable virtual tabletop that feels like a physical miniatures game.

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
net/               — Networking (WebSocket + HTTP player view server)
  server.py        — PlayerViewServer: interactive web player view with token dragging
player_sprites/    — Player character sprite PNGs (shared across encounters)
main.py            — App orchestrator
scanner.py         — Filesystem scanner + watchdog monitor
launcher.py        — Adventure/map/token/player-character selection GUI
```

### Data Flow
```
Filesystem → DNDScanner → LauncherWindow → 2D MapViewer
                ↑                ↓                ↓
           Watchdog FS     config.json     EncounterState → PlayerViewServer (WebSocket)
                                                ↓                    ↕
                                          Combat Panels        Player Browsers
                                    (Dice, Initiative, Log)  (move tokens via web)
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
- **Player View:** WebSocket + HTTP (websockets library), HTML5 Canvas
- **Images:** Pillow
- **File Monitoring:** watchdog
- **Python:** 3.8+

## Key Conventions
- Config is stored per-folder in `config.json` with maps, tokens, and player_sprites sections
- Player sprites live in `player_sprites/` folder at project root (shared across encounters)
- Grid dimensions auto-calculated from image aspect ratio if not in filename
- Token detection: PNGs without `WxH` pattern and without map keywords
- Map detection: files with `WxH` in name OR containing "map", "ambush", "floor", "room"
- All token positioning uses grid-snap (nearest cell center)
- `core/` modules are pure Python with JSON serialization — no PySide6 imports
- EncounterState is created per session and passed to the 2D viewer
- Dark fantasy theme applied globally via `ui.theme.apply_theme(app)`
- Player view: players can drag their own tokens (is_player=True), server relays to DM

## Development Guidelines
- Test with the Bandit_Ambush_5 encounter folder as reference
- When adding new features, update config.json schema if persistence is needed
- Right-click tokens for damage/heal/conditions/visibility context menu
- Combat panels (dice, initiative, log) are QDockWidgets in the 2D viewer

## Subagents
- **graphic-designer** — Asset creation, UI/UX design, token/map art direction

## Current State
- Single encounter (Bandit_Ambush_5) with 2 map variants and 3 token types
- 2D viewer with grid, draggable tokens, HP bars, condition icons, context menus
- Interactive player view: web-based, players can move their own tokens
- Player sprites system: DM picks characters from player_sprites/ folder per encounter
- Dice engine: parses 2d6+3, 1d20adv, 4d6kh3, complex expressions
- Initiative tracker: roll, sort, advance/rewind turns, skip dead creatures
- Combat log: timestamped, filterable by event type
- Creature editor: full stat block dialog
- Dark fantasy theme applied to all UI
- No fog of war painting yet
- No measurement ruler or AoE templates yet
