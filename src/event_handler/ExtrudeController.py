import ast
import numpy as np

from src.geometry.VerticesHolder import verticesHolder


class ExtrudeController:
    """Extrude tool extracted from EventHandler.apply_extrude()."""

    def __init__(self, game, triangle_filler, remove_internal_edges_callable=None):
        self.game = game
        self.triangle_filler = triangle_filler
        self.remove_internal_edges_callable = remove_internal_edges_callable

    def get_extrude_base_index_and_point(self):
        try:
            vertices = verticesHolder.vertices.reshape(-1, 6)
            if len(vertices) == 0:
                return None, None
            last_idx = None
            if self.game.last_selected_vertex_index is not None:
                last_idx = self.game.last_selected_vertex_index
            elif len(self.game.selected_vertices) > 0:
                last_idx = max(self.game.selected_vertices)
            if last_idx is None or last_idx < 0 or last_idx >= len(vertices):
                return None, None
            P = vertices[last_idx, :3].astype(float)
            return last_idx, P
        except Exception:
            return None, None

    def apply_extrude(self):
        text = (self.game.extrude_text or "").strip()
        if text.count('[') > 1:
            last_open = text.rfind('[')
            last_close = text.rfind(']')
            if last_close != -1 and last_close > last_open:
                text = text[last_open:last_close + 1]
            else:
                text = text[last_open:]
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            self.game.extrude_error = "Invalid format. Use [x, y, z] with numbers."
            return
        if not (isinstance(parsed, (list, tuple)) and len(parsed) == 3):
            self.game.extrude_error = "Enter exactly three numbers like [1.0, 2.0, 3.0]."
            return
        try:
            px, py, pz = (float(parsed[0]), float(parsed[1]), float(parsed[2]))
        except (TypeError, ValueError):
            self.game.extrude_error = "Coordinates must be numbers."
            return

        if len(self.game.selected_vertices) == 0:
            self.game.extrude_mode = False
            self.game.extrude_text = ""
            self.game.extrude_error = ""
            return

        last_idx, P = self.get_extrude_base_index_and_point()
        vertices = verticesHolder.vertices.reshape(-1, 6)
        if last_idx is None or P is None or last_idx < 0 or last_idx >= len(vertices):
            self.game.extrude_error = "Invalid last selected vertex."
            return

        try:
            self.game.extrude_base_index = last_idx
            self.game.extrude_base_point = [float(P[0]), float(P[1]), float(P[2])]
        except Exception:
            pass

        Pprime = np.array([px, py, pz], dtype=float)
        offset = Pprime - P

        selected = sorted(list(self.game.selected_vertices))
        if not selected:
            self.game.extrude_error = "No vertices selected."
            return

        self.game.push_undo_snapshot("Extrude selection")

        # Copy selected to the end with translation; keep original colors for copies
        new_rows = []
        for i in selected:
            pos = vertices[i, :3].astype(float) + offset
            color = vertices[i, 3:6].astype(float)
            new_rows.append(np.concatenate([pos, color]))
        new_rows = np.array(new_rows, dtype=np.float32)

        if new_rows.size:
            verticesHolder.vertices = np.append(verticesHolder.vertices, new_rows.flatten()).astype('f4')

        rows = verticesHolder.vertices.reshape(-1, 6)
        total_before = len(rows) - len(new_rows)
        index_map = {old_idx: total_before + k for k, old_idx in enumerate(selected)}

        used_fallback_for_sides = False
        saved_selection = set(self.game.selected_vertices)
        try:
            new_indices = [index_map[i] for i in selected if i in index_map]
            if len(new_indices) >= 3:
                self.game.selected_vertices = set(new_indices)
                self.triangle_filler.form_triangles_from_selected()

            if len(selected) >= 3:
                sel_positions = np.array([rows[i, :3].astype(float) for i in selected], dtype=np.float64)
                centroid = sel_positions.mean(axis=0)
                centered = sel_positions - centroid
                if np.linalg.norm(centered) > 0:
                    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
                    u_axis = Vt[0]
                    v_axis = Vt[1] if Vt.shape[0] > 1 else np.array([0.0, 1.0, 0.0])
                    proj_u = centered.dot(u_axis)
                    proj_v = centered.dot(v_axis)
                    pts2 = np.stack([proj_u, proj_v], axis=1)
                    sorted_idx = sorted(range(len(pts2)), key=lambda i: (pts2[i][0], pts2[i][1]))

                    def cross(o, a, b):
                        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

                    lower = []
                    for i in sorted_idx:
                        while len(lower) >= 2 and cross(pts2[lower[-2]], pts2[lower[-1]], pts2[i]) <= 0:
                            lower.pop()
                        lower.append(i)
                    upper = []
                    for i in reversed(sorted_idx):
                        while len(upper) >= 2 and cross(pts2[upper[-2]], pts2[upper[-1]], pts2[i]) <= 0:
                            upper.pop()
                        upper.append(i)
                    hull_idx = lower[:-1] + upper[:-1]
                    if len(hull_idx) < 3:
                        angles = np.arctan2(pts2[:, 1], pts2[:, 0])
                        hull_idx = list(np.argsort(angles))
                    ordered = [selected[int(k)] for k in hull_idx]

                    for i in range(len(ordered)):
                        a = ordered[i]
                        b = ordered[(i + 1) % len(ordered)]
                        a2 = index_map.get(a)
                        b2 = index_map.get(b)
                        if a2 is None or b2 is None:
                            continue
                        self.game.selected_vertices = {a, b, a2, b2}
                        self.triangle_filler.form_triangles_from_selected()
                    used_fallback_for_sides = True
        finally:
            self.game.selected_vertices = saved_selection

        if (not used_fallback_for_sides) and getattr(self.game, 'cleanup_mode', False):
            try:
                if callable(self.remove_internal_edges_callable):
                    self.remove_internal_edges_callable()
            except Exception:
                pass

        # Remove the raw extruded copy rows (they were only used as positional sources for triangulation)
        try:
            rows_all = verticesHolder.vertices.reshape(-1, 6)
            new_copy_indices = [index_map[i] for i in selected if i in index_map]
            if new_copy_indices:
                keep_mask = np.ones(len(rows_all), dtype=bool)
                keep_mask[new_copy_indices] = False
                rows_kept = rows_all[keep_mask]
                verticesHolder.vertices = rows_kept.astype('f4').flatten()
        except Exception:
            pass

        self.game.renderer.renderer3D.update_vertex_buffer()
        self.game.extrude_mode = False
        self.game.extrude_text = ""
        self.game.extrude_error = ""
        try:
            if hasattr(self.game, 'extrude_base_index'):
                delattr(self.game, 'extrude_base_index')
            if hasattr(self.game, 'extrude_base_point'):
                delattr(self.game, 'extrude_base_point')
            self.game.yellow_highlights.clear()
        except Exception:
            pass


