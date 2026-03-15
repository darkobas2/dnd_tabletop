"""3D Ursina viewer for D&D maps — launched as subprocess from main.py.

Uses Ursina's EditorCamera (smooth, battle-tested controls):
  Right Drag    — Orbit around clicked point
  Middle Drag   — Pan
  Scroll        — Zoom (smooth)
  Left Click    — Select / drag token
  G             — Toggle grid
  Escape        — Quit
"""

from ursina import *
import json
import sys
import math
from pathlib import Path

try:
    from ipc_bridge import IPCClient
except ImportError:
    IPCClient = None


# ---------------------------------------------------------------------------
# Billboard Token — always faces camera, 3D base
# ---------------------------------------------------------------------------

class DNDToken3D(Entity):
    """A 3D token: billboard sprite (always faces camera) on a 3D base."""

    def __init__(self, texture_path, name, grid_x, grid_z, scale_val=1.0):
        p_path = Path(texture_path).absolute().as_posix()
        super().__init__(position=(grid_x, 0, grid_z))
        self.token_name = name
        self.creature_id = ""
        self._scale_val = scale_val

        tex = None
        try:
            tex = Texture(p_path)
        except Exception:
            print(f"Warning: Could not load texture {p_path}")

        s = scale_val

        # --- Base (cube disc since cylinder may not be available) ---
        self.base = Entity(
            parent=self,
            model='cube',
            color=color.rgb(50, 45, 40),
            scale=(s * 0.9, 0.1, s * 0.9),
            y=0.05,
            collider='box',
        )

        # --- Standee sprite (faces camera via update loop) ---
        self.sprite = Entity(
            parent=self,
            model='quad',
            texture=tex,
            scale=(s * 0.85, s * 0.85),
            y=s * 0.5 + 0.1,
            collider='box',
        )

        # Tag children for click detection
        self.sprite.parent_token = self
        self.base.parent_token = self

    def update(self):
        """Make the sprite always face the camera (billboard effect)."""
        if camera:
            self.sprite.look_at(camera.position, axis='y')
            self.sprite.rotation_x = 0
            self.sprite.rotation_z = 0

    def highlight(self, on=True):
        self.base.color = color.rgb(220, 200, 50) if on else color.rgb(50, 45, 40)

    def set_grid_pos(self, gx, gz, map_scale):
        self.x = (gx + 0.5) * map_scale
        self.z = (gz + 0.5) * map_scale
        self.y = 0


# ---------------------------------------------------------------------------
# Main 3D Map
# ---------------------------------------------------------------------------

