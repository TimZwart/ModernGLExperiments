import pygame
import numpy as np
from src.geometry.VerticesHolder import verticesHolder


class SelectionController:
    """
    Handles selection-related helpers:
    - nearest vertex picking (with ambiguity detection)
    - disambiguation modal setup/teardown
    - simple 2D triangle hit testing helpers
    - vertex list click + scroll

    Extracted from EventHandler for organization.
    """

    def __init__(self, game, vertex_editor=None):
        self.game = game
        # Optional dependency used to prefill edit UI on single-selection.
        self.vertex_editor = vertex_editor

    def find_nearest_vertex(self, x, y):
        if verticesHolder.vertices.size == 0:
            return None
        vertices = verticesHolder.vertices.reshape(-1, 6)
        screen_coords = self.game.renderer.renderer3D.world_to_screen(vertices[:, :3])

        # Calculate distances for all vertices
        distances = np.sqrt(np.sum((screen_coords - np.array([x, y])) ** 2, axis=1))

        # Find the index of the nearest vertex
        nearest_index = int(np.argmin(distances))
        nearest_distance = float(distances[nearest_index])

        # Set a maximum distance threshold (e.g., 500 pixels)
        max_distance = 500
        if nearest_distance > max_distance:
            return None
        return nearest_index

    def find_nearest_vertex_with_ambiguity(self, x, y):
        if verticesHolder.vertices.size == 0:
            return None, []
        vertices = verticesHolder.vertices.reshape(-1, 6)
        screen_coords = self.game.renderer.renderer3D.world_to_screen(vertices[:, :3])
        distances = np.sqrt(np.sum((screen_coords - np.array([x, y])) ** 2, axis=1))
        nearest_index = int(np.argmin(distances))
        nearest_distance = float(distances[nearest_index])
        max_distance = 500
        if nearest_distance > max_distance:
            return None, []
        # Determine ambiguous: all vertices whose world positions equal the nearest one (within tolerance)
        tol = 1e-6
        target_pos = vertices[nearest_index, :3]
        diffs = np.abs(vertices[:, :3] - target_pos)
        same_mask = (diffs[:, 0] <= tol) & (diffs[:, 1] <= tol) & (diffs[:, 2] <= tol)
        candidates = np.where(same_mask)[0].tolist()
        # Sort candidates by distance so the top is the closest in screen-space
        candidates.sort(key=lambda i: distances[i])
        if len(candidates) > 1:
            return nearest_index, candidates
        return nearest_index, []

    def _pt_sub(self, a, b):
        return (a[0] - b[0], a[1] - b[1])

    def _cross(self, a, b):
        return a[0] * b[1] - a[1] * b[0]

    def _same_side(self, p1, p2, a, b):
        ab = self._pt_sub(b, a)
        cp1 = self._cross(ab, self._pt_sub(p1, a))
        cp2 = self._cross(ab, self._pt_sub(p2, a))
        return cp1 * cp2 >= 0

    def point_in_triangle(self, p, a, b, c):
        # Barycentric/edge method in screen space
        return self._same_side(p, a, b, c) and self._same_side(p, b, a, c) and self._same_side(p, c, a, b)

    def barycentric_weights(self, p, a, b, c):
        # Compute barycentric weights for point p in triangle (a,b,c) in 2D
        denom = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denom) < 1e-12:
            return 1.0, 0.0, 0.0
        w0 = ((b[1] - c[1]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[1])) / denom
        w1 = ((c[1] - a[1]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[1])) / denom
        w2 = 1.0 - w0 - w1
        return w0, w1, w2

    def start_disambiguation(self, candidates: list, ctrl_pressed: bool):
        try:
            self.game.disambiguation_mode = True
            self.game.disambiguation_candidates = list(candidates)
            self.game.disambiguation_selected = 0
            self.game.disambiguation_item_rects = []
            self.game.disambiguation_ctrl_pressed = bool(ctrl_pressed)
            # Snapshot prior selection and intended action
            self.game.disambiguation_prev_selection = set(self.game.selected_vertices)
            self.game.disambiguation_action = 'toggle' if ctrl_pressed else 'replace'
            # Prepare colored overlays for triangles that include any candidate vertex
            rows = verticesHolder.vertices.reshape(-1, 6)
            tri_count = len(rows) // 3
            candidate_set = set(candidates)
            colors = [
                (0, 0, 255, 110),   # blue
                (255, 0, 0, 110),   # red
                (0, 255, 0, 110),   # green
                (255, 255, 0, 110), # yellow
                (255, 0, 255, 110), # magenta
                (0, 255, 255, 110), # cyan
                (255, 128, 0, 110), # orange
                (128, 0, 255, 110), # purple
                (128, 128, 128, 110), # gray
            ]
            overlays = []
            color_index = 0
            time = pygame.time.get_ticks() * 0.001
            mvp = self.game.renderer.renderer3D.get_mvp_matrix(time)
            for t in range(tri_count):
                i0 = t * 3
                tri_indices = [i0 + 0, i0 + 1, i0 + 2]
                if any(idx in candidate_set for idx in tri_indices):
                    pos = rows[tri_indices, :3]
                    pts = self.game.renderer.renderer3D.world_to_screen(pos)
                    ones = np.ones((pos.shape[0], 1), dtype=float)
                    homo = np.concatenate([pos, ones], axis=1)
                    clip = homo.dot(np.array(mvp))
                    with np.errstate(divide='ignore', invalid='ignore'):
                        ndc = clip[:, :3] / clip[:, 3:4]
                    ndc_z = ndc[:, 2].astype(float)
                    if np.isnan(pts).any() or np.isnan(ndc_z).any():
                        continue
                    color = colors[color_index % len(colors)]
                    color_index += 1
                    overlays.append({
                        'candidate': next((idx for idx in tri_indices if idx in candidate_set), tri_indices[0]),
                        'triangle_index': t,
                        'screen_pts': [(float(pts[0][0]), float(pts[0][1])), (float(pts[1][0]), float(pts[1][1])), (float(pts[2][0]), float(pts[2][1]))],
                        'ndc_z': [float(ndc_z[0]), float(ndc_z[1]), float(ndc_z[2])],
                        'color': color,
                    })
            self.game.disambiguation_triangles = overlays
            highlight_indices = set()
            for ov in overlays:
                ti = int(ov['triangle_index'])
                j0 = ti * 3
                highlight_indices.update([j0, j0 + 1, j0 + 2])
            self.game.yellow_highlights = highlight_indices
            self.game.set_status("Click a highlighted triangle to choose the vertex", 240)
        except Exception:
            if candidates:
                self.end_disambiguation(candidates[0])

    def end_disambiguation(self, chosen_index):
        try:
            self.game.disambiguation_mode = False
            self.game.disambiguation_item_rects = []
            self.game.disambiguation_ctrl_pressed = False
            self.game.disambiguation_triangles = []
            prior = getattr(self.game, 'disambiguation_prev_selection', set())
            action = getattr(self.game, 'disambiguation_action', None)
            self.game.yellow_highlights = set()
            if chosen_index is None:
                self.game.set_status("Selection cancelled", 120)
                return
            self.game.selected_vertices = set(prior)
            if action == 'toggle':
                if chosen_index in self.game.selected_vertices:
                    self.game.selected_vertices.remove(chosen_index)
                else:
                    self.game.selected_vertices.add(chosen_index)
            else:
                self.game.selected_vertices = {chosen_index}
            self.game.last_selected_vertex_index = chosen_index
            if len(self.game.selected_vertices) == 1:
                self.game.edit_mode = True
                if self.vertex_editor is not None:
                    self.vertex_editor.prefill_edit_fields(chosen_index)
        except Exception:
            pass

    def handle_vertex_list_click(self, x, y, ctrl_pressed):
        # Keep behavior identical by calling back into the game's overlay rect computation
        try:
            total_vertices = len(verticesHolder.vertices) // 6
            start_index = self.game.uiOverlayCreator.scroll_offset
            end_index = min(start_index + self.game.uiOverlayCreator.max_visible_vertices, total_vertices)
            y_position = 10
            for index in range(start_index, end_index):
                rect = self.game.uiOverlayCreator.get_vertex_rect(index, y_position)
                if rect.collidepoint(x, y):
                    # Toggle selection for this row
                    actual_index = index
                    if ctrl_pressed:
                        if actual_index in self.game.selected_vertices:
                            self.game.selected_vertices.remove(actual_index)
                        else:
                            self.game.selected_vertices.add(actual_index)
                    else:
                        self.game.selected_vertices = {actual_index}
                    self.game.last_selected_vertex_index = actual_index
                    if len(self.game.selected_vertices) == 1 and self.vertex_editor is not None:
                        self.game.edit_mode = True
                        self.vertex_editor.prefill_edit_fields(actual_index)
                    else:
                        self.game.edit_mode = False
                        self.game.edit_text = ""
                        self.game.edit_pos_text = ""
                        self.game.edit_color_text = ""
                    return True
                y_position += 30
        except Exception:
            pass
        return False

    def handle_scroll(self, y):
        total_vertices = len(verticesHolder.vertices) // 6
        if y > 0:  # Scroll up
            self.game.uiOverlayCreator.scroll_offset = max(0, self.game.uiOverlayCreator.scroll_offset - self.game.scroll_speed)
        else:  # Scroll down
            max_offset = max(0, total_vertices - self.game.uiOverlayCreator.max_visible_vertices)
            self.game.uiOverlayCreator.scroll_offset = min(max_offset, self.game.uiOverlayCreator.scroll_offset + self.game.scroll_speed)


