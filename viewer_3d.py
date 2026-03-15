"""3D Ursina viewer for D&D maps — launched as subprocess from main.py.

Camera controls (TaleSpire / Tabletop Simulator conventions):
  Right Drag    — Orbit camera around clicked point on map
  Middle Drag   — Pan camera
  Scroll        — Zoom toward/away from cursor
  WASD / Arrows — Pan camera
  Q / E         — Rotate camera 45 degrees
  Space         — Reset camera to top-down
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
# 3D Standee Token — thick cardboard-style miniature
# ---------------------------------------------------------------------------

class DNDToken3D(Entity):
    """A 3D standee token: thick slab with artwork, on a cylindrical base."""

    def __init__(self, texture_path, name, grid_x, grid_z, scale_val=1.0):
        p_path = Path(texture_path).absolute().as_posix()
        super().__init__(position=(grid_x, 0, grid_z))
        self.token_name = name
        self.creature_id = ""

        tex = None
        try:
            tex = Texture(p_path)
        except Exception:
            print(f"Warning: Could not load texture {p_path}")

        s = scale_val

        # --- Circular base ---
        self.token_base = Entity(
            parent=self,
            model='cylinder',
            color=color.rgb(40, 40, 45),
            scale=(s * 0.9, 0.08, s * 0.9),
            y=0.04,
            collider='box',
        )
        # Base rim highlight
        Entity(
            parent=self,
            model='cylinder',
            color=color.rgb(80, 70, 55),
            scale=(s * 0.92, 0.02, s * 0.92),
            y=0.085,
        )

        # --- Standee slab (thick "cardboard") ---
        slab_height = s * 1.0
        slab_thickness = s * 0.06
        slab_y = slab_height / 2 + 0.1

        # The slab body (thin cube gives it depth)
        self.slab = Entity(
            parent=self,
            model='cube',
            color=color.rgb(30, 30, 35),
            scale=(s * 0.85, slab_height, slab_thickness),
            y=slab_y,
            collider='box',
        )

        # Front artwork
        self.front_face = Entity(
            parent=self,
            model='quad',
            texture=tex,
            scale=(s * 0.85, slab_height),
            y=slab_y,
            z=-(slab_thickness / 2 + 0.001),
            collider='box',
        )

        # Back artwork
        self.back_face = Entity(
            parent=self,
            model='quad',
            texture=tex,
            scale=(s * 0.85, slab_height),
            y=slab_y,
            z=(slab_thickness / 2 + 0.001),
            rotation_y=180,
            collider='box',
        )

        # Tag children for click detection
        for child in (self.front_face, self.back_face, self.slab, self.token_base):
            child.parent_token = self

    def highlight(self, on=True):
        self.token_base.color = color.rgb(220, 200, 50) if on else color.rgb(40, 40, 45)

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

        # Lighting — ambient only (fast on iGPU, no shadows)
        AmbientLight(color=color.rgba(200, 195, 210, 255))

        # Table surface (dark wood under the map)
        table_margin = 3
        Entity(
            model='cube',
            color=color.rgb(45, 30, 20),
            scale=(self.w + table_margin * 2, 0.3, self.h + table_margin * 2),
            position=(self.w / 2, -0.2, self.h / 2),
        )

        # Map on the table (slightly raised)
        self.floor = Entity(
            model='quad',
            texture=map_tex,
            rotation=(90, 0, 0),
            scale=(self.w, self.h),
            collider='box',
            position=(self.w / 2, 0.01, self.h / 2),
        )

        # Map border / frame
        border_w = 0.08
        border_color = color.rgb(70, 50, 30)
        for bx, bz, bsx, bsz in [
            (self.w / 2, -border_w / 2, self.w + border_w * 2, border_w),          # front
            (self.w / 2, self.h + border_w / 2, self.w + border_w * 2, border_w),  # back
            (-border_w / 2, self.h / 2, border_w, self.h + border_w * 2),          # left
            (self.w + border_w / 2, self.h / 2, border_w, self.h + border_w * 2),  # right
        ]:
            Entity(
                model='cube',
                color=border_color,
                scale=(bsx, 0.15, bsz),
                position=(bx, 0.05, bz),
            )

        # Grid overlay
        self.grid = Entity(
            model=Grid(self.width_sq, self.height_sq),
            rotation=(90, 0, 0),
            scale=(self.w, self.h),
            position=self.floor.position,
            color=color.rgba(255, 255, 255, 25),
            y=0.02,
        )

        # Walls from scan data
        self.walls = []
        scan_data = config.get('scan_data', {})
        if 'walls' in scan_data:
            for wd in scan_data['walls']:
                self._create_wall(wd)

        # ---- Camera state ----
        self._cam_target = Vec3(self.w / 2, 0, self.h / 2)
        self._cam_dist = max(self.w, self.h) * 1.0
        self._cam_yaw = 0.0
        self._cam_pitch = 55.0
        self._rotating = False
        self._panning = False
        self._apply_camera()

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
            text='[RMB] Orbit  [MMB] Pan  [Scroll] Zoom  [WASD] Move  [Q/E] Rotate  [Space] Reset  [G] Grid',
            position=(-0.85, 0.48),
            scale=0.65,
            color=color.rgba(180, 180, 180, 100),
        )

    # ---- Camera ----

    def _apply_camera(self):
        self._cam_pitch = clamp(self._cam_pitch, 5, 89)
        self._cam_dist = clamp(self._cam_dist, 2, 150)

        pr = math.radians(self._cam_pitch)
        yr = math.radians(self._cam_yaw)

        cam_y = self._cam_dist * math.sin(pr)
        horiz = self._cam_dist * math.cos(pr)
        cam_x = horiz * math.sin(yr)
        cam_z = -horiz * math.cos(yr)

        camera.position = self._cam_target + Vec3(cam_x, cam_y, cam_z)
        camera.look_at(self._cam_target)

    def _reset_camera(self):
        self._cam_target = Vec3(self.w / 2, 0, self.h / 2)
        self._cam_dist = max(self.w, self.h) * 1.0
        self._cam_yaw = 0
        self._cam_pitch = 55
        self._apply_camera()

    # ---- Walls ----

    def _create_wall(self, wall_data):
        sx, sy = wall_data['start']
        ex, ey = wall_data['end']
        h = wall_data.get('height', 3)
        ms = self.map_scale
        dist = math.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)
        if dist < 0.1:
            return
        Entity(
            model='cube',
            color=color.rgb(120, 110, 100),
            scale=(dist * ms, h, 0.2),
            position=((sx + ex) / 2 * ms, h / 2, (sy + ey) / 2 * ms),
            rotation_y=-math.degrees(math.atan2(ey - sy, ex - sx)),
            collider='box',
        )

    # ---- IPC ----

    def _on_ipc(self, msg):
        if msg.get("type") == "token_move":
            cid = msg.get("creature_id")
            for t in self.tokens:
                if t.creature_id == cid:
                    t.set_grid_pos(msg.get("x", 0), msg.get("y", 0), self.map_scale)

    # ---- Frame update ----

    def update(self):
        dt = time.dt

        # Token dragging
        if self.dragging and self.selected_token and mouse.world_point:
            self.selected_token.x = mouse.world_point.x
            self.selected_token.z = mouse.world_point.z
            self.selected_token.y = 0.3

        # Right-drag: orbit
        if self._rotating:
            if mouse.velocity[0] != 0 or mouse.velocity[1] != 0:
                self._cam_yaw -= mouse.velocity[0] * 150
                self._cam_pitch += mouse.velocity[1] * 150
                self._apply_camera()

        # Middle-drag: pan
        if self._panning:
            if mouse.velocity[0] != 0 or mouse.velocity[1] != 0:
                yr = math.radians(self._cam_yaw)
                right = Vec3(math.cos(yr), 0, math.sin(yr))
                fwd = Vec3(-math.sin(yr), 0, math.cos(yr))
                speed = self._cam_dist * 0.5
                self._cam_target += right * (-mouse.velocity[0] * speed)
                self._cam_target += fwd * (-mouse.velocity[1] * speed)
                self._apply_camera()

        # WASD / Arrow key panning
        pan_speed = self._cam_dist * 0.5 * dt
        yr = math.radians(self._cam_yaw)
        right = Vec3(math.cos(yr), 0, math.sin(yr))
        fwd = Vec3(-math.sin(yr), 0, math.cos(yr))

        move = Vec3(0, 0, 0)
        if held_keys['w'] or held_keys['up arrow']:
            move += fwd * pan_speed
        if held_keys['s'] or held_keys['down arrow']:
            move -= fwd * pan_speed
        if held_keys['a'] or held_keys['left arrow']:
            move -= right * pan_speed
        if held_keys['d'] or held_keys['right arrow']:
            move += right * pan_speed

        if move.length() > 0:
            self._cam_target += move
            self._apply_camera()

    # ---- Input ----

    def input(self, key):
        # Grid toggle
        if key == 'g':
            self.grid.enabled = not self.grid.enabled
        # Quit
        elif key == 'escape':
            if self.ipc:
                self.ipc.stop()
            application.quit()
        # Reset camera
        elif key == 'space':
            self._reset_camera()
        # Q/E rotation (45 degree steps)
        elif key == 'q':
            self._cam_yaw -= 45
            self._apply_camera()
        elif key == 'e':
            self._cam_yaw += 45
            self._apply_camera()

        # ---- Scroll: zoom toward cursor ----
        if key == 'scroll up':
            self._cam_dist *= 0.9
            if mouse.world_point:
                target = Vec3(mouse.world_point.x, 0, mouse.world_point.z)
                self._cam_target = lerp(self._cam_target, target, 0.12)
            self._apply_camera()
        elif key == 'scroll down':
            self._cam_dist *= 1.1
            self._apply_camera()

        # ---- Right mouse: orbit ----
        if key == 'right mouse down':
            if mouse.world_point:
                self._cam_target = Vec3(mouse.world_point.x, 0, mouse.world_point.z)
                self._apply_camera()
            self._rotating = True
        elif key == 'right mouse up':
            self._rotating = False

        # ---- Middle mouse: pan ----
        if key == 'middle mouse down':
            self._panning = True
        elif key == 'middle mouse up':
            self._panning = False

        # ---- Left click: select/drag tokens ----
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
            # Clicked empty space
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
