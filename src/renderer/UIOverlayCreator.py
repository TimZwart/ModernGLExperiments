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
        # Status message (transient)
        msg_text, msg_frames = self.game.status_message
        if msg_frames > 0 and msg_text:
            status_surface = self.font.render(msg_text, True, (0, 255, 0))
            self.overlay.blit(status_surface, (10, 25))
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

        # Display filename editing area (Save)
        bottom_padding = 10
        rect_height = self.game.filename_rect.height
        save_rect_top = self.height - rect_height - bottom_padding
        self.game.filename_rect.topleft = (10, save_rect_top)

        if self.game.filename_edit_mode and getattr(self.game, 'filename_edit_purpose', 'save') == 'save':
            pygame.draw.rect(self.overlay, (0, 255, 0), self.game.filename_rect, 2)
            filename_surface = self.font.render(self.game.filename_text, True, (0, 255, 0))
            self.overlay.blit(filename_surface, (15, save_rect_top + 5))
        else:
            filename_display = self.font.render(f"Save to: {self.game.filename_text} (click to edit)", True, (150, 150, 150))
            pygame.draw.rect(self.overlay, (100, 100, 100), self.game.filename_rect, 1)
            self.overlay.blit(filename_display, (15, save_rect_top + 5))

        # Open file field above Save
        open_rect_top = save_rect_top - 35
        self.game.open_rect.topleft = (10, open_rect_top)
        if self.game.filename_edit_mode and getattr(self.game, 'filename_edit_purpose', 'save') == 'open':
            pygame.draw.rect(self.overlay, (0, 200, 255), self.game.open_rect, 2)
            open_surface = self.font.render(self.game.filename_text, True, (0, 200, 255))
            self.overlay.blit(open_surface, (15, open_rect_top + 5))
        else:
            open_hint = self.font.render("Open file: press B or F3 (click to edit path)", True, (120, 120, 120))
            pygame.draw.rect(self.overlay, (80, 80, 80), self.game.open_rect, 1)
            self.overlay.blit(open_hint, (15, open_rect_top + 5))

        # Add-vertex input field above Open
        add_rect_top = open_rect_top - 35
        self.game.add_vertex_rect.topleft = (10, add_rect_top)
        if self.game.add_vertex_mode:
            pygame.draw.rect(self.overlay, (0, 200, 255), self.game.add_vertex_rect, 2)
            add_surface = self.font.render(self.game.add_vertex_text, True, (0, 200, 255))
            self.overlay.blit(add_surface, (15, add_rect_top + 5))
            # Render validation error above the input if present
            if getattr(self.game, 'add_vertex_error', ""):
                err_surface = self.font.render(self.game.add_vertex_error, True, (255, 80, 80))
                self.overlay.blit(err_surface, (15, max(0, add_rect_top - 20)))
        else:
            add_hint = self.font.render("Add vertex: press P to enter [x, y, z]", True, (120, 120, 120))
            pygame.draw.rect(self.overlay, (80, 80, 80), self.game.add_vertex_rect, 1)
            self.overlay.blit(add_hint, (15, add_rect_top + 5))

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
            f"Add Vertex: {keybindings['add_vertex'].upper()} or Insert (enter [x, y, z])",
            "Delete Selected: Delete",
            f"Clear All Vertices: {keybindings.get('clear_vertices', 'x').upper()}",
            f"Save Vertices: {keybindings['save_vertices'].upper()} or F5",
            f"Change Filename: {keybindings['change_filename'].upper()} or F6",
            f"New File: {keybindings.get('new_file', 'n').upper()} or F9",
            f"Open File: {keybindings.get('open_file', 'b').upper()} or F3",
            f"Form Triangles: {keybindings['form_triangles'].upper()} or F7",
            f"Fix Inward-Facing Triangles (flip): {keybindings.get('remove_backfaces', 'f10').upper()} or F10",
            f"Check Edge (select 2 vertices): {keybindings.get('check_edge', 'f11').upper()} or F11",
            f"Remove Internal Edges (raycast): {keybindings.get('remove_internal_edges', 'f12').upper()} or F12",
            f"Yaw Left: {keybindings['yaw_left'].upper()} or Numpad 4",
            f"Yaw Right: {keybindings['yaw_right'].upper()} or Numpad 6",
            f"Pitch Up: {keybindings['pitch_up'].upper()} or Numpad 8",
            f"Pitch Down: {keybindings['pitch_down'].upper()} or Numpad 2",
            f"Toggle Wireframe: {keybindings['toggle_wireframe'].upper()} or F8",
            f"Help: {keybindings['help'].upper()} or F1",
            rotate_help,
            "Edit selected vertex: click its line or red box, then type [x, y, z], Enter to apply",
            "Press H or F1 again to close help",
        ]
        y = 20
        for text in help_texts[:-5]:
            surf = font.render(text, True, (255, 255, 255))
            self.overlay.blit(surf, (20, y))
            y += 30

        # Put the last five items on a second column
        second_col_x = self.width // 2 + 20
        y2 = 20
        for text in help_texts[-5:]:
            surf = font.render(text, True, (255, 255, 255))
            self.overlay.blit(surf, (second_col_x, y2))
            y2 += 30