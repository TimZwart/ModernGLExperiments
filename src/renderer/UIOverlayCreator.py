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
        # Cache for internal-triangle debug origin occlusion test (to avoid doing heavy ray tests every frame)
        self._internal_debug_occlusion = {
            'last_time_ms': -1,
            'last_eye': None,
            'last_look': None,
            'last_point': None,
            'occluded': False,
        }

    def _ray_intersects_triangle_3d(self, origin, direction, v0, v1, v2, eps=1e-8):
        # Möller–Trumbore intersection; returns (hit:bool, t:float|None)
        edge1 = v1 - v0
        edge2 = v2 - v0
        pvec = np.cross(direction, edge2)
        det = float(np.dot(edge1, pvec))
        if -eps < det < eps:
            return False, None
        inv_det = 1.0 / det
        tvec = origin - v0
        u = float(np.dot(tvec, pvec) * inv_det)
        if u < 0.0 - eps or u > 1.0 + eps:
            return False, None
        qvec = np.cross(tvec, edge1)
        v = float(np.dot(direction, qvec) * inv_det)
        if v < 0.0 - eps or u + v > 1.0 + eps:
            return False, None
        t = float(np.dot(edge2, qvec) * inv_det)
        if t <= eps:
            return False, None
        return True, t

    def _is_point_occluded_from_camera(self, world_point, max_age_ms: int = 200) -> bool:
        """Return True if any triangle blocks the segment from the camera eye to world_point."""
        try:
            now = pygame.time.get_ticks()
            eye = tuple(getattr(self.game.camera, 'eye', (0.0, 0.0, 0.0)))
            look = tuple(getattr(self.game.camera, 'look_at', (0.0, 0.0, 0.0)))
            pt = (float(world_point[0]), float(world_point[1]), float(world_point[2]))
            cache = self._internal_debug_occlusion

            if (cache['last_time_ms'] >= 0) and (now - cache['last_time_ms'] <= max_age_ms) and \
               (cache['last_eye'] == eye) and (cache['last_look'] == look) and (cache['last_point'] == pt):
                return bool(cache['occluded'])

            cam = np.array(eye, dtype=np.float64)
            p = np.array(pt, dtype=np.float64)
            dv = p - cam
            dist = float(np.linalg.norm(dv))
            if dist <= 1e-9:
                occluded = False
            else:
                d = dv / dist
                rows = verticesHolder.vertices.reshape(-1, 6)
                tri_count = len(rows) // 3
                tri_rows = rows[:tri_count * 3]
                tri_pos = tri_rows.reshape(tri_count, 3, 6)[:, :, :3].astype(np.float64)
                occluded = False
                # Early-out: any hit before reaching p means occluded
                limit = dist - 1e-6
                for t in range(tri_count):
                    v0, v1, v2 = tri_pos[t]
                    hit, tt = self._ray_intersects_triangle_3d(cam, d, v0, v1, v2)
                    if hit and tt is not None and float(tt) < limit:
                        occluded = True
                        break

            cache['last_time_ms'] = int(now)
            cache['last_eye'] = eye
            cache['last_look'] = look
            cache['last_point'] = pt
            cache['occluded'] = bool(occluded)
            return bool(occluded)
        except Exception:
            return False

    def _pos_placeholder(self):
        return "[x, y, z]"

    def _color_placeholder(self):
        # Show current color rounded as hint
        try:
            col = getattr(self.game, 'current_color', [1.0, 1.0, 1.0])
            r = f"{float(col[0]):.3f}"
            g = f"{float(col[1]):.3f}"
            b = f"{float(col[2]):.3f}"
            return f"[{r}, {g}, {b}]"
        except Exception:
            return "[r, g, b]"

    def _ellipsize_path(self, path: str, max_width: int) -> str:
        """Return a version of the path that fits within max_width using ellipsis.
        Prefers keeping the filename (tail) visible.
        """
        try:
            if max_width <= 0:
                return "..."
            if self.font.size(path)[0] <= max_width:
                return path
            ellipsis = "..."
            base = os.path.basename(path) or path
            # If we can show at least the filename with an ellipsis prefix, prefer that
            candidate = ellipsis + base
            if self.font.size(candidate)[0] <= max_width:
                return candidate
            # Otherwise, shorten the filename itself from the left side
            # Binary search the longest tail of base that fits with ellipsis
            low, high = 0, len(base)
            best = ellipsis
            while low <= high:
                mid = (low + high) // 2
                tail = base[-mid:] if mid > 0 else ""
                cand = ellipsis + tail
                w = self.font.size(cand)[0]
                if w <= max_width:
                    best = cand
                    low = mid + 1
                else:
                    high = mid - 1
            return best
        except Exception:
            return "..."

    def get_vertex_rect(self, index, y_position):
        vertex_text = f"Vertex {index}: {verticesHolder.vertices[index * 6:index * 6 + 3]}"
        text_width, text_height = self.font.size(vertex_text)
        return pygame.Rect(10, y_position, text_width + 10, 30)

    def draw_ui_overlay(self):
        # Clear the overlay
        self.overlay.fill((0, 0, 0, 0))
        # During disambiguation, draw colored triangle overlays on top of normal UI
        disambiguating = getattr(self.game, 'disambiguation_mode', False)
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
            if getattr(self.game, 'cleanup_mode', False):
                self.draw_cleanup_help_screen()
            elif getattr(self.game, 'shapes_mode', False):
                self.draw_shapes_help_screen()
            else:
                self.draw_help_screen()
            return
        # View Mode modal overlay
        if getattr(self.game, 'view_mode', False):
            self.draw_view_mode_screen()
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
        # Ensure the filepath fits on screen by ellipsizing if necessary
        left_x = 160
        right_margin = 10
        max_w = max(0, self.width - right_margin - left_x)
        # Filename uses full available width; warning will be placed on next line
        display_path = self._ellipsize_path(f"{self.game.filename_text}", max_w)
        filename_text = self.font.render(display_path, True, (255, 255, 0))
        self.overlay.blit(filename_text, (left_x, 10))
        
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
            # Place warning below filename line, aligned with filename column
            warn_y = 10 + self.font.get_height() + 4
            self.overlay.blit(warn_surface, (left_x, warn_y))
        if not getattr(self.game, 'shapes_mode', False):
            for i in range(self.scroll_offset, min(self.scroll_offset + self.max_visible_vertices, total_vertices)):
                vertex_text = f"Vertex {i}: {verticesHolder.vertices[i * 6:i * 6 + 3]}"
                # Dark purple for trailing (stray) vertices in the list
                if i in trailing_indices:
                    color = (128, 0, 128)
                else:
                    tri_hl = getattr(self.game, 'triangle_highlights', set())
                    color = (255, 0, 0) if i in self.game.selected_vertices else (255, 255, 0) if (i in self.game.yellow_highlights or i in tri_hl) else (255, 255, 255)
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
        
        # Color picker modal overlay
        if getattr(self.game, 'color_picker_mode', False):
            self.draw_color_picker()
        # Add-vertex input field above unified area
        add_rect_top = unified_top - 35
        self.game.add_vertex_rect.topleft = (10, add_rect_top)
        if self.game.add_vertex_mode:
            # Position field
            self.game.add_vertex_pos_rect.topleft = (10, add_rect_top)
            pygame.draw.rect(self.overlay, (0, 200, 255) if self.game.add_vertex_focus == 'pos' else (0, 120, 150), self.game.add_vertex_pos_rect, 2)
            pos_text = self.game.add_vertex_pos_text if self.game.add_vertex_pos_text else self._pos_placeholder()
            pos_color = (0, 200, 255) if self.game.add_vertex_focus == 'pos' else (0, 200, 255)
            pos_surface = self.font.render(pos_text, True, pos_color)
            self.overlay.blit(pos_surface, (self.game.add_vertex_pos_rect.left + 5, add_rect_top + 5))
            # Color field
            self.game.add_vertex_color_rect.top = add_rect_top + 35
            self.game.add_vertex_color_rect.left = 10
            pygame.draw.rect(self.overlay, (0, 200, 255) if self.game.add_vertex_focus == 'color' else (0, 120, 150), self.game.add_vertex_color_rect, 2)
            col_text = self.game.add_vertex_color_text if self.game.add_vertex_color_text else self._color_placeholder()
            col_color = (0, 200, 255) if self.game.add_vertex_focus == 'color' else (0, 200, 255)
            col_surface = self.font.render(col_text, True, col_color)
            self.overlay.blit(col_surface, (self.game.add_vertex_color_rect.left + 5, self.game.add_vertex_color_rect.top + 5))
            # Validation error above the first input if present
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

        # Cleanup Mode banner
        if getattr(self.game, 'cleanup_mode', False):
            banner = self.font.render("Cleanup Mode", True, (255, 200, 0))
            self.overlay.blit(banner, (self.game.extrude_rect.left, (add_rect_top - 35) + 30))

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
                    # Position the label slightly higher and to the right to avoid overlap
                    label_x = 160
                    label_y = self.height - 95
                else:
                    selected_text = self.font.render(f"Selected Vertex {selected}: {selected_coords}", True, (255, 255, 0))
                    label_x = 10
                    label_y = self.height - 50
                self.overlay.blit(selected_text, (label_x, label_y))

                # Update editable area
                self.game.edit_rect.top = self.height - 35
                pygame.draw.rect(self.overlay, (255, 255, 0), self.game.edit_rect, 2)

                if self.game.edit_mode:
                    # Draw two edit fields side-by-side: position (left), color (right)
                    self.game.edit_pos_rect.top = self.height - 35
                    self.game.edit_pos_rect.left = 10
                    self.game.edit_color_rect.top = self.height - 35
                    desired_left = self.game.edit_pos_rect.left + self.game.edit_pos_rect.width + 15
                    max_left = self.width - self.game.edit_color_rect.width - 10
                    self.game.edit_color_rect.left = max(10, min(desired_left, max_left))

                    # Labels above fields
                    try:
                        pos_label = self.font.render("pos:", True, (255, 255, 0))
                        color_label = self.font.render("color:", True, (255, 255, 0))
                        self.overlay.blit(pos_label, (self.game.edit_pos_rect.left, max(0, self.game.edit_pos_rect.top - 20)))
                        self.overlay.blit(color_label, (self.game.edit_color_rect.left, max(0, self.game.edit_color_rect.top - 20)))
                    except Exception:
                        pass

                    # Position field
                    pygame.draw.rect(self.overlay, (255, 255, 0) if self.game.edit_focus == 'pos' else (150, 150, 0), self.game.edit_pos_rect, 2)
                    pos_text = self.game.edit_pos_text if getattr(self.game, 'edit_pos_text', "") else self._pos_placeholder()
                    pos_surface = self.font.render(pos_text, True, (255, 255, 0))
                    self.overlay.blit(pos_surface, (self.game.edit_pos_rect.left + 5, self.game.edit_pos_rect.top + 5))

                    # Color field
                    pygame.draw.rect(self.overlay, (255, 255, 0) if self.game.edit_focus == 'color' else (150, 150, 0), self.game.edit_color_rect, 2)
                    color_text = self.game.edit_color_text if getattr(self.game, 'edit_color_text', "") else self._color_placeholder()
                    color_surface = self.font.render(color_text, True, (255, 255, 0))
                    self.overlay.blit(color_surface, (self.game.edit_color_rect.left + 5, self.game.edit_color_rect.top + 5))
            else:
                selected_list = sorted(list(self.game.selected_vertices))
                # Header showing which vertices are selected
                header_text = self.font.render(f"Selected Vertices: {selected_list}", True, (255, 255, 0))
                self.overlay.blit(header_text, (10, self.height - 80))

                # When editing with multiple selected, show color-only field
                if self.game.edit_mode:
                    # Place color field at the standard input row
                    self.game.edit_color_rect.top = self.height - 35
                    self.game.edit_color_rect.left = 10
                    try:
                        color_label = self.font.render("color:", True, (255, 255, 0))
                        self.overlay.blit(color_label, (self.game.edit_color_rect.left, max(0, self.game.edit_color_rect.top - 20)))
                    except Exception:
                        pass
                    pygame.draw.rect(self.overlay, (255, 255, 0) if self.game.edit_focus == 'color' else (150, 150, 0), self.game.edit_color_rect, 2)
                    color_text = self.game.edit_color_text if getattr(self.game, 'edit_color_text', "") else self._color_placeholder()
                    color_surface = self.font.render(color_text, True, (255, 255, 0))
                    self.overlay.blit(color_surface, (self.game.edit_color_rect.left + 5, self.game.edit_color_rect.top + 5))
                else:
                    # Show color-only input field (inactive) so it's visible/clickable
                    self.game.edit_color_rect.top = self.height - 35
                    self.game.edit_color_rect.left = 10
                    try:
                        color_label = self.font.render("color:", True, (180, 180, 100))
                        self.overlay.blit(color_label, (self.game.edit_color_rect.left, max(0, self.game.edit_color_rect.top - 20)))
                    except Exception:
                        pass
                    pygame.draw.rect(self.overlay, (80, 80, 80), self.game.edit_color_rect, 1)
                    color_text = self._color_placeholder()
                    color_surface = self.font.render(color_text, True, (180, 180, 100))
                    self.overlay.blit(color_surface, (self.game.edit_color_rect.left + 5, self.game.edit_color_rect.top + 5))

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

        # If there are yellow highlights (e.g., candidate triangles), draw their vertices as yellow squares
        combined_hl = set(getattr(self.game, 'yellow_highlights', set())) | set(getattr(self.game, 'triangle_highlights', set()))
        if combined_hl:
            try:
                hl_indices = sorted(list(combined_hl))
                rows = verticesHolder.vertices.reshape(-1, 6)
                pos = rows[hl_indices, :3]
                pts = self.game.renderer.renderer3D.world_to_screen(pos)
                for sx, sy in pts:
                    if not (np.isnan(sx) or np.isnan(sy)):
                        rect = pygame.Rect(sx - 4, sy - 4, 8, 8)
                        pygame.draw.rect(self.overlay, (255, 255, 0, 255), rect, 2)
            except Exception:
                pass

        # Triangle selection tool: draw selected triangles (filled + outline) and a small panel.
        if getattr(self.game, 'triangle_select_mode', False):
            try:
                rows = verticesHolder.vertices.reshape(-1, 6)
                tri_set = list(getattr(self.game, 'selected_triangles', set()))
                active = getattr(self.game, 'last_selected_triangle_index', None)
                for t in tri_set:
                    ti = int(t)
                    i0 = ti * 3
                    if i0 + 2 >= len(rows):
                        continue
                    pos = rows[[i0 + 0, i0 + 1, i0 + 2], :3]
                    pts = self.game.renderer.renderer3D.world_to_screen(pos)
                    if np.isnan(pts).any():
                        continue
                    poly = [(float(pts[0][0]), float(pts[0][1])), (float(pts[1][0]), float(pts[1][1])), (float(pts[2][0]), float(pts[2][1]))]
                    if active is not None and int(active) == ti:
                        fill = (0, 200, 255, 70)
                        outline = (0, 255, 255, 230)
                    else:
                        fill = (0, 160, 200, 50)
                        outline = (0, 200, 255, 180)
                    pygame.draw.polygon(self.overlay, fill, poly)
                    pygame.draw.polygon(self.overlay, outline, poly, 2)
            except Exception:
                pass
            self._draw_triangle_selection_panel()

        # Cleanup inspector: draw triangles whose vertices share positions with the current selection
        if getattr(self.game, 'cleanup_mode', False) and getattr(self.game, 'cleanup_position_overlays', []):
            try:
                overlays = self.game.cleanup_position_overlays
                wireframes = getattr(self.game, 'cleanup_position_wireframes', [])
                # Draw wireframes for non-matching triangles first
                if wireframes:
                    for wf in wireframes:
                        if len(wf) == 3:
                            pygame.draw.polygon(self.overlay, (200, 200, 200, 180), wf, 1)
                for ov in overlays:
                    pts = ov.get('screen_pts', [])
                    color = ov.get('color', (255, 0, 0, 120))
                    if len(pts) == 3:
                        # Filled triangle
                        pygame.draw.polygon(self.overlay, color, pts)
                        # Outline for clarity
                        outline = (color[0], color[1], color[2], 220)
                        pygame.draw.polygon(self.overlay, outline, pts, 2)
                        # Coordinates label near centroid
                        label_pos = ov.get('label_pos', (pts[0][0], pts[0][1]))
                        labels = ov.get('labels', [])
                        for idx, line in enumerate(labels):
                            text_surface = self.font.render(line, True, (color[0], color[1], color[2]))
                            self.overlay.blit(text_surface, (label_pos[0] + 6, label_pos[1] + 6 + idx * 18))
            except Exception:
                pass

        # Internal triangle inspector: draw failing rays + a small report panel
        # Note: rays remain visible even after leaving Cleanup Mode, so the user can move the camera around.
        if getattr(self.game, 'internal_triangle_debug_rays', []):
            try:
                rays = list(getattr(self.game, 'internal_triangle_debug_rays', []))
                # Determine whether the origin (triangle centroid) is occluded from the current camera view.
                origin_world = None
                try:
                    if rays:
                        origin_world = rays[0].get('origin', None)
                except Exception:
                    origin_world = None
                origin_occluded = False
                if origin_world is not None and isinstance(origin_world, (list, tuple)) and len(origin_world) == 3:
                    origin_occluded = self._is_point_occluded_from_camera(origin_world)
                origin_marker_color = (160, 160, 160, 230) if origin_occluded else (255, 0, 0, 230)

                # Build a list of endpoints for projection (origin+end per ray)
                pts3d = []
                for r in rays:
                    pts3d.append(r.get('origin', [0.0, 0.0, 0.0]))
                    pts3d.append(r.get('end', [0.0, 0.0, 0.0]))
                pts3d = np.array(pts3d, dtype=float).reshape(-1, 3)
                pts2d = self.game.renderer.renderer3D.world_to_screen(pts3d)
                # Draw rays and hit labels
                for i, r in enumerate(rays):
                    a = pts2d[i * 2 + 0]
                    b = pts2d[i * 2 + 1]
                    ax, ay = float(a[0]), float(a[1])
                    bx, by = float(b[0]), float(b[1])
                    if np.isnan(ax) or np.isnan(ay) or np.isnan(bx) or np.isnan(by):
                        continue
                    color = r.get('color', (255, 0, 0, 220))
                    pygame.draw.line(self.overlay, color, (ax, ay), (bx, by), 2)
                    pygame.draw.circle(self.overlay, color, (int(bx), int(by)), 3)
                    # Mark the ray origin with a tiny triangle (grey if occluded from camera POV, red otherwise)
                    try:
                        dx = bx - ax
                        dy = by - ay
                        n = (dx * dx + dy * dy) ** 0.5
                        if n < 1e-6:
                            ux, uy = 1.0, 0.0
                        else:
                            ux, uy = dx / n, dy / n
                        px, py = -uy, ux
                        size = 6.0
                        tip = (ax + ux * size * 2.0, ay + uy * size * 2.0)
                        base = (ax - ux * size * 0.8, ay - uy * size * 0.8)
                        p1 = (base[0] + px * size * 0.9, base[1] + py * size * 0.9)
                        p2 = (base[0] - px * size * 0.9, base[1] - py * size * 0.9)
                        pygame.draw.polygon(self.overlay, origin_marker_color, [tip, p1, p2])
                    except Exception:
                        pass
                    hits = int(r.get('hits', 0))
                    di = int(r.get('dir_index', -1))
                    label = f"d{di:02d}:{hits}"
                    text = self.font.render(label, True, (255, 255, 255))
                    self.overlay.blit(text, (bx + 6, by + 2))
            except Exception:
                pass
            # Highlight triangles that are closest to the missed rays (yellow edges)
            try:
                closest_tris = set(getattr(self.game, 'internal_triangle_debug_closest_triangles', set()))
                if closest_tris:
                    rows = verticesHolder.vertices.reshape(-1, 6)
                    tri_count = len(rows) // 3
                    pts3d = []
                    tri_ids = []
                    for t in sorted(list(closest_tris)):
                        ti = int(t)
                        if ti < 0 or ti >= tri_count:
                            continue
                        i0 = ti * 3
                        pos = rows[[i0 + 0, i0 + 1, i0 + 2], :3]
                        pts3d.append(pos[0].tolist())
                        pts3d.append(pos[1].tolist())
                        pts3d.append(pos[2].tolist())
                        tri_ids.append(ti)
                    if pts3d:
                        pts3d = np.array(pts3d, dtype=float).reshape(-1, 3)
                        pts2d = self.game.renderer.renderer3D.world_to_screen(pts3d)
                        for i, ti in enumerate(tri_ids):
                            p0 = pts2d[i * 3 + 0]
                            p1 = pts2d[i * 3 + 1]
                            p2 = pts2d[i * 3 + 2]
                            x0, y0 = float(p0[0]), float(p0[1])
                            x1, y1 = float(p1[0]), float(p1[1])
                            x2, y2 = float(p2[0]), float(p2[1])
                            if np.isnan(x0) or np.isnan(y0) or np.isnan(x1) or np.isnan(y1) or np.isnan(x2) or np.isnan(y2):
                                continue
                            pygame.draw.polygon(self.overlay, (255, 255, 0, 230), [(x0, y0), (x1, y1), (x2, y2)], 3)
            except Exception:
                pass
            # Draw closest-point pairs (green on triangle, red on ray) for each missed ray
            try:
                pairs = list(getattr(self.game, 'internal_triangle_debug_closest_points', []))
                if pairs:
                    pts3d = []
                    for p in pairs:
                        pts3d.append(p.get('pt_tri', [0.0, 0.0, 0.0]))
                        pts3d.append(p.get('pt_ray', [0.0, 0.0, 0.0]))
                    pts3d = np.array(pts3d, dtype=float).reshape(-1, 3)
                    pts2d = self.game.renderer.renderer3D.world_to_screen(pts3d)
                    for i in range(len(pairs)):
                        tri_pt = pts2d[i * 2 + 0]
                        ray_pt = pts2d[i * 2 + 1]
                        tx, ty = float(tri_pt[0]), float(tri_pt[1])
                        rx, ry = float(ray_pt[0]), float(ray_pt[1])
                        if not (np.isnan(tx) or np.isnan(ty)):
                            pygame.draw.circle(self.overlay, (255, 255, 0, 230), (int(tx), int(ty)), 5)
                        if not (np.isnan(rx) or np.isnan(ry)):
                            pygame.draw.circle(self.overlay, (255, 0, 0, 230), (int(rx), int(ry)), 5)
            except Exception:
                pass
            self._draw_internal_triangle_inspector_panel()

        # Draw disambiguation colored triangle overlays last (so they sit on top)
        if disambiguating:
            try:
                # Dim entire screen slightly to focus on choice
                dim = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 80))
                self.overlay.blit(dim, (0, 0))
                tris = getattr(self.game, 'disambiguation_triangles', [])
                for ov in tris:
                    pts = ov.get('screen_pts', [])
                    color = ov.get('color', (255, 255, 0, 110))
                    if len(pts) == 3:
                        # Filled triangle
                        pygame.draw.polygon(self.overlay, color, pts)
                        # Outline for clarity
                        pygame.draw.polygon(self.overlay, (255, 255, 255, 220), pts, 2)
                kind = getattr(self.game, 'disambiguation_kind', 'vertex')
                hint = "Click a colored triangle to choose (Esc to cancel)" if kind == 'triangle' else "Click a colored triangle to choose the vertex (Esc to cancel)"
                hint_surf = self.font.render(hint, True, (255, 255, 255))
                self.overlay.blit(hint_surf, (10, 10))
                # For triangle disambiguation, also draw a clickable list panel.
                if kind == 'triangle':
                    self._draw_disambiguation_triangle_panel()
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
            f"Add Vertex: {keybindings['add_vertex'].upper()} or Insert",
            "  then enter position [x, y, z] and color [r, g, b]",
            "  or press C to open color picker",
            "Delete Selected: Delete",
            f"Deselect All: {keybindings.get('deselect_all', '-').upper()}",
            f"Save Vertices: {keybindings['save_vertices'].upper()} or F5",
            f"Change Filename: {keybindings['change_filename'].upper()} or F6",
            f"New File: {keybindings.get('new_file', 'n').upper()} or F9",
            f"Open File: {keybindings.get('open_file', 'b').upper()} or F3",
            f"Fill with triangles between selected points: {keybindings['form_triangles'].upper()} or F7",
            f"Triangle Select Tool: {keybindings.get('select_triangles', 't').upper()} (click triangles; Ctrl+click multi-select)",
            f"Check Triangle Exists (3 selected positions): {keybindings.get('check_triangle_positions', 'p').upper()}",
            f"View Mode: {keybindings.get('view_mode', 'v').upper()} (choose views, wireframe, distance fade)",
            f"Extrude selected: {keybindings.get('extrude', 'e').upper()} (enter P' [x, y, z])",
            f"Yaw Left: {keybindings['yaw_left'].upper()} or Numpad 4",
            f"Yaw Right: {keybindings['yaw_right'].upper()} or Numpad 6",
            f"Pitch Up: {keybindings['pitch_up'].upper()} or Numpad 8",
            f"Pitch Down: {keybindings['pitch_down'].upper()} or Numpad 2",
            f"Undo last action: Ctrl+Z or {keybindings.get('undo', 'z').upper()}",
            f"Color Picker: {keybindings.get('color_picker', 'c').upper()} (predefined colors)",
            f"Help: {keybindings['help'].upper()} or F1",
            rotate_help,
            f"Toggle Shapes Mode (enter/exit): {keybindings.get('shapes_mode', 'm').upper()}",
            f"Toggle Cleanup Mode (enter/exit): {keybindings.get('cleanup_mode', 'u').upper()}",
            "Edit selected vertex: click its line or red box,",
            "  then edit position [x, y, z] and color [r, g, b] or use C",
            "  Tab to switch fields, Enter to apply",
            "Press H or F1 again to close help",
        ]
        y = 20
        # Layout: move the last two items of the first column into the second column
        second_col_count = 17
        for text in help_texts[:-second_col_count]:
            surf = font.render(text, True, (255, 255, 255))
            self.overlay.blit(surf, (20, y))
            y += 30

        # Put the remaining items on a second column
        second_col_x = self.width // 2 + 20
        y2 = 20
        for text in help_texts[-second_col_count:]:
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

    def draw_cleanup_help_screen(self):
        font = pygame.font.Font(None, 24)
        texts = [
            "Cleanup Mode:",
            f"Toggle Cleanup Mode (enter/exit): {keybindings.get('cleanup_mode', 'u').upper()}",
            f"Clear All Vertices: {keybindings.get('clear_vertices', 'x').upper()}",
            f"Fix Inward-Facing Triangles (flip): {keybindings.get('remove_backfaces', 'f10').upper()} or F10",
            f"Check Edge (select 2 vertices): {keybindings.get('check_edge', 'f11').upper()} or F11",
            "  - Yellow = endpoints of matching triangle edge(s) in the vertex list",
            f"Remove Internal Triangles (centroid raycast): {keybindings.get('remove_internal_triangles', 'i').upper()}",
            f"Inspect Selected Triangle Internal?: {keybindings.get('inspect_internal_triangle', 'k').upper()}",
            f"Remove Internal Edges (raycast): {keybindings.get('remove_internal_edges', 'f12').upper()} or F12",
            f"Remove Triangles Covered by Others: {keybindings.get('remove_covered', 'f4').upper()} or F4",
            f"Show Triangles Using Selected Positions: {keybindings.get('show_position_matches', 'f2').upper()} or F2",
            f"Export .vertices.analyze: {keybindings.get('save_vertices', 'f5').upper()} or F5",
            f"Undo last action: Ctrl+Z or {keybindings.get('undo', 'z').upper()}",
            f"Help: {keybindings['help'].upper()} or F1 to close",
        ]
        y = 20
        for text in texts:
            surf = font.render(text, True, (255, 255, 255))
            self.overlay.blit(surf, (20, y))
            y += 30

    def draw_view_mode_screen(self):
        """Modal overlay for choosing render views and toggling wireframe."""
        try:
            # Dim background
            dim = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 160))
            self.overlay.blit(dim, (0, 0))

            panel_w = 520
            row_h = 30
            items = [
                ("view_normal", "View: Normal"),
                ("view_distance_fade", "View: Distance Fade (colors fade with distance)"),
                ("toggle_wireframe", f"Wireframe: {'ON' if getattr(self.game.renderer.renderer3D, 'wireframe', False) else 'OFF'}"),
            ]
            panel_h = 60 + len(items) * row_h + 50
            panel_x = (self.width - panel_w) // 2
            panel_y = (self.height - panel_h) // 2
            panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
            pygame.draw.rect(self.overlay, (30, 30, 30), panel)
            pygame.draw.rect(self.overlay, (200, 200, 200), panel, 2)

            title = "View Mode (Up/Down, Enter to apply, F8 toggles wireframe, Esc to close)"
            title_surf = self.font.render(title, True, (255, 255, 255))
            self.overlay.blit(title_surf, (panel_x + 10, panel_y + 10))

            self.game.view_mode_item_rects = []
            selected = int(getattr(self.game, 'view_mode_selected', 0))
            y = panel_y + 40
            for idx, (item_id, label) in enumerate(items):
                is_sel = (idx == selected)
                row = pygame.Rect(panel_x + 10, y, panel_w - 20, row_h - 2)
                pygame.draw.rect(self.overlay, (0, 100, 200) if is_sel else (60, 60, 60), row)
                pygame.draw.rect(self.overlay, (120, 120, 120), row, 1)

                # Mark active view
                prefix = ""
                try:
                    active_view = getattr(self.game, 'active_view', 'normal')
                    if item_id == "view_normal" and active_view == "normal":
                        prefix = "✓ "
                    if item_id == "view_distance_fade" and active_view == "distance_fade":
                        prefix = "✓ "
                except Exception:
                    pass

                text = self.font.render(prefix + label, True, (255, 255, 255))
                self.overlay.blit(text, (row.left + 8, row.top + 6))
                self.game.view_mode_item_rects.append((item_id, row))
                y += row_h

            hint = f"Press {keybindings.get('view_mode','v').upper()} to toggle View Mode"
            hint_surf = self.font.render(hint, True, (200, 200, 200))
            self.overlay.blit(hint_surf, (panel_x + 10, panel.bottom - 30))
        except Exception:
            self.game.view_mode_item_rects = []
    
    def draw_color_picker(self):
        """Draw the color picker modal overlay with predefined colors."""
        # Calculate layout: 4 columns, rows as needed
        colors_per_col = 4
        color_names = list(self.game.predefined_colors.keys())
        num_rows = (len(color_names) + colors_per_col - 1) // colors_per_col
        
        # Calculate panel size needed
        square_size = 40
        spacing = 10
        text_height = 25
        cols = colors_per_col
        panel_w = cols * square_size + (cols + 1) * spacing
        panel_h = num_rows * square_size + (num_rows + 1) * spacing + text_height + 20
        
        # Position panel in center
        panel_x = (self.width - panel_w) // 2
        panel_y = (self.height - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        
        # Dim background
        dim = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        self.overlay.blit(dim, (0, 0))
        
        # Draw panel
        pygame.draw.rect(self.overlay, (40, 40, 40), panel_rect)
        pygame.draw.rect(self.overlay, (200, 200, 200), panel_rect, 2)
        
        # Title
        title_surf = self.font.render("Select Color", True, (255, 255, 255))
        self.overlay.blit(title_surf, (panel_x + 10, panel_y + 8))
        
        # Reset color picker rects for click detection
        self.game.color_picker_rects = []
        
        # Draw color squares
        square_x = panel_x + spacing
        square_y = panel_y + text_height + 15
        
        for i, (color_name, rgb_values) in enumerate(self.game.predefined_colors.items()):
            row = i // colors_per_col
            col = i % colors_per_col
            
            square_rect = pygame.Rect(
                square_x + col * (square_size + spacing),
                square_y + row * (square_size + spacing),
                square_size,
                square_size
            )
            
            # Convert 0.0-1.0 RGB to 0-255 for pygame
            pygame_color = tuple(int(c * 255) for c in rgb_values)
            
            # Draw color square
            pygame.draw.rect(self.overlay, pygame_color, square_rect)
            pygame.draw.rect(self.overlay, (200, 200, 200), square_rect, 2)
            
            # Draw color name (use white or black text based on brightness)
            brightness = sum(pygame_color) // 3
            text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
            
            # Scale font down for color names
            small_font = pygame.font.Font(None, 16)
            name_surf = small_font.render(color_name, True, text_color)
            text_pt_x = square_rect.centerx - name_surf.get_width() // 2
            text_pt_y = square_rect.centery - name_surf.get_height() // 2
            self.overlay.blit(name_surf, (text_pt_x, text_pt_y))
            
            # Store rect and color name for click detection
            self.game.color_picker_rects.append((square_rect, color_name))

    def draw_disambiguation_panel(self):
        # Deprecated: replaced by colored triangle overlays
        return

    def _draw_internal_triangle_inspector_panel(self):
        """Right-side panel showing failing direction hit counts for the last inspected triangle."""
        try:
            lines = list(getattr(self.game, 'internal_triangle_debug_lines', []))
            tri = getattr(self.game, 'internal_triangle_debug_triangle', None)
            if not lines:
                return
            panel_w = 320
            row_h = 20
            max_rows = min(18, len(lines))
            panel_h = 34 + max_rows * row_h
            panel_x = self.width - panel_w - 10
            panel_y = 40
            panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
            pygame.draw.rect(self.overlay, (20, 20, 20, 220), panel)
            pygame.draw.rect(self.overlay, (255, 160, 0, 220), panel, 2)
            title = f"Tri {tri} internal check (failures)" if tri is not None else "Triangle internal check (failures)"
            title_surf = self.font.render(title, True, (255, 160, 0))
            self.overlay.blit(title_surf, (panel_x + 10, panel_y + 8))
            y = panel_y + 28
            for i in range(max_rows):
                surf = self.font.render(lines[i], True, (255, 255, 255))
                self.overlay.blit(surf, (panel_x + 10, y))
                y += row_h
        except Exception:
            pass

    def _draw_triangle_selection_panel(self):
        """Right-side panel listing currently selected triangles for quick active selection."""
        try:
            self.game.triangle_item_rects = []
            tris = sorted(list(getattr(self.game, 'selected_triangles', set())))
            if not tris:
                # Small status indicator only
                surf = self.font.render("Triangle Select: ON", True, (0, 255, 255))
                self.overlay.blit(surf, (self.width - surf.get_width() - 10, 10))
                return
            panel_w = 360
            row_h = 24
            max_rows = min(10, len(tris))
            panel_h = 34 + max_rows * (row_h + 4)
            panel_x = self.width - panel_w - 10
            panel_y = 40
            panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
            pygame.draw.rect(self.overlay, (20, 20, 20, 200), panel)
            pygame.draw.rect(self.overlay, (0, 200, 255, 220), panel, 2)
            title = self.font.render("Selected Triangles (click to activate)", True, (0, 255, 255))
            self.overlay.blit(title, (panel_x + 10, panel_y + 8))
            rows = verticesHolder.vertices.reshape(-1, 6)
            active = getattr(self.game, 'last_selected_triangle_index', None)
            y = panel_y + 30
            for idx, t in enumerate(tris[:max_rows]):
                i0 = int(t) * 3
                verts = (i0, i0 + 1, i0 + 2)
                label = f"Tri {t}: v{verts[0]}, v{verts[1]}, v{verts[2]}"
                selected = (active is not None and int(active) == int(t))
                row_rect = pygame.Rect(panel_x + 6, y, panel_w - 12, row_h)
                pygame.draw.rect(self.overlay, (0, 120, 160) if selected else (45, 45, 45), row_rect)
                pygame.draw.rect(self.overlay, (90, 90, 90), row_rect, 1)
                txt = self.font.render(label, True, (255, 255, 255))
                self.overlay.blit(txt, (row_rect.left + 6, row_rect.top + 4))
                self.game.triangle_item_rects.append((int(t), row_rect))
                y += row_h + 4
            hint = "Ctrl+click to multi-select"
            hint_surf = self.font.render(hint, True, (180, 180, 180))
            self.overlay.blit(hint_surf, (panel_x + 10, panel.bottom - 22))
        except Exception:
            self.game.triangle_item_rects = []

    def _draw_disambiguation_triangle_panel(self):
        """Clickable list of triangle candidates while disambiguating triangles."""
        try:
            self.game.disambiguation_item_rects = []
            candidates = list(getattr(self.game, 'disambiguation_candidates', []))
            if not candidates:
                return
            panel_w = 360
            row_h = 24
            max_rows = min(9, len(candidates))
            panel_h = 40 + max_rows * (row_h + 4)
            panel_x = self.width - panel_w - 10
            panel_y = 40
            panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
            pygame.draw.rect(self.overlay, (20, 20, 20, 220), panel)
            pygame.draw.rect(self.overlay, (255, 255, 255, 220), panel, 2)
            title = self.font.render("Choose Triangle (click row / 1-9 / Enter)", True, (255, 255, 255))
            self.overlay.blit(title, (panel_x + 10, panel_y + 10))
            selected_idx = int(getattr(self.game, 'disambiguation_selected', 0))
            y = panel_y + 34
            for i, t in enumerate(candidates[:max_rows]):
                row_rect = pygame.Rect(panel_x + 6, y, panel_w - 12, row_h)
                is_sel = (i == selected_idx)
                pygame.draw.rect(self.overlay, (80, 80, 120) if is_sel else (45, 45, 45), row_rect)
                pygame.draw.rect(self.overlay, (110, 110, 110), row_rect, 1)
                i0 = int(t) * 3
                label = f"{i+1}. Tri {t}: v{i0}, v{i0+1}, v{i0+2}"
                txt = self.font.render(label, True, (255, 255, 255))
                self.overlay.blit(txt, (row_rect.left + 6, row_rect.top + 4))
                self.game.disambiguation_item_rects.append((int(t), row_rect))
                y += row_h + 4
        except Exception:
            self.game.disambiguation_item_rects = []