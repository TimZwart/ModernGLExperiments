import pygame
import numpy as np

from src.game import Game
from src.geometry.VerticesHolder import verticesHolder
from src.configuration.loadconfig import keybindings, mouse_rotation_button


class UIOverlayCreator:
    def __init__(self, width, height, game:Game):
        self.width = width
        self.height = height
        self.game = game
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.font = pygame.font.Font(None, 24)
        self.scroll_offset = 0
        self.max_visible_vertices = 15

    def get_vertex_rect(self, index, y_position):
        vertex_text = f"Vertex {index}: {verticesHolder.vertices[index * 6:index * 6 + 3]}"
        text_width, text_height = self.font.size(vertex_text)
        return pygame.Rect(10, y_position, text_width + 10, 30)

    def draw_ui_overlay(self):
        # Clear the overlay
        self.overlay.fill((0, 0, 0, 0))
        if self.game.help_mode:
            self.draw_help_screen()
            return
        # Render text on the overlay
        debug_text = self.font.render(f"Vertices count: {len(verticesHolder.vertices) // 6}", True, (255, 0, 0))
        self.overlay.blit(debug_text, (10, 10))
        help_prompt = self.font.render(f"Press {keybindings['help'].upper()} for help", True, (0, 255, 255))
        self.overlay.blit(help_prompt, (10, self.height - 110))
        filename_text = self.font.render(f"Current file: {self.game.filename_text}", True, (255, 255, 0))
        self.overlay.blit(filename_text, (10, self.height - 80))
        
        # Create a clickable area for each vertex
        self.vertex_rects = []
        total_vertices = len(verticesHolder.vertices) // 6
        for i in range(self.scroll_offset, min(self.scroll_offset + self.max_visible_vertices, total_vertices)):
            vertex_text = f"Vertex {i}: {verticesHolder.vertices[i * 6:i * 6 + 3]}"
            color = (255, 255, 0) if i in self.game.yellow_highlights else (255, 0, 0) if i in self.game.selected_vertices else (255, 255, 255)
            text_surface = self.font.render(vertex_text, True, color)
            y_position = 40 + (i - self.scroll_offset) * 30
            self.overlay.blit(text_surface, (10, y_position))
            
            # Create a clickable area for each vertex
            vertex_rect = self.get_vertex_rect(i, y_position)
            self.vertex_rects.append((i, vertex_rect))
            pygame.draw.rect(self.overlay, (100, 100, 100), vertex_rect, 1)

        # Draw scroll indicators if necessary
        if self.scroll_offset > 0:
            pygame.draw.polygon(self.overlay, (255, 255, 255), [(10, 35), (20, 25), (30, 35)])
        if total_vertices > self.scroll_offset + self.max_visible_vertices:
            pygame.draw.polygon(self.overlay, (255, 255, 255), [(10, self.height - 85), (20, self.height - 75), (30, self.height - 85)])

        # Display filename editing area
        # Always anchor the filename UI to the bottom of the screen
        bottom_padding = 10
        rect_height = self.game.filename_rect.height
        rect_top = self.height - rect_height - bottom_padding
        self.game.filename_rect.topleft = (10, rect_top)

        if self.game.filename_edit_mode:
            pygame.draw.rect(self.overlay, (0, 255, 0), self.game.filename_rect, 2)
            filename_surface = self.font.render(self.game.filename_text, True, (0, 255, 0))
            self.overlay.blit(filename_surface, (15, rect_top + 5))
        else:
            # Show clickable filename area
            filename_display = self.font.render(f"Save to: {self.game.filename_text} (click to edit)", True, (150, 150, 150))
            pygame.draw.rect(self.overlay, (100, 100, 100), self.game.filename_rect, 1)
            self.overlay.blit(filename_display, (15, rect_top + 5))

        # Display selected vertex coordinates
        if self.game.selected_vertices:
            if len(self.game.selected_vertices) == 1:
                selected = list(self.game.selected_vertices)[0]
                selected_coords = verticesHolder.vertices[selected * 6:selected * 6 + 3]
                if self.game.edit_mode:
                    selected_text = self.font.render(f"Edit Vertex {selected}: {self.game.edit_text}", True, (255, 255, 0))
                    pygame.draw.rect(self.overlay, (255, 255, 0), self.game.edit_rect, 2)
                else:
                    selected_text = self.font.render(f"Selected Vertex {selected}: {selected_coords}", True, (255, 255, 0))
                self.overlay.blit(selected_text, (10, self.height - 50))

                # Update editable area
                self.game.edit_rect.top = self.height - 35
                pygame.draw.rect(self.overlay, (255, 255, 0), self.game.edit_rect, 2)

                if self.game.edit_mode:
                    edit_surface = self.font.render(self.game.edit_text, True, (255, 255, 0))
                    self.overlay.blit(edit_surface, (15, self.height - 30))
            else:
                selected_list = sorted(list(self.game.selected_vertices))
                selected_text = self.font.render(f"Selected Vertices: {selected_list}", True, (255, 255, 0))
                self.overlay.blit(selected_text, (10, self.height - 50))

        # Draw selected vertices markers
        if self.game.selected_vertices:
            selected_indices = list(self.game.selected_vertices)
            vertices = verticesHolder.vertices.reshape(-1, 6)
            selected_pos = vertices[selected_indices, :3]
            screen_coords = self.game.renderer.renderer3D.world_to_screen(selected_pos)
            square_size = 8
            for coord in screen_coords:
                sx, sy = coord
                if not np.isnan(sx) and not np.isnan(sy) and 0 <= sx < self.width and 0 <= sy < self.height:
                    rect = pygame.Rect(sx - square_size // 2, sy - square_size // 2, square_size, square_size)
                    pygame.draw.rect(self.overlay, (255, 0, 0, 255), rect)

    def draw_help_screen(self):
        font = pygame.font.Font(None, 24)
        rotate_key = keybindings.get('rotate', None)
        rotate_help = f"Mouse Rotation: Button {mouse_rotation_button}"
        if rotate_key:
            rotate_help = f"Mouse Rotation: Button {mouse_rotation_button} or {rotate_key.upper()} (hold)"
        help_texts = [
            "Keybindings:",
            f"Forward: {keybindings['forward'].upper()} or Arrow Up",
            f"Backward: {keybindings['backward'].upper()} or Arrow Down",
            f"Left: {keybindings['left'].upper()} or Arrow Left",
            f"Right: {keybindings['right'].upper()} or Arrow Right",
            f"Up: {keybindings['up'].upper()} or Page Up",
            f"Down: {keybindings['down'].upper()} or Page Down",
            f"Add Vertex: {keybindings['add_vertex'].upper()} or Insert",
            f"Save Vertices: {keybindings['save_vertices'].upper()} or F5",
            f"Change Filename: {keybindings['change_filename'].upper()} or F6",
            f"New File: {keybindings.get('new_file', 'n').upper()} or F9",
            f"Form Triangles: {keybindings['form_triangles'].upper()} or F7",
            f"Yaw Left: {keybindings['yaw_left'].upper()} or Numpad 4",
            f"Yaw Right: {keybindings['yaw_right'].upper()} or Numpad 6",
            f"Pitch Up: {keybindings['pitch_up'].upper()} or Numpad 8",
            f"Pitch Down: {keybindings['pitch_down'].upper()} or Numpad 2",
            f"Toggle Wireframe: {keybindings['toggle_wireframe'].upper()} or F8",
            f"Help: {keybindings['help'].upper()} or F1",
            rotate_help,
            "Press H or F1 again to close help",
        ]
        y = 20
        for text in help_texts:
            surf = font.render(text, True, (255, 255, 255))
            self.overlay.blit(surf, (20, y))
            y += 30