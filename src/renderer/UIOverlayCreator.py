import pygame

from src.game import Game
from src.geometry.VerticesHolder import verticesHolder


class UIOverlayCreator:
    def __init__(self, width, height, game:Game):
        self.width = width
        self.height = height
        self.game = game
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

    def get_vertex_rect(self, index, y_position):
        return pygame.Rect(10, y_position, self.width - 20, 30)

    def draw_ui_overlay(self):
        # Clear the overlay
        self.overlay.fill((0, 0, 0, 0))
        # Render text on the overlay
        font = pygame.font.Font(None, 24)
        debug_text = font.render(f"Vertices count: {len(verticesHolder.vertices) // 6}", True, (255, 0, 0))
        self.overlay.blit(debug_text, (10, 10))
        add_vertex_text = font.render("Press 'P' to add a new vertex at (0, 0, 0)  Press 'O' to save vertices to scout.vertices", True, (255, 255, 0))
        self.overlay.blit(add_vertex_text, (10, self.height - 80))
        
        # Create a clickable area for each vertex
        self.vertex_rects = []
        for i in range(min(20, len(verticesHolder.vertices) // 6)):
            vertex_text = f"Vertex {i}: {verticesHolder.vertices[i * 6:i * 6 + 3]}"
            text_surface = font.render(vertex_text, True, (255, 255, 255))
            y_position = 40 + i * 30
            self.overlay.blit(text_surface, (10, y_position))
            
            # Create a clickable area for each vertex
            vertex_rect = self.get_vertex_rect(i, y_position)
            self.vertex_rects.append(vertex_rect)
            pygame.draw.rect(self.overlay, (100, 100, 100), vertex_rect, 1)

        # Display selected vertex coordinates
        if self.game.selected_vertex is not None:
            selected_coords = verticesHolder.vertices[self.game.selected_vertex * 6:self.game.selected_vertex * 6 + 3]
            if self.game.edit_mode:
                selected_text = font.render(f"Edit Vertex: {self.game.edit_text}", True, (255, 255, 0))
                pygame.draw.rect(self.overlay, (255, 255, 0), self.game.edit_rect, 2)
            else:
                selected_text = font.render(f"Selected Vertex: {selected_coords}", True, (255, 255, 0))
            self.overlay.blit(selected_text, (10, self.height - 50))

            # Update editable area
            self.game.edit_rect.top = self.height - 35
            pygame.draw.rect(self.overlay, (255, 255, 0), self.game.edit_rect, 2)

            if self.game.edit_mode:
                edit_surface = font.render(self.game.edit_text, True, (255, 255, 0))
                self.overlay.blit(edit_surface, (15, self.height - 30))