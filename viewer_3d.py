from ursina import *
import json
import sys
import os
import math
from pathlib import Path

class DNDToken3D(Entity):
    def __init__(self, texture_path, name, grid_x, grid_y, scale=1.0):
        # Convert path to posix for Ursina compatibility
        p_path = Path(texture_path).absolute().as_posix()
        super().__init__(position=(grid_x, 0, grid_y))
        self.name = name
        
        # Robust texture loading
        try:
            tex = Texture(p_path)
        except:
            tex = None
            print(f"Error: Could not load texture {p_path}")

        self.token_base = Entity(
            parent=self,
            model='cube',
            color=color.black,
            scale=(0.85 * scale, 0.1, 0.85 * scale),
            collider='box'
        )
        
        self.front_face = Entity(
            parent=self,
            model='quad',
            texture=tex,
            scale=(scale, scale),
            y=scale/2 + 0.1,
            z=-0.02,
            collider='box'
        )
        self.back_face = Entity(
            parent=self,
            model='quad',
            texture=tex,
            scale=(scale, scale),
            y=scale/2 + 0.1,
            z=0.02,
            rotation_y=180,
            collider='box'
        )
        
        self.front_face.parent_token = self
        self.back_face.parent_token = self
        self.token_base.parent_token = self

class DNDMap3D:
    def __init__(self, config):
        self.app = Ursina(
            title=f"D&D 3D World: {config['map_name']}",
            development_mode=False,
            editor_ui_enabled=False
        )
        
        self.width_sq = config['width_sq']
        self.height_sq = config['height_sq']
        self.map_scale = config['map_scale']
        
        map_path = Path(config['map_path']).absolute().as_posix()
        try:
            map_tex = Texture(map_path)
        except:
            map_tex = None

        Sky(color=color.black)
        self.sun = DirectionalLight(y=30, z=-30, rotation=(45, 45, 0))
        self.sun.shadows = True
        
        # Floor Plane
        self.floor = Entity(
            model='quad',
            texture=map_tex,
            rotation=(90, 0, 0),
            scale=(self.width_sq * self.map_scale, self.height_sq * self.map_scale),
            collider='box',
            x=(self.width_sq * self.map_scale) / 2,
            z=(self.height_sq * self.map_scale) / 2,
            receive_shadows=True
        )
        
        # Interactive Grid
        self.grid = Entity(
            model=Grid(self.width_sq, self.height_sq),
            rotation=(90, 0, 0),
            scale=(self.width_sq * self.map_scale, self.height_sq * self.map_scale),
            position=self.floor.position,
            color=color.rgba(255, 255, 255, 40),
            y=0.01
        )
        
        # Walls
        self.walls = []
        if 'scan_data' in config and 'walls' in config['scan_data']:
            for wall_data in config['scan_data']['walls']:
                self.create_3d_wall(wall_data)

        # Better Intuitive Camera
        # EditorCamera is already very intuitive:
        # - Right Click + Mouse Move: Rotate
        # - Mouse Wheel: Zoom
        # - Middle Click + Mouse Move: Pan
        self.cam = EditorCamera()
        self.cam.position = (self.width_sq*self.map_scale/2, 20, -10)
        self.cam.rotation_x = 45

        # Tokens
        self.tokens = []
        start_x = 0.5
        for token_name, data in config['tokens'].items():
            count, token_scale, path = data
            for i in range(count):
                t = DNDToken3D(
                    texture_path=path,
                    name=token_name,
                    grid_x=start_x * self.map_scale,
                    grid_y=0.5 * self.map_scale,
                    scale=token_scale * self.map_scale
                )
                self.tokens.append(t)
                start_x += 1.2

        self.selected_token = None
        self.dragging = False

    def create_3d_wall(self, wall_data):
        sx, sy = wall_data['start']
        ex, ey = wall_data['end']
        h = wall_data.get('height', 3)
        
        dist = math.sqrt((ex - sx)**2 + (ey - sy)**2)
        center_x = (sx + ex) / 2
        center_z = (sy + ey) / 2
        
        # Solid brick walls
        wall = Entity(
            model='cube',
            texture='brick',
            color=color.light_gray,
            scale=(dist * self.map_scale, h, 0.15),
            position=(center_x * self.map_scale, h/2, center_z * self.map_scale),
            rotation_y=-math.degrees(math.atan2(ey - sy, ex - sx)),
            collider='box',
            cast_shadows=True
        )
        self.walls.append(wall)

    def update(self):
        if self.dragging and self.selected_token and mouse.world_point:
            self.selected_token.x = mouse.world_point.x
            self.selected_token.z = mouse.world_point.z
            self.selected_token.y = 0.5

    def input(self, key):
        if key == 'g':
            self.grid.enabled = not self.grid.enabled
        elif key == 'escape':
            self.app.quit()
            
        if key == 'left mouse down':
            if mouse.hovered_entity:
                hit = mouse.hovered_entity
                parent = getattr(hit, 'parent_token', None)
                if parent:
                    self.selected_token = parent
                    self.dragging = True
                    self.selected_token.token_base.color = color.yellow
                else:
                    self.selected_token = None
            else:
                self.selected_token = None

        if key == 'left mouse up' and self.selected_token:
            self.dragging = False
            self.selected_token.token_base.color = color.black
            # Snap to grid logic
            ms = self.map_scale
            self.selected_token.x = round(self.selected_token.x / ms - 0.5) * ms + ms/2
            self.selected_token.z = round(self.selected_token.z / ms - 0.5) * ms + ms/2
            self.selected_token.y = 0

    def run(self):
        self.app.update = self.update
        self.app.run()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            config = json.load(f)
        m = DNDMap3D(config)
        m.run()
