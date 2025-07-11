import pygame
from src.geometry.VerticesHolder import verticesHolder

import numpy as np

class EventHandler:
    def __init__(self, game):
        self.game = game

    def handle_events(self):
        continue_running = True
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                continue_running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    x, y = event.pos
                    if self.game.filename_rect and self.game.filename_rect.collidepoint(x, y):
                        self.game.filename_edit_mode = True
                    elif self.game.edit_rect and self.game.edit_rect.collidepoint(x, y) and self.game.selected_vertex is not None:
                        self.game.edit_mode = True
                        self.game.edit_text = f"{list(verticesHolder.vertices[self.game.selected_vertex*6:self.game.selected_vertex*6+3])}"
                    elif self.handle_vertex_list_click(x, y):
                        pass # Vertex in the list was clicked, no need to do anything else
                    else:
                        nearest_vertex = self.find_nearest_vertex(x, y)
                        if nearest_vertex is not None:
                            self.game.selected_vertex = nearest_vertex
                            self.game.edit_mode = False
                            self.game.edit_text = ""
                        else:
                            print("No vertex nearby")
            elif event.type == pygame.KEYDOWN:
                if self.game.filename_edit_mode:
                    if event.key == pygame.K_RETURN:
                        self.apply_filename_edit()
                    elif event.key == pygame.K_BACKSPACE:
                        self.game.filename_text = self.game.filename_text[:-1]
                    else:
                        self.game.filename_text += event.unicode
                elif self.game.edit_mode:
                    if event.key == pygame.K_RETURN:
                        self.apply_edit()
                    elif event.key == pygame.K_BACKSPACE:
                        self.game.edit_text = self.game.edit_text[:-1]
                    else:
                        self.game.edit_text += event.unicode
                elif event.key == pygame.K_p:  # 'P' key to add a vertex
                    self.add_vertex(0.0, 0.0, 0.0)  # Add a vertex at (0, 0, 0)
                elif event.key == pygame.K_o:  # 'O' key to save vertices
                    self.save_vertices()
                elif event.key == pygame.K_c:  # 'C' key to change filename
                    self.game.filename_edit_mode = True
                elif event.key == pygame.K_w:
                    self.game.camera.forward()
                elif event.key == pygame.K_s:
                    self.game.camera.backward()
                elif event.key == pygame.K_a:
                    self.game.camera.left()
                elif event.key == pygame.K_d:
                    self.game.camera.right()
                elif event.key == pygame.K_q:
                    self.game.camera.upwards()
                elif event.key == pygame.K_e:
                    self.game.camera.downwards()
            elif event.type == pygame.MOUSEWHEEL:
                self.handle_scroll(event.y)
        
        return continue_running 

    def find_nearest_vertex(self, x, y):
        vertices = verticesHolder.vertices.reshape(-1, 6)
        screen_coords = self.game.renderer.renderer3D.world_to_screen(vertices[:, :3])
        
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
            new_coords = eval(self.game.edit_text)
            if isinstance(new_coords, (list, tuple)) and len(new_coords) == 3:
                verticesHolder.vertices[self.game.selected_vertex*6:self.game.selected_vertex*6+3] = new_coords
                print(f"New vertex coordinates set to: {new_coords}")
                self.game.edit_mode = False
                print("edit mode deactivated")
                self.game.renderer.renderer3D.update_vertex_buffer()
            else:
                print(f"return pressed in edit mode, but input was not valid: {new_coords} has length {len(new_coords)} and type {type(new_coords)}")
        except:
            print("Invalid input. Please enter coordinates as [x, y, z]")
            raise

    def add_vertex(self, x:float, y:float, z:float):
        assert isinstance(x, float), "x must be float"
        assert isinstance(y, float), "y must be float"
        assert isinstance(z, float), "z must be float"
        
        current_count = len(verticesHolder.vertices) // 6
        if current_count % 3 == 0:
            self.game.current_color = self.game.random_color()
        
        new_vertex = [x, y, z] + self.game.current_color
        verticesHolder.vertices = np.append(verticesHolder.vertices, new_vertex).astype('f4')
        self.game.renderer.renderer3D.update_vertex_buffer()
        print(f"New vertex added: {new_vertex[:3]}")

    def save_vertices(self):
        filename = self.game.filename_text
        vertices = verticesHolder.vertices.reshape(-1, 6)
        with open(filename, 'w') as file:
            for vertex in vertices:
                file.write(f"{' '.join(map(str, vertex))}\n")
        print(f"Vertices saved to {filename}")

    def apply_filename_edit(self):
        # Simply exit filename edit mode - the filename_text is already updated
        self.game.filename_edit_mode = False
        print(f"Save filename set to: {self.game.filename_text}")

    def handle_vertex_list_click(self, x, y):
        for actual_index, rect in self.game.uiOverlayCreator.vertex_rects:
            if rect.collidepoint(x, y):
                self.game.selected_vertex = actual_index
                self.game.edit_mode = True
                self.game.edit_text = f"{list(verticesHolder.vertices[self.game.selected_vertex*6:self.game.selected_vertex*6+3])}"
                return True
        return False

    def handle_scroll(self, y):
        total_vertices = len(verticesHolder.vertices) // 6
        if y > 0:  # Scroll up
            self.game.uiOverlayCreator.scroll_offset = max(0, self.game.uiOverlayCreator.scroll_offset - self.game.scroll_speed)
        else:  # Scroll down
            max_offset = max(0, total_vertices - self.game.uiOverlayCreator.max_visible_vertices)
            self.game.uiOverlayCreator.scroll_offset = min(max_offset, self.game.uiOverlayCreator.scroll_offset + self.game.scroll_speed) 