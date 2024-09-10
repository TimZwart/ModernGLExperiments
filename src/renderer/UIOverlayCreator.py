import pygame

from src.game import Game
from src.geometry.VerticesHolder import verticesHolder


class UIOverlayCreator:
    def __init__(self, width, height, game:Game):
        self.width = width
        self.height = height
        self.game = game
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

    def draw_ui_overlay(self):
        # Clear the overlay
        self.overlay.fill((0, 0, 0, 0))
        # Render text on the overlay
        font = pygame.font.Font(None, 24)
        debug_text = font.render(f"Vertices count: {len(verticesHolder.vertices) // 6}", True, (255, 0, 0))
        self.overlay.blit(debug_text, (10, 10))
        add_vertex_text = font.render("Press 'A' to add a new vertex at (0, 0, 0)", True, (255, 255, 0))
        self.overlay.blit(add_vertex_text, (10, self.height - 80))
        vertices_text = [font.render(f"Vertex {i}: {verticesHolder.vertices[i * 6:i * 6 + 3]}", True, (255, 255, 255))
                         for i in range(min(20, len(verticesHolder.vertices) // 6))]
        for i, text in enumerate(vertices_text):
            self.overlay.blit(text, (10, 40 + i * 30))
        # Display selected vertex coordinates
        if self.game.selected_vertex is not None:
            selected_coords = verticesHolder.vertices[self.game.selected_vertex * 6:self.game.selected_vertex * 6 + 3]
            if self.game.edit_mode:
                selected_text = font.render(f"Edit Vertex: {self.game.edit_text}", True, (255, 255, 0))
                pygame.draw.rect(self.overlay, (255, 255, 0), self.game.edit_rect, 2)
            else:
                selected_text = font.render(f"Selected Vertex: {selected_coords}", True, (255, 255, 0))
            self.overlay.blit(selected_text, (10, self.height - 50))

            # Create editable area
            edit_rect = pygame.Rect(10, self.height - 35, 290, 30)
            pygame.draw.rect(self.overlay, (255, 255, 0), edit_rect, 2)
            self.edit_rect = edit_rect

            if self.game.edit_mode:
                edit_surface = font.render(self.game.edit_text, True, (255, 255, 0))
                self.overlay.blit(edit_surface, (15, self.height - 30))