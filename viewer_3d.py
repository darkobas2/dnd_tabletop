from ursina import *
import json
import sys
import os
from pathlib import Path

class DNDToken3D(Entity):
    def __init__(self, texture_path, name, grid_x, grid_y, scale=1.0):
        # Use load_texture for better absolute path handling
        tex = load_texture(texture_path)
        super().__init__(
            model='quad',
            texture=tex,
            scale=(scale, scale),
            position=(grid_x, 0.5, grid_y),
            billboard=True,
            collider='box'
        )
        self.name = name

class DNDMap3D:
    def __init__(self, config):
        # Initialize Ursina with explicit settings
        self.app = Ursina(
            title=f"D&D 3D: {config['map_name']}",
            development_mode=False,
            editor_ui_enabled=False
        )
        
        width_sq = config['width_sq']
        height_sq = config['height_sq']
        map_scale = config['map_scale']
        
        map_tex = load_texture(config['map_path'])
        
        Sky()
        DirectionalLight(y=2, z=-3, rotation=(45, 45, 45))
        
        # Floor Plane
        self.floor = Entity(
            model='quad',
            texture=map_tex,
            rotation=(90, 0, 0),
            scale=(width_sq * map_scale, height_sq * map_scale),
            collider='box',
            x=(width_sq * map_scale) / 2,
            z=(height_sq * map_scale) / 2
        )
        
        # Grid overlay - use Grid model with correct subdivisions
        self.grid = Entity(
            model=Grid(width_sq, height_sq),
            rotation=(90, 0, 0),
            scale=(width_sq * map_scale, height_sq * map_scale),
            position=self.floor.position,
            color=color.black66,
            y=0.01
        )
        
        # Camera
        self.camera = EditorCamera()
        self.camera.position = (width_sq/2, 20, -10)
        self.camera.rotation_x = 45

        self.tokens = []
        start_x = 0.5
        for token_name, data in config['tokens'].items():
            count, token_scale, path = data
            for i in range(count):
                t = DNDToken3D(
                    texture_path=path,
                    name=token_name,
                    grid_x=start_x,
                    grid_y=0.5,
                    scale=token_scale * map_scale
                )
                self.tokens.append(t)
                start_x += 1.0

        self.selected_token = None

    def input(self, key):
        if key == 'g':
            self.grid.enabled = not self.grid.enabled
        elif key == 'escape':
            self.app.quit()
            
        if key == 'left mouse down':
            if mouse.hovered_entity and isinstance(mouse.hovered_entity, DNDToken3D):
                self.selected_token = mouse.hovered_entity
            else:
                self.selected_token = None

        if key == 'right mouse down' and self.selected_token:
            if mouse.world_point:
                # Snap logic for Ursina coordinates
                self.selected_token.x = round(mouse.world_point.x - 0.5) + 0.5
                self.selected_token.z = round(mouse.world_point.z - 0.5) + 0.5

    def run(self):
        self.app.input = self.input
        self.app.run()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            config = json.load(f)
        m = DNDMap3D(config)
        m.run()
