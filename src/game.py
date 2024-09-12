import sys
import pygame
from src.geometry.VerticesHolder import verticesHolder
import numpy as np
from src.camera.Camera import Camera

class Game:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.selected_vertex = None  # Add this line
        self.edit_mode = False
        self.edit_text = ""
        self.edit_rect = None
        self.camera = Camera()
        from src.renderer.UIOverlayCreator import UIOverlayCreator
        self.uiOverlayCreator = UIOverlayCreator(width, height, self)
        from src.renderer.Renderer import Renderer
        self.renderer = Renderer(width, height, self.uiOverlayCreator, self.camera)

    def find_nearest_vertex(self, x, y):
        vertices = verticesHolder.vertices.reshape(-1, 6)
        screen_coords = self.renderer.renderer3D.world_to_screen(vertices[:, :3])
        
        # Calculate distances in screen space
        distances = np.sqrt(np.sum((screen_coords - np.array([x, y])) ** 2, axis=1))
        
        # Find the index of the nearest vertex
        nearest_index = np.argmin(distances)
        
        # Set a maximum distance threshold (e.g., 100 pixels)
        max_distance = 100
        nearest_distance = distances[nearest_index]
        
        print(f"Nearest vertex: {nearest_index}, distance: {nearest_distance:.2f}")
        print(f"Click position: ({x}, {y})")
        print(f"Nearest vertex screen position: ({screen_coords[nearest_index][0]:.2f}, {screen_coords[nearest_index][1]:.2f})")
        
        if nearest_distance > max_distance:
            print(f"No vertex within {max_distance} pixels")
            return None
        
        return nearest_index

    def apply_edit(self):
        try:
            new_coords = eval(self.edit_text)
            if isinstance(new_coords, (list, tuple)) and len(new_coords) == 3:
                verticesHolder.vertices[self.selected_vertex*6:self.selected_vertex*6+3] = new_coords
                print(f"New vertex coordinates set to: {new_coords}")
                self.edit_mode = False
                print("edit mode deactivated")
                self.renderer.renderer3D.update_vertex_buffer()
            else:
                print(f"return pressed in edit mode, but input was not valid: {new_coords} has length {len(new_coords)} and type {type(new_coords)}")
        except:
            print("Invalid input. Please enter coordinates as [x, y, z]")
            raise

    def add_vertex(self, x:float, y:float, z:float):
        assert isinstance(x, float), "x must be float"
        assert isinstance(y, float), "y must be float"
        assert isinstance(z, float), "z must be float"
        new_vertex = [x, y, z, 1.0, 1.0, 1.0]  # Default color: white
        verticesHolder.vertices = np.append(verticesHolder.vertices, new_vertex).astype('f4')
        self.renderer.renderer3D.update_vertex_buffer()
        print(f"New vertex added: {new_vertex[:3]}")

    def save_vertices(self):
        filename = "assets/scout.vertices"
        vertices = verticesHolder.vertices.reshape(-1, 6)
        with open(filename, 'w') as file:
            for vertex in vertices:
                file.write(f"{' '.join(map(str, vertex))}\n")
        print(f"Vertices saved to {filename}")

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        print("left mouse button pressed")
                        x, y = event.pos
                        if not self.edit_rect:
                            print("no edit rect, weird")
                        if self.edit_rect and self.edit_rect.collidepoint(x, y):
                            self.edit_mode = True
                            print("edit mode activated")
                            self.edit_text = f"{verticesHolder.vertices[self.selected_vertex*6:self.selected_vertex*6+3]}"
                        else:
                            self.selected_vertex = self.find_nearest_vertex(x, y)
                            print(f"selected vertex: {self.selected_vertex}")
                            self.edit_mode = False
                            self.edit_text = ""
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:  # 'A' key to add a vertex
                        self.add_vertex(0.0, 0.0, 0.0)  # Add a vertex at (0, 0, 0)
                    elif event.key == pygame.K_o:  # 'S' key to save vertices
                        self.save_vertices()
                    elif event.key == pygame.K_w:
                        self.camera.forward()
                    elif event.key == pygame.K_s:
                        self.camera.backward()
                    elif event.key == pygame.K_a:
                        self.camera.left()
                    elif event.key == pygame.K_d:
                        self.camera.right()
                    elif event.key == pygame.K_q:
                        self.camera.upwards()
                    elif event.key == pygame.K_e:
                        self.camera.downwards()
                    elif self.edit_mode:
                        if event.key == pygame.K_RETURN:
                            self.apply_edit()
                        elif event.key == pygame.K_BACKSPACE:
                            self.edit_text = self.edit_text[:-1]

                        else:
                            self.edit_text += event.unicode
            
            self.renderer.render()
        pygame.quit()