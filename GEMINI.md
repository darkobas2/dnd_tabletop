# D&D Interactive Tabletop Simulator — Gemini Guide

## What This Project Is
A virtual tabletop (VTT) simulator for D&D built in Python. It scans folders for maps and tokens, provides a launcher GUI, and renders encounters in either 2D (PySide6/Qt) or 3D (Ursina/Panda3D). The vision: a fully immersive tabletop experience that bridges physical miniatures feel with digital convenience.

## Project Structure
```
DND/
├── main.py              # Entry point, app orchestrator
├── launcher.py          # PySide6 launcher GUI (folder/map/token selection)
├── scanner.py           # Auto-detects maps & tokens from filesystem
├── viewer.py            # 2D interactive map viewer (Qt Graphics)
├── viewer_3d.py         # 3D tabletop viewer (Ursina engine, runs as subprocess)
├── requirements.txt     # PySide6, watchdog, pillow, ursina, opencv-python
├── CLAUDE.md            # Claude Code project context
├── .claude/agents/      # Claude Code subagents (ursina-developer, graphic-designer)
└── <Encounter_Folders>/ # Each folder = one encounter
    ├── config.json      # Grid config, token counts/sizes, AI scan data
    ├── *.jpg            # Map images (detected by WxH pattern in filename)
    └── *.png            # Token images
```

## How It Works
1. **Scanner** crawls the project directory for encounter folders containing maps + tokens
2. **Watchdog** monitors filesystem for live updates
3. **Launcher** presents a GUI to pick encounters, configure tokens, and choose 2D or 3D
4. **2D Viewer** — QGraphicsView with grid overlay, drag-to-move tokens, zoom/pan
5. **3D Viewer** — Ursina app launched as subprocess (config via tempfile JSON), 3D standee tokens on a textured floor with grid and reconstructed walls

## Key Technical Details
- **3D viewer is a subprocess** — Qt and Ursina/Panda3D OpenGL contexts conflict, so viewer_3d.py runs independently
- **Map detection heuristic** — files with `NNxNN` in name or keywords like "map", "ambush", "floor"
- **Token detection** — PNGs that don't match map patterns
- **Config persistence** — per-folder `config.json` stores grid dimensions, token counts/sizes, wall scan data
- **AI Scan** — OpenCV adaptive thresholding + Hough line detection for wall/structure identification

## Dependencies
PySide6, watchdog, pillow, ursina, opencv-python

## What Needs Work
- **Networking** — No multiplayer yet. Need player/DM client architecture.
- **Game Mechanics** — No dice, initiative tracker, HP bars, spell effects, or combat log.
- **Asset Pipeline** — Manual token import. Need integrated token creator/editor.
- **3D Polish** — Lighting, terrain elevation, fog of war, line-of-sight.
- **AI Scan** — Wall detection works but needs tuning for different map styles.
- **Performance** — Large maps with many tokens need optimization.
- **Audio** — No ambient sound or music integration.

## Guidelines for Contributing
- Maintain feature parity between 2D and 3D where feasible
- Keep 3D code subprocess-compatible (no shared memory with Qt process)
- Update config.json schema docs when adding new persistent fields
- Test against Bandit_Ambush_5 encounter as the reference scenario
- Python 3.8+ compatibility
