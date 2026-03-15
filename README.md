# D&D Interactive Map App

A professional D&D map viewer with automated folder scanning, grid-snapping, and token management.

## Setup
1. Install Python 3.8+
2. Install dependencies:
   ```bash
   pip install PySide6 watchdog pillow
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Controls
- **Select Folder/Map:** Use the launcher to choose your adventure.
- **Set Counts:** Adjust how many of each character/enemy to spawn.
- **Launch:** Click "Launch Map" to enter interactive mode.
- **Grid Toggle:** Press **'G'** to show/hide the grid lines.
- **Full Screen Toggle:** Press **'F'** to enter/exit full-screen.
- **Zoom:** Use the **Mouse Wheel** to zoom in and out.
- **Pan:** **Click and Drag** the background to move the map.
- **Move Tokens:** **Click and Drag** characters to move them; they will snap to the nearest grid square center.
- **Exit:** Press **'Esc'** to return to the launcher.

## Auto-Detection
- **Maps:** Files with dimensions in the name (e.g., `22x16`) are automatically detected as maps.
- **Characters:** PNG files without dimensions are treated as tokens/characters.
- **Auto-Sync:** Adding a new folder or file to the base directory will automatically refresh the launcher list.
