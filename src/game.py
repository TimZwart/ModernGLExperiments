import sys
import pygame
from src.geometry.VerticesHolder import verticesHolder
import numpy as np


class Game:
    def __init__(self, width: int, height: int):
        self.renderer = None #initialized later
        self.width, self.height = width, height
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.selected_vertex = None  # Add this line
        self.edit_mode = False
        self.edit_text = ""
        self.edit_rect = None

    def find_nearest_vertex(self, x, y):
        vertices = verticesHolder.vertices.reshape(-1, 6)
        screen_coords = self.renderer.renderer3D.world_to_screen(vertices[:, :3])
        distances = np.sqrt(np.sum((screen_coords - np.array([x, y])) ** 2, axis=1))
        nearest_index = np.argmin(distances)
        return nearest_index

    def apply_edit(self):
        try:
            new_coords = eval(self.edit_text)
            if isinstance(new_coords, (list, tuple)) and len(new_coords) == 3:
                verticesHolder.vertices[self.selected_vertex*6:self.selected_vertex*6+3] = new_coords
                print(f"New vertex coordinates set to: {new_coords}")
                self.edit_mode = False
                self.renderer.renderer3D.update_vertex_buffer()
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
                        x, y = event.pos
                        if not self.edit_rect:
                            print("no edit rect, weird")
                        if self.edit_rect and self.edit_rect.collidepoint(x, y):
                            self.edit_mode = True
                            self.edit_text = f"{verticesHolder.vertices[self.selected_vertex*6:self.selected_vertex*6+3]}"
                        else:
                            self.selected_vertex = self.find_nearest_vertex(x, y)
                            self.edit_mode = False
                            self.edit_text = ""
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:  # 'A' key to add a vertex
                        self.add_vertex(0.0, 0.0, 0.0)  # Add a vertex at (0, 0, 0)
                    elif event.key == pygame.K_s:  # 'S' key to save vertices
                        self.save_vertices()
                    elif self.edit_mode:
                        if event.key == pygame.K_RETURN:
                            self.apply_edit()
                        elif event.key == pygame.K_BACKSPACE:
                            self.edit_text = self.edit_text[:-1]
                        else:
                            self.edit_text += event.unicode
            
            self.renderer.render()
        pygame.quit()