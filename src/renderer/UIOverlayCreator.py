import pygame
import numpy as np
import os

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
        # File picker modal overlay
        if getattr(self.game, 'file_picker_mode', False):
            # Dim background
            dim = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 160))
            self.overlay.blit(dim, (0, 0))
            # Panel
            panel_w, panel_h = max(600, self.width // 2), min(self.height - 120, 40 + 30 * int(self.game.file_picker_max_visible))
            panel_x = (self.width - panel_w) // 2
            panel_y = (self.height - panel_h) // 2
            panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
            pygame.draw.rect(self.overlay, (30, 30, 30), panel_rect)
            pygame.draw.rect(self.overlay, (200, 200, 200), panel_rect, 2)
            # Title
            title = f"Open file in: {self.game.file_picker_dir}"
            title_surf = self.font.render(title, True, (255, 255, 0))
            self.overlay.blit(title_surf, (panel_x + 10, panel_y + 8))
            # Items
            self.game.file_picker_item_rects = []
            items = self.game.file_picker_items
            start = int(self.game.file_picker_scroll)
            end = min(len(items), start + int(self.game.file_picker_max_visible))
            y = panel_y + 35
            text_left = panel_x + 10
            for i in range(start, end):
                name = items[i]
                # Show basename for readability
                try:
                    display = name if len(name) < 2 else name
                    display = display if os.path.isabs(display) else name
                    display = os.path.basename(name)
                except Exception:
                    display = name
                selected = (i == int(self.game.file_picker_index))
                color = (0, 100, 200) if selected else (60, 60, 60)
                row_rect = pygame.Rect(panel_x + 6, y - 2, panel_w - 12, 26)
                pygame.draw.rect(self.overlay, color, row_rect)
                pygame.draw.rect(self.overlay, (100, 100, 100), row_rect, 1)
                text_color = (255, 255, 255)
                text_surface = self.font.render(display, True, text_color)
                self.overlay.blit(text_surface, (text_left, y))
                self.game.file_picker_item_rects.append((i, row_rect))
                y += 28
            # Hints
            hint = "Up/Down, PgUp/PgDn, Home/End, Enter to open, Esc to cancel"
            hint_surf = self.font.render(hint, True, (200, 200, 200))
            self.overlay.blit(hint_surf, (panel_x + 10, panel_y + panel_h - 24))
            return
        if self.game.help_mode:
            if getattr(self.game, 'shapes_mode', False):
                self.draw_shapes_help_screen()
            else:
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
        # Help prompt will be drawn later, after layout calculations, to avoid overlap with shapes inputs
        filename_text = self.font.render(f"{self.game.filename_text}", True, (255, 255, 0))
        self.overlay.blit(filename_text, (160, 10))
        
        # Create a clickable area for each vertex (hidden while in shapes mode)
        self.vertex_rects = []
        total_vertices = len(verticesHolder.vertices) // 6
        # Warn if vertex count not divisible by 3 (incomplete triangle at the end)
        trailing_count = total_vertices % 3
        trailing_indices = []
        if trailing_count != 0:
            trailing_indices = list(range(total_vertices - trailing_count, total_vertices)) if total_vertices >= trailing_count else []
            warn_text = f"Warning: {trailing_count} stray vertex" + ("" if trailing_count == 1 else "ices") + "; last triangle incomplete"
            warn_surface = self.font.render(warn_text, True, (255, 200, 0))
            # Top-right corner to avoid overlapping main UI
            self.overlay.blit(warn_surface, (max(10, self.width - 360), 10))
        if not getattr(self.game, 'shapes_mode', False):
            for i in range(self.scroll_offset, min(self.scroll_offset + self.max_visible_vertices, total_vertices)):
                vertex_text = f"Vertex {i}: {verticesHolder.vertices[i * 6:i * 6 + 3]}"
                # Dark purple for trailing (stray) vertices in the list
                if i in trailing_indices:
                    color = (128, 0, 128)
                else:
                    color = (255, 0, 0) if i in self.game.selected_vertices else (255, 255, 0) if i in self.game.yellow_highlights else (255, 255, 255)
                text_surface = self.font.render(vertex_text, True, color)
                y_position = 40 + (i - self.scroll_offset) * 30
                self.overlay.blit(text_surface, (10, y_position))
                
                # Create a clickable area for each vertex
                vertex_rect = self.get_vertex_rect(i, y_position)
                self.vertex_rects.append((i, vertex_rect))
                pygame.draw.rect(self.overlay, (100, 100, 100), vertex_rect, 1)

        # Draw scroll indicators if necessary
        if not getattr(self.game, 'shapes_mode', False):
            if self.scroll_offset > 0:
                pygame.draw.polygon(self.overlay, (255, 255, 255), [(10, 35), (20, 25), (30, 35)])
            if total_vertices > self.scroll_offset + self.max_visible_vertices:
                pygame.draw.polygon(self.overlay, (255, 255, 255), [(10, self.height - 85), (20, self.height - 75), (30, self.height - 85)])

        # Unified filename input area (Save/Open/New) at single position
        bottom_padding = 10
        rect_height = self.game.filename_rect.height
        unified_top = self.height - rect_height - bottom_padding
        self.game.filename_rect.topleft = (10, unified_top)

        if self.game.filename_edit_mode:
            purpose = getattr(self.game, 'filename_edit_purpose', 'save')
            # Color by purpose
            color = (0, 255, 0) if purpose == 'save' else (0, 200, 255) if purpose == 'open' else (255, 200, 0)
            pygame.draw.rect(self.overlay, color, self.game.filename_rect, 2)
            input_surface = self.font.render(self.game.filename_text, True, color)
            self.overlay.blit(input_surface, (15, unified_top + 5))
        else:
            # No hint text; covered by help screen
            pygame.draw.rect(self.overlay, (80, 80, 80), self.game.filename_rect, 1)
        # Add-vertex input field above unified area
        add_rect_top = unified_top - 35
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
            pygame.draw.rect(self.overlay, (80, 80, 80), self.game.add_vertex_rect, 1)
            # Intentionally no hint text on main screen

        # Extrude input field next to add-vertex
        self.game.extrude_rect.top = add_rect_top
        if self.game.extrude_mode:
            pygame.draw.rect(self.overlay, (200, 160, 0), self.game.extrude_rect, 2)
            extrude_surface = self.font.render(self.game.extrude_text, True, (200, 160, 0))
            self.overlay.blit(extrude_surface, (self.game.extrude_rect.left + 5, add_rect_top + 5))
            if getattr(self.game, 'extrude_error', ""):
                err_surface = self.font.render(self.game.extrude_error, True, (255, 80, 80))
                self.overlay.blit(err_surface, (self.game.extrude_rect.left, max(0, add_rect_top - 20)))
            # Show base point used for extrusion, if available
            try:
                base_pt = getattr(self.game, 'extrude_base_point', None)
                if base_pt is not None and len(base_pt) == 3:
                    base_text = f"Base P: [{float(base_pt[0]):.3f}, {float(base_pt[1]):.3f}, {float(base_pt[2]):.3f}]"
                    base_surface = self.font.render(base_text, True, (200, 160, 0))
                    self.overlay.blit(base_surface, (self.game.extrude_rect.left, max(0, add_rect_top - 20)))
            except Exception:
                pass
        else:
            pygame.draw.rect(self.overlay, (80, 80, 80), self.game.extrude_rect, 1)

        # Shapes mode banner and inputs
        if getattr(self.game, 'shapes_mode', False):
            banner = self.font.render("Shapes Mode", True, (0, 255, 180))
            # Place banner slightly below the shapes input row to avoid overlap with input text
            self.overlay.blit(banner, (self.game.extrude_rect.left, (add_rect_top - 35) + 30))

            # Place shape inputs on a row above the bottom inputs to ensure visibility on 800x600
            row_y = add_rect_top - 35

            # Only show shape input fields after a shape flow has started
            if getattr(self.game, 'shape_input_mode', None) is not None:
                # Primary field: fixed at left margin to avoid overlap on 800x600
                self.game.shape_primary_rect.top = row_y
                self.game.shape_primary_rect.left = 10
                pygame.draw.rect(self.overlay, (0, 255, 180), self.game.shape_primary_rect, 2)
                primary_label = "Point [x, y, z]" if self.game.shape_step in (None, 'point') else ("Width" if self.game.shape_step == 'width' else ("Sides" if self.game.shape_step == 'sides' else ""))
                primary_text = self.game.shape_primary_text if self.game.shape_primary_text else primary_label
                primary_surface = self.font.render(primary_text, True, (0, 255, 180))
                self.overlay.blit(primary_surface, (self.game.shape_primary_rect.left + 5, row_y + 5))

                # Secondary field (Length): position to the right of primary with a gap, clamped within screen
                self.game.shape_secondary_rect.top = row_y
                desired_left = self.game.shape_primary_rect.left + self.game.shape_primary_rect.width + 20
                max_left = self.width - self.game.shape_secondary_rect.width - 10
                self.game.shape_secondary_rect.left = max(10, min(desired_left, max_left))
                show_secondary = (self.game.shape_input_mode == 'rectangle' and self.game.shape_step == 'length')
                if show_secondary:
                    pygame.draw.rect(self.overlay, (0, 255, 180), self.game.shape_secondary_rect, 2)
                    secondary_label = "Length"
                    secondary_text = self.game.shape_secondary_text if self.game.shape_secondary_text else secondary_label
                    secondary_surface = self.font.render(secondary_text, True, (0, 255, 180))
                    self.overlay.blit(secondary_surface, (self.game.shape_secondary_rect.left + 5, row_y + 5))

                if getattr(self.game, 'shape_error', ""):
                    err_surface = self.font.render(self.game.shape_error, True, (255, 80, 80))
                    self.overlay.blit(err_surface, (self.game.shape_primary_rect.left, max(0, row_y - 20)))

            # Place help prompt further above shapes row to avoid overlap with error text
            help_prompt = self.font.render(f"Press {keybindings['help'].upper()} for help", True, (0, 255, 255))
            self.overlay.blit(help_prompt, (10, max(10, row_y - 50)))
        else:
            # Default help prompt position when not in shapes mode
            help_prompt = self.font.render(f"Press {keybindings['help'].upper()} for help", True, (0, 255, 255))
            self.overlay.blit(help_prompt, (10, self.height - 110))

        # Axis guides at base vertex during rectangle two-vertex 'direction' step
        try:
            if (
                getattr(self.game, 'shapes_mode', False)
                and getattr(self.game, 'shape_input_mode', None) == 'rectangle'
                and getattr(self.game, 'shape_step', None) == 'direction'
                and hasattr(self.game, 'event_handler')
                and getattr(self.game.event_handler, '_shape_two_vertices_mode', False)
            ):
                base_world = None
                # Prefer stored base point from the rectangle flow
                if hasattr(self.game.event_handler, '_shape_edge_p0'):
                    base_world = np.array(self.game.event_handler._shape_edge_p0, dtype=float)
                # Fallback to highlighted base vertex index
                elif getattr(self.game.event_handler, '_shape_base_index', None) is not None:
                    idx = int(self.game.event_handler._shape_base_index)
                    verts = verticesHolder.vertices.reshape(-1, 6)
                    if 0 <= idx < len(verts):
                        base_world = verts[idx, :3].astype(float)
                if base_world is not None:
                    # Compute fixed pixel-length guides using screen-space directions
                    px_len = 50.0
                    eps = 0.05
                    pts_world = np.vstack([
                        base_world,
                        base_world + np.array([eps, 0.0, 0.0], dtype=float),
                        base_world + np.array([0.0, eps, 0.0], dtype=float),
                        base_world + np.array([0.0, 0.0, eps], dtype=float),
                    ])
                    screen_pts = self.game.renderer.renderer3D.world_to_screen(pts_world)
                    bx, by = screen_pts[0]
                    if not (np.isnan(bx) or np.isnan(by)):
                        # Draw base coordinates near the base screen position
                        try:
                            bx_text = f"[{base_world[0]:.3f}, {base_world[1]:.3f}, {base_world[2]:.3f}]"
                            base_text_surface = self.font.render(bx_text, True, (255, 255, 255))
                            shadow_surface = self.font.render(bx_text, True, (0, 0, 0))
                            # Slight shadow for readability
                            self.overlay.blit(shadow_surface, (bx + 7, by + 7))
                            self.overlay.blit(base_text_surface, (bx + 6, by + 6))
                        except Exception:
                            pass
                        dir_vectors = [screen_pts[1] - screen_pts[0], screen_pts[2] - screen_pts[0], screen_pts[3] - screen_pts[0]]
                        colors = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]
                        labels = ["+X", "+Y", "+Z"]
                        for d, color, label in zip(dir_vectors, colors, labels):
                            dx, dy = float(d[0]), float(d[1])
                            if np.isnan(dx) or np.isnan(dy):
                                continue
                            dlen = (dx*dx + dy*dy) ** 0.5
                            if dlen <= 1e-6:
                                continue
                            nx, ny = dx / dlen, dy / dlen
                            ex, ey = bx + nx * px_len, by + ny * px_len
                            pygame.draw.line(self.overlay, color, (bx, by), (ex, ey), 2)
                            # Draw label slightly beyond the line end along its direction
                            tx, ty = ex + nx * 6.0, ey + ny * 6.0
                            text_surface = self.font.render(label, True, (color[0], color[1], color[2]))
                            self.overlay.blit(text_surface, (tx, ty))
        except Exception:
            # Avoid overlay crashes from any transient state issues
            pass

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
        # Draw trailing (stray) vertex markers in dark purple
        if trailing_indices:
            vertices = verticesHolder.vertices.reshape(-1, 6)
            try:
                trailing_pos = vertices[trailing_indices, :3]
                screen_coords = self.game.renderer.renderer3D.world_to_screen(trailing_pos)
                square_size = 10
                for coord in screen_coords:
                    sx, sy = coord
                    if not np.isnan(sx) and not np.isnan(sy) and 0 <= sx < self.width and 0 <= sy < self.height:
                        rect = pygame.Rect(sx - square_size // 2, sy - square_size // 2, square_size, square_size)
                        pygame.draw.rect(self.overlay, (128, 0, 128, 255), rect)
            except Exception:
                pass

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
            f"Fill with triangles between selected points: {keybindings['form_triangles'].upper()} or F7",
            f"Fix Inward-Facing Triangles (flip): {keybindings.get('remove_backfaces', 'f10').upper()} or F10",
            f"Check Edge (select 2 vertices): {keybindings.get('check_edge', 'f11').upper()} or F11",
            "  - Yellow = endpoints of matching triangle edge(s) in the vertex list",
            f"Remove Internal Edges (raycast): {keybindings.get('remove_internal_edges', 'f12').upper()} or F12",
            f"Extrude selected: {keybindings.get('extrude', 'e').upper()} (enter P' [x, y, z])",
            f"Yaw Left: {keybindings['yaw_left'].upper()} or Numpad 4",
            f"Yaw Right: {keybindings['yaw_right'].upper()} or Numpad 6",
            f"Pitch Up: {keybindings['pitch_up'].upper()} or Numpad 8",
            f"Pitch Down: {keybindings['pitch_down'].upper()} or Numpad 2",
            f"Toggle Wireframe: {keybindings['toggle_wireframe'].upper()} or F8",
            f"Undo last action: Ctrl+Z or {keybindings.get('undo', 'z').upper()}",
            f"Help: {keybindings['help'].upper()} or F1",
            rotate_help,
            f"Toggle Shapes Mode (enter/exit): {keybindings.get('shapes_mode', 'm').upper()}",
            "Edit selected vertex: click its line or red box, ", 
            "  then type [x, y, z], Enter to apply",
            "Press H or F1 again to close help",
        ]
        y = 20
        for text in help_texts[:-13]:
            surf = font.render(text, True, (255, 255, 255))
            self.overlay.blit(surf, (20, y))
            y += 30

        # Put the remaining items on a second column
        second_col_x = self.width // 2 + 20
        y2 = 20
        for text in help_texts[-13:]:
            surf = font.render(text, True, (255, 255, 255))
            self.overlay.blit(surf, (second_col_x, y2))
            y2 += 30

    def draw_shapes_help_screen(self):
        font = pygame.font.Font(None, 24)
        texts = [
            "Shapes Mode:",
            f"Toggle Shapes Mode (enter/exit): {keybindings.get('shapes_mode', 'm').upper()}",
            f"Rectangle: {keybindings.get('shape_rectangle', 'r').upper()} — enter [x, y, z], width, length",
            f"Regular N-gon: {keybindings.get('shape_ngon', 'g').upper()} — enter [x, y, z], sides (>=3)",
            f"Undo last action: Ctrl+Z or {keybindings.get('undo', 'z').upper()}",
            "Confirm current field: Enter",
            "Edit current field: Backspace",
            f"Help: {keybindings['help'].upper()} or F1 to close",
        ]
        y = 20
        for text in texts:
            surf = font.render(text, True, (255, 255, 255))
            self.overlay.blit(surf, (20, y))
            y += 30