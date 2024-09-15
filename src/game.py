import sys
import pygame
from src.geometry.VerticesHolder import verticesHolder
import numpy as np
from src.camera.Camera import Camera
import random

class Game:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.selected_vertex = None  # Add this line
        self.edit_mode = False
        self.edit_text = ""
        self.edit_rect = pygame.Rect(10, self.height - 35, 290, 30)
        self.camera = Camera()
        from src.renderer.UIOverlayCreator import UIOverlayCreator
        self.uiOverlayCreator = UIOverlayCreator(width, height, self)
        from src.renderer.Renderer import Renderer
        self.renderer = Renderer(width, height, self.uiOverlayCreator, self.camera)
        self.vertex_count = len(verticesHolder.vertices) // 6
        if self.vertex_count > 0:
            if self.vertex_count % 3 == 0:
                self.current_color = self.random_color()
            else:
                last_vertex = verticesHolder.vertices[-6:]
                self.current_color = last_vertex[3:6].tolist()
        else:
            self.current_color = self.random_color()
        self.scroll_speed = 3  # Number of vertices to scroll per mouse wheel event

    def random_color(self):
        return [random.random() for _ in range(3)]

    def find_nearest_vertex(self, x, y):
        vertices = verticesHolder.vertices.reshape(-1, 6)
        screen_coords = self.renderer.renderer3D.world_to_screen(vertices[:, :3])
        
        print(f"Total vertices: {len(vertices)}")
        print(f"Screen coordinates shape: {screen_coords.shape}")
        
        # Calculate distances for all vertices
        distances = np.sqrt(np.sum((screen_coords - np.array([x, y])) ** 2, axis=1))
        
        # Find the index of the nearest vertex
        nearest_index = np.argmin(distances)
        nearest_distance = distances[nearest_index]
        
        # Set a maximum distance threshold (e.g., 500 pixels)
        max_distance = 500
        
        print(f"Click position: ({x}, {y})")
        print("Vertex positions:")
        for i, (sx, sy) in enumerate(screen_coords):
            print(f"Vertex {i}: ({sx:.2f}, {sy:.2f}), distance: {distances[i]:.2f}")
        
        print(f"Nearest vertex screen position: ({screen_coords[nearest_index][0]:.2f}, {screen_coords[nearest_index][1]:.2f})")
        print(f"Distance to nearest vertex: {nearest_distance:.2f}")
        
        if nearest_distance > max_distance:
            print(f"No vertex within {max_distance} pixels")
            return None
        
        print(f"Selected vertex index: {nearest_index}")
        
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
        
        if self.vertex_count % 3 == 0:
            self.current_color = self.random_color()
        
        new_vertex = [x, y, z] + self.current_color
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

    def handle_vertex_list_click(self, x, y):
        for actual_index, rect in self.uiOverlayCreator.vertex_rects:
            if rect.collidepoint(x, y):
                self.selected_vertex = actual_index
                self.edit_mode = True
                self.edit_text = f"{verticesHolder.vertices[self.selected_vertex*6:self.selected_vertex*6+3]}"
                return True
        return False

    def handle_scroll(self, y):
        total_vertices = len(verticesHolder.vertices) // 6
        if y > 0:  # Scroll up
            self.uiOverlayCreator.scroll_offset = max(0, self.uiOverlayCreator.scroll_offset - self.scroll_speed)
        else:  # Scroll down
            max_offset = max(0, total_vertices - self.uiOverlayCreator.max_visible_vertices)
            self.uiOverlayCreator.scroll_offset = min(max_offset, self.uiOverlayCreator.scroll_offset + self.scroll_speed)

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        x, y = event.pos
                        if self.edit_rect and self.edit_rect.collidepoint(x, y):
                            self.edit_mode = True
                            self.edit_text = f"{verticesHolder.vertices[self.selected_vertex*6:self.selected_vertex*6+3]}"
                        elif self.handle_vertex_list_click(x, y):
                            pass  # Vertex in the list was clicked, no need to do anything else
                        else:
                            nearest_vertex = self.find_nearest_vertex(x, y)
                            if nearest_vertex is not None:
                                self.selected_vertex = nearest_vertex
                                self.edit_mode = False
                                self.edit_text = ""
                            else:
                                print("No vertex nearby")
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
                elif event.type == pygame.MOUSEWHEEL:
                    self.handle_scroll(event.y)
            
            self.renderer.render()
        pygame.quit()