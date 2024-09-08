import sys
import pygame
from src.renderer.Renderer3D import Renderer3D
from src.geometry.loader import load_vertices
from src.geometry.VerticesHolder import verticesHolder
import numpy as np

class Game:
    def __init__(self, renderer: Renderer3D):
        self.renderer = renderer
        self.width, self.height = renderer.width, renderer.height
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.selected_vertex = None  # Add this line
        self.edit_mode = False
        self.edit_text = ""
        self.edit_rect = None

    def find_nearest_vertex(self, x, y):
        vertices = verticesHolder.vertices.reshape(-1, 6)
        screen_coords = self.renderer.world_to_screen(vertices[:, :3])
        distances = np.sqrt(np.sum((screen_coords - np.array([x, y])) ** 2, axis=1))
        nearest_index = np.argmin(distances)
        return nearest_index

    def render(self):
        # Clear the overlay
        self.overlay.fill((0, 0, 0, 0))
        
        # Render text on the overlay
        font = pygame.font.Font(None, 24)
        debug_text = font.render(f"Vertices count: {len(verticesHolder.vertices) // 6}", True, (255, 0, 0))
        self.overlay.blit(debug_text, (10, 10))
        
        vertices_text = [font.render(f"Vertex {i}: {verticesHolder.vertices[i*6:i*6+3]}", True, (255, 255, 255)) for i in range(min(20, len(verticesHolder.vertices) // 6))]
        for i, text in enumerate(vertices_text):
            self.overlay.blit(text, (10, 40 + i * 30))
        
        # Display selected vertex coordinates
        if self.selected_vertex is not None:
            selected_coords = verticesHolder.vertices[self.selected_vertex*6:self.selected_vertex*6+3]
            if self.edit_mode:
                selected_text = font.render(f"Edit Vertex: {self.edit_text}", True, (255, 255, 0))
                pygame.draw.rect(self.overlay, (255, 255, 0), self.edit_rect, 2)
            else:
                selected_text = font.render(f"Selected Vertex: {selected_coords}", True, (255, 255, 0))
            self.overlay.blit(selected_text, (10, self.height - 40))
            
            # Create editable area
            edit_rect = pygame.Rect(10, self.height - 35, 290, 30)
            pygame.draw.rect(self.overlay, (255, 255, 0), edit_rect, 2)
            self.edit_rect = edit_rect
            
            if self.edit_mode:
                edit_surface = font.render(self.edit_text, True, (255, 255, 0))
                self.overlay.blit(edit_surface, (15, self.height - 30))
        
        # Update the text texture
        self.renderer.update_text_texture(self.overlay)
        
        # Render OpenGL content and text texture
        self.renderer.render()
        
        # Update the display
        pygame.display.flip()

    def apply_edit(self):
        try:
            new_coords = eval(self.edit_text)
            if isinstance(new_coords, (list, tuple)) and len(new_coords) == 3:
                verticesHolder.vertices[self.selected_vertex*6:self.selected_vertex*6+3] = new_coords
                self.edit_mode = False
                self.renderer.update_vertex_buffer()
        except:
            print("Invalid input. Please enter coordinates as [x, y, z]")

    def run(self):
        running = True
        frame_count = 0
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
                        else:
                            self.selected_vertex = self.find_nearest_vertex(x, y)
                            self.edit_mode = False
                            self.edit_text = ""
                elif event.type == pygame.KEYDOWN:
                    if self.edit_mode:
                        if event.key == pygame.K_RETURN:
                            self.apply_edit()
                        elif event.key == pygame.K_BACKSPACE:
                            self.edit_text = self.edit_text[:-1]
                        else:
                            self.edit_text += event.unicode
            
            self.render()
            frame_count += 1
            if frame_count % 60 == 0:  # Print every 60 frames
                print(f"Rendered {frame_count} frames")
        pygame.quit()

if __name__ == '__main__':
    width, height = 800, 600
    pygame.init()
    pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF)
    vertex_file = None
    if len(sys.argv) > 1:
        vertex_file = sys.argv[1]
    verticesHolder.vertices = load_vertices(vertex_file)
    renderer = Renderer3D(width, height)
    game = Game(renderer)
    game.run()