class DNDMap3D:
    def __init__(self, config):
        self.app = Ursina(
            title=f"D&D 3D: {config['map_name']}",
            development_mode=False,
            editor_ui_enabled=False,
            borderless=False,
        )

        self.width_sq = config['width_sq']
        self.height_sq = config['height_sq']
        self.map_scale = config.get('map_scale', 1.0)
        ms = self.map_scale
        self.w = self.width_sq * ms
        self.h = self.height_sq * ms

        map_path = Path(config['map_path']).absolute().as_posix()
        map_tex = None
        try:
            map_tex = Texture(map_path)
        except Exception:
            pass

        # ---- Environment ----
        Sky(color=color.rgb(12, 12, 25))
        AmbientLight(color=color.rgba(210, 205, 220, 255))

        # Dark table under the map
        table_pad = 2
        Entity(
            model='cube',
            color=color.rgb(45, 30, 20),
            scale=(self.w + table_pad * 2, 0.4, self.h + table_pad * 2),
            position=(self.w / 2, -0.25, self.h / 2),
        )

        # Map floor (slightly raised)
        self.floor = Entity(
            model='quad',
            texture=map_tex,
            rotation=(90, 0, 0),
            scale=(self.w, self.h),
            collider='box',
            position=(self.w / 2, 0.01, self.h / 2),
        )

        # Wooden frame around map
        frame_h = 0.2
        frame_w = 0.1
        frame_col = color.rgb(70, 50, 30)
        for fx, fz, fsx, fsz in [
            (self.w / 2, -frame_w / 2, self.w + frame_w * 2, frame_w),
            (self.w / 2, self.h + frame_w / 2, self.w + frame_w * 2, frame_w),
            (-frame_w / 2, self.h / 2, frame_w, self.h),
            (self.w + frame_w / 2, self.h / 2, frame_w, self.h),
        ]:
            Entity(model='cube', color=frame_col,
                   scale=(fsx, frame_h, fsz), position=(fx, frame_h / 2 - 0.05, fz))

        # Grid
        self.grid = Entity(
            model=Grid(self.width_sq, self.height_sq),
            rotation=(90, 0, 0),
            scale=(self.w, self.h),
            position=self.floor.position,
            color=color.rgba(255, 255, 255, 25),
            y=0.02,
        )

        # ---- 3D geometry from scan data ----
        self.walls = []
        scan_data = config.get('scan_data', {})
        if 'walls' in scan_data:
            for wd in scan_data['walls']:
                self._create_wall(wd)
        if 'heightmap' in scan_data:
            self._create_terrain(scan_data['heightmap'])
        if 'structures' in scan_data:
            for s in scan_data['structures']:
                self._create_structure(s)

        # ---- EditorCamera — the real deal ----
        self.cam = EditorCamera(
            rotation_speed=200,
            pan_speed=Vec2(5, 5),
            move_speed=10,
            zoom_speed=1.25,
            zoom_smoothing=8,
            rotate_around_mouse_hit=True,  # Orbit around where you click!
        )
        # Position camera looking at map center
        self.cam.position = (self.w / 2, 0, self.h / 2)
        self.cam.rotation_x = 50
        camera.z = -max(self.w, self.h) * 1.2

        # ---- Tokens ----
        self.tokens = []
        start_x = 0
        for token_name, data in config['tokens'].items():
            count, token_scale, path = data
            for i in range(count):
                t = DNDToken3D(
                    texture_path=path,
                    name=token_name,
                    grid_x=(start_x + 0.5) * ms,
                    grid_z=0.5 * ms,
                    scale_val=token_scale * ms,
                )
                self.tokens.append(t)
                start_x += 1

        self.selected_token = None
        self.dragging = False

        # ---- IPC ----
        self.ipc = None
        ipc_port = config.get('ipc_port')
        if ipc_port and IPCClient:
            self.ipc = IPCClient(ipc_port, on_message=self._on_ipc)
            if not self.ipc.connect():
                self.ipc = None

        # ---- HUD ----
        Text(
            text='[RMB] Orbit  [MMB] Pan  [Scroll] Zoom  [LMB] Move token  [G] Grid',
            position=(-0.75, 0.48),
            scale=0.7,
            color=color.rgba(180, 180, 180, 100),
        )

    # ---- 3D World Generation ----

    def _create_wall(self, wall_data):
        sx, sy = wall_data['start']
        ex, ey = wall_data['end']
        h = wall_data.get('height', 3)
        ms = self.map_scale
        dist = math.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)
        if dist < 0.1:
            return

        thickness = 0.25
        wall = Entity(
            model='cube',
            color=color.rgb(100, 90, 80),
            scale=(dist * ms, h, thickness),
            position=((sx + ex) / 2 * ms, h / 2, (sy + ey) / 2 * ms),
            rotation_y=-math.degrees(math.atan2(ey - sy, ex - sx)),
            collider='box',
        )
        # Wall top cap (lighter edge)
        Entity(
            parent=wall,
            model='cube',
            color=color.rgb(130, 120, 110),
            scale=(1, 0.02, 1),
            y=0.5,
        )
        self.walls.append(wall)

    def _create_terrain(self, heightmap_data):
        """Create raised floor sections from heightmap data."""
        ms = self.map_scale
        for block in heightmap_data:
            x, z = block['x'] * ms, block['z'] * ms
            w, d = block.get('w', 1) * ms, block.get('d', 1) * ms
            h = block.get('h', 0.5)
            c = block.get('color', [80, 75, 70])
            Entity(
                model='cube',
                color=color.rgb(*c),
                scale=(w, h, d),
                position=(x + w / 2, h / 2, z + d / 2),
                collider='box',
            )

    def _create_structure(self, struct):
        """Create a structure (pillar, platform, etc.) from scan data."""
        ms = self.map_scale
        stype = struct.get('type', 'box')
        x = struct['x'] * ms
        z = struct['z'] * ms
        h = struct.get('h', 2)
        s = struct.get('size', 1) * ms
        c = struct.get('color', [90, 85, 80])

        if stype == 'pillar':
            Entity(model='cylinder', color=color.rgb(*c),
                   scale=(s * 0.3, h, s * 0.3), position=(x, h / 2, z))
        elif stype == 'platform':
            Entity(model='cube', color=color.rgb(*c),
                   scale=(s, h * 0.3, s), position=(x, h * 0.15, z))
        else:
            Entity(model='cube', color=color.rgb(*c),
                   scale=(s, h, s), position=(x, h / 2, z))

    # ---- IPC ----

    def _on_ipc(self, msg):
        if msg.get("type") == "token_move":
            cid = msg.get("creature_id")
            for t in self.tokens:
                if t.creature_id == cid:
                    t.set_grid_pos(msg.get("x", 0), msg.get("y", 0), self.map_scale)

    # ---- Frame update ----

    def update(self):
        if self.dragging and self.selected_token and mouse.world_point:
            self.selected_token.x = mouse.world_point.x
            self.selected_token.z = mouse.world_point.z
            self.selected_token.y = 0.3

    # ---- Input (only handles left-click for tokens + G/Esc) ----

    def input(self, key):
        if key == 'g':
            self.grid.enabled = not self.grid.enabled
        elif key == 'escape':
            if self.ipc:
                self.ipc.stop()
            application.quit()

        # Left click: select/drag tokens (EditorCamera does NOT use left-click)
        if key == 'left mouse down':
            hit = mouse.hovered_entity
            if hit:
                parent_tok = getattr(hit, 'parent_token', None)
                if parent_tok:
                    if self.selected_token and self.selected_token != parent_tok:
                        self.selected_token.highlight(False)
                    self.selected_token = parent_tok
                    self.selected_token.highlight(True)
                    self.dragging = True
                    return
            if self.selected_token:
                self.selected_token.highlight(False)
            self.selected_token = None
            self.dragging = False

        if key == 'left mouse up' and self.dragging and self.selected_token:
            self.dragging = False
            ms = self.map_scale
            gx = round(self.selected_token.x / ms - 0.5)
            gz = round(self.selected_token.z / ms - 0.5)
            self.selected_token.set_grid_pos(gx, gz, ms)
            if self.ipc:
                self.ipc.send({
                    "type": "token_moved",
                    "creature_id": self.selected_token.creature_id,
                    "x": gx, "y": gz,
                })

    def run(self):
        handler = Entity()
        handler.input = self.input
        handler.update = self.update
        self.app.run()
        if self.ipc:
            self.ipc.stop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            config = json.load(f)
        DNDMap3D(config).run()
