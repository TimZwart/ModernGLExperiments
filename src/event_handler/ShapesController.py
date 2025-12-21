import ast
import itertools
import numpy as np

from src.geometry.VerticesHolder import verticesHolder


class ShapesController:
    """
    Shapes Mode / input flow extracted from EventHandler.
    Keeps the same behavior by writing into game.shape_* fields and appending vertices to verticesHolder.
    """

    def __init__(self, game, clear_rotation_state=None):
        self.game = game
        # Optional callback to clear rotation states in the outer event system (mouse drag / rotate key).
        self.clear_rotation_state = clear_rotation_state

    def _clear_rotation(self):
        try:
            if callable(self.clear_rotation_state):
                self.clear_rotation_state()
        except Exception:
            pass

    def get_default_shape_point_text(self):
        # If there are no vertices, default to origin
        try:
            total = len(verticesHolder.vertices) // 6
            if total == 0:
                return "[0.0, 0.0, 0.0]"
            # Prefer last selected vertex if available
            idx = getattr(self.game, 'last_selected_vertex_index', None)
            if idx is not None and 0 <= idx < total:
                coords = verticesHolder.vertices[idx * 6:idx * 6 + 3]
                if len(coords) == 3:
                    x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                    return f"[{x}, {y}, {z}]"
            # Otherwise use the last vertex in the list
            coords = verticesHolder.vertices[(total - 1) * 6:(total - 1) * 6 + 3]
            if len(coords) == 3:
                x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                return f"[{x}, {y}, {z}]"
        except Exception:
            pass
        return "[0.0, 0.0, 0.0]"

    def toggle_shapes_mode(self, mouse_button_rotation_held_ref=None, rotate_key_held_ref=None):
        # Exit any existing shape input flow when toggling
        self.game.shapes_mode = not self.game.shapes_mode
        if not self.game.shapes_mode:
            self.cancel_shape_flow(clear_error=True)
            self.game.set_status("Shapes Mode OFF", 120)
        else:
            self.cancel_shape_flow(clear_error=True)
            self._clear_rotation()
            self.game.set_status("Shapes Mode ON", 120)

    def cancel_shape_flow(self, clear_error: bool = False):
        self.game.shape_input_mode = None
        self.game.shape_step = None
        self.game.shape_primary_text = ""
        self.game.shape_secondary_text = ""
        # Clear any temporary state for shapes (stored on this controller)
        for attr in (
            "_shape_tmp_point", "_shape_tmp_width", "_shape_tmp_length", "_shape_tmp_sides",
            "_shape_tmp_dim", "_shape_tmp_direction_point", "_shape_two_vertices_mode",
            "_shape_edge_p0", "_shape_edge_p1", "_shape_base_index",
        ):
            if hasattr(self, attr):
                try:
                    delattr(self, attr)
                except Exception:
                    pass
        try:
            self.game.yellow_highlights.clear()
        except Exception:
            pass
        if clear_error:
            self.game.shape_error = ""

    def start_rectangle_flow(self):
        self.game.shape_input_mode = 'rectangle'
        self.game.shape_primary_text = ""
        self.game.shape_secondary_text = ""
        self._clear_rotation()
        vertices = verticesHolder.vertices.reshape(-1, 6)
        if len(self.game.selected_vertices) == 2 and len(vertices) > 0:
            i_a, i_b = sorted(list(self.game.selected_vertices))
            if 0 <= i_a < len(vertices) and 0 <= i_b < len(vertices):
                p0 = vertices[i_a, :3].astype(float)
                p1 = vertices[i_b, :3].astype(float)
                self._shape_edge_p0 = p0
                self._shape_edge_p1 = p1
                self._shape_two_vertices_mode = True
                self.game.shape_step = 'dimension'
                self._shape_base_index = i_a
                self.game.yellow_highlights = {i_a}
                bx, by, bz = float(p0[0]), float(p0[1]), float(p0[2])
                self.game.shape_error = f"Enter other dimension (number). Base: [{bx:.3f}, {by:.3f}, {bz:.3f}]"
                return
        self._shape_two_vertices_mode = False
        self.game.shape_step = 'point'
        self.game.shape_primary_text = self.get_default_shape_point_text()
        self.game.shape_error = "Enter start point [x, y, z]"

    def start_ngon_flow(self):
        self.game.shape_input_mode = 'ngon'
        self.game.shape_step = 'point'
        self.game.shape_primary_text = ""
        self.game.shape_secondary_text = ""
        self._clear_rotation()
        self.game.shape_primary_text = self.get_default_shape_point_text()
        self.game.shape_error = "Enter center/start point [x, y, z]"

    def backspace_shape_text(self):
        if self.game.shape_step in ('point', 'width', 'sides', 'dimension', 'direction'):
            self.game.shape_primary_text = self.game.shape_primary_text[:-1]
        elif self.game.shape_step == 'length':
            self.game.shape_secondary_text = self.game.shape_secondary_text[:-1]
        self.game.shape_error = ""

    def append_shape_text(self, ch: str):
        if not ch:
            return
        if self.game.shape_step in ('point', 'width', 'sides', 'dimension', 'direction'):
            self.game.shape_primary_text += ch
        elif self.game.shape_step == 'length':
            self.game.shape_secondary_text += ch
        self.game.shape_error = ""

    def apply_shape_step(self):
        mode = self.game.shape_input_mode
        step = self.game.shape_step
        if mode is None or step is None:
            return
        try:
            if step == 'point':
                point = ast.literal_eval((self.game.shape_primary_text or '').strip())
                if not (isinstance(point, (list, tuple)) and len(point) == 3):
                    raise ValueError("Enter [x, y, z]")
                px, py, pz = float(point[0]), float(point[1]), float(point[2])
                self._shape_tmp_point = (px, py, pz)
                if mode == 'rectangle':
                    self.game.shape_step = 'width'
                    self.game.shape_primary_text = ""
                    self.game.shape_error = "Enter width (number)"
                elif mode == 'ngon':
                    self.game.shape_step = 'sides'
                    self.game.shape_primary_text = ""
                    self.game.shape_error = "Enter number of sides (>=3)"
                return
            if mode == 'rectangle':
                if getattr(self, '_shape_two_vertices_mode', False):
                    if step == 'dimension':
                        dim = self.parse_number(self.game.shape_primary_text)
                        if not np.isfinite(dim) or dim <= 0:
                            raise ValueError("Dimension must be > 0")
                        self._shape_tmp_dim = dim
                        self.game.shape_step = 'direction'
                        self.game.shape_primary_text = ""
                        try:
                            bx, by, bz = float(self._shape_edge_p0[0]), float(self._shape_edge_p0[1]), float(self._shape_edge_p0[2])
                            self.game.shape_error = f"Enter direction point [x, y, z]. Base: [{bx:.3f}, {by:.3f}, {bz:.3f}]"
                            if hasattr(self, '_shape_base_index'):
                                self.game.yellow_highlights = {getattr(self, '_shape_base_index', None)}
                        except Exception:
                            self.game.shape_error = "Enter direction point [x, y, z]"
                        return
                    if step == 'direction':
                        point = ast.literal_eval((self.game.shape_primary_text or '').strip())
                        if not (isinstance(point, (list, tuple)) and len(point) == 3):
                            raise ValueError("Enter [x, y, z]")
                        pdx, pdy, pdz = float(point[0]), float(point[1]), float(point[2])
                        self._shape_tmp_direction_point = np.array([pdx, pdy, pdz], dtype=float)
                        self.commit_rectangle_from_two_vertices()
                        return
                if step == 'width':
                    width = self.parse_number(self.game.shape_primary_text)
                    if not np.isfinite(width) or width <= 0:
                        raise ValueError("Width must be > 0")
                    self._shape_tmp_width = width
                    self.game.shape_step = 'length'
                    self.game.shape_secondary_text = ""
                    self.game.shape_error = "Enter length (number)"
                    return
                if step == 'length':
                    length = self.parse_number(self.game.shape_secondary_text)
                    if not np.isfinite(length) or length <= 0:
                        raise ValueError("Length must be > 0")
                    self._shape_tmp_length = length
                    self.commit_rectangle()
                    return
            if mode == 'ngon':
                if step == 'sides':
                    sides_val = int(ast.literal_eval((self.game.shape_primary_text or '0').strip()))
                    if sides_val < 3:
                        raise ValueError("Sides must be >= 3")
                    self._shape_tmp_sides = sides_val
                    self.commit_ngon()
                    return
        except Exception as e:
            self.game.shape_error = f"{e}"

    def append_vertex_with_color(self, pos_tuple, color_rgb):
        x, y, z = float(pos_tuple[0]), float(pos_tuple[1]), float(pos_tuple[2])
        new_vertex = [x, y, z] + list(color_rgb)
        verticesHolder.vertices = np.append(verticesHolder.vertices, new_vertex).astype('f4')

    def parse_number(self, text_value: str) -> float:
        s = (text_value or '').strip()
        try:
            val = ast.literal_eval(s)
            if isinstance(val, (int, float)):
                return float(val)
        except Exception:
            pass
        try:
            return float(s)
        except Exception:
            raise ValueError("Enter a numeric value (e.g., 10 or 10.5)")

    def drop_trailing_incomplete_vertices(self) -> int:
        try:
            rows_count = len(verticesHolder.vertices) // 6
            remainder = rows_count % 3
            if remainder == 0:
                return 0
            if rows_count - remainder <= 0:
                verticesHolder.vertices = np.array([], dtype='f4')
                return rows_count
            keep_rows = rows_count - remainder
            verticesHolder.vertices = verticesHolder.vertices[:keep_rows * 6].astype('f4')
            return remainder
        except Exception:
            return 0

    def commit_rectangle(self):
        self.game.push_undo_snapshot("Add rectangle")
        self.drop_trailing_incomplete_vertices()
        px, py, pz = self._shape_tmp_point
        width = float(self._shape_tmp_width)
        length = float(self._shape_tmp_length)
        p0 = (px, py, pz)
        p1 = (px + width, py, pz)
        p2 = (px + width, py + length, pz)
        p3 = (px, py + length, pz)
        color = self.game.random_color()
        for tri in [(p0, p1, p2), (p0, p2, p3)]:
            for pos in tri:
                self.append_vertex_with_color(pos, color)
        self.game.renderer.renderer3D.update_vertex_buffer()
        self.game.set_status("Rectangle added", 180)
        self._clear_rotation()
        self.cancel_shape_flow(clear_error=True)

    def commit_ngon(self):
        try:
            n = int(self._shape_tmp_sides)
        except Exception:
            n = None
        self.game.push_undo_snapshot(f"Add {n}-gon" if n is not None else "Add n-gon")
        self.drop_trailing_incomplete_vertices()
        px, py, pz = self._shape_tmp_point
        n = int(self._shape_tmp_sides)
        radius = 1.0
        verts = []
        for k in range(n):
            angle = 2.0 * np.pi * (k / n)
            x = px + radius * np.cos(angle)
            y = py + radius * np.sin(angle)
            z = pz
            verts.append((x, y, z))
        color = self.game.random_color()
        center = (px, py, pz)
        for k in range(n):
            a = verts[k]
            b = verts[(k + 1) % n]
            for pos in (center, a, b):
                self.append_vertex_with_color(pos, color)
        self.game.renderer.renderer3D.update_vertex_buffer()
        self.game.set_status(f"{n}-gon added", 180)
        self._clear_rotation()
        self.cancel_shape_flow(clear_error=True)

    def commit_rectangle_from_two_vertices(self):
        # Snapshot before mutating geometry
        self.game.push_undo_snapshot("Add rectangle (2-vertex)")
        self.drop_trailing_incomplete_vertices()

        p0 = np.array(self._shape_edge_p0, dtype=float)
        p1 = np.array(self._shape_edge_p1, dtype=float)
        dim = float(self._shape_tmp_dim)
        dir_pt = np.array(self._shape_tmp_direction_point, dtype=float)

        edge = p1 - p0
        edge_len = float(np.linalg.norm(edge))
        if edge_len <= 1e-12:
            self.game.shape_error = "Selected vertices must not be the same point"
            return
        edge_dir = edge / edge_len

        v = dir_pt - p0
        v_perp = v - np.dot(v, edge_dir) * edge_dir
        v_len = float(np.linalg.norm(v_perp))
        if v_len <= 1e-12:
            self.game.shape_error = "Direction point must not lie on the base edge"
            return
        perp_dir = v_perp / v_len

        p2 = p1 + perp_dir * dim
        p3 = p0 + perp_dir * dim

        # Create/ensure vertices for corners, then fill quad
        color = self.game.random_color()
        for pos in (tuple(p0), tuple(p1), tuple(p2), tuple(p3)):
            self.append_vertex_with_color(pos, color)

        # Fill triangles among the last 4 appended vertices
        total = len(verticesHolder.vertices) // 6
        indices = list(range(total - 4, total))
        self.fill_among_indices(indices)

        self.game.renderer.renderer3D.update_vertex_buffer()
        self.game.set_status("Rectangle added", 180)
        self._clear_rotation()
        self.cancel_shape_flow(clear_error=True)

    def fill_among_indices(self, indices):
        if len(indices) < 3:
            return
        vertices = verticesHolder.vertices.reshape(-1, 6)
        # Existing triangles as sets of positions
        existing_triangles = []
        num_tri = len(vertices) // 3
        for t in range(num_tri):
            tri_pos = set(tuple(vertices[t * 3 + i, :3]) for i in range(3))
            existing_triangles.append(tri_pos)

        def round_triplet(p):
            return (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))

        unique_by_pos = {}
        for i in sorted(indices):
            key = round_triplet(vertices[i, :3])
            if key not in unique_by_pos:
                unique_by_pos[key] = i
        indices = sorted(unique_by_pos.values())

        new_triangles = []
        for comb in itertools.combinations(sorted(indices), 3):
            pos = [tuple(vertices[i, :3]) for i in comb]
            if len(set(pos)) < 3:
                continue
            p0 = np.array(pos[0], dtype=float)
            p1 = np.array(pos[1], dtype=float)
            p2 = np.array(pos[2], dtype=float)
            if np.linalg.norm(np.cross(p1 - p0, p2 - p0)) < 1e-8:
                continue
            pos_set = set(pos)
            if pos_set not in existing_triangles:
                new_triangles.append(pos)

        if not new_triangles:
            return
        new_data = []
        for tri_pos in new_triangles:
            new_color = self.game.random_color()
            for pos in tri_pos:
                new_data.extend(pos)
                new_data.extend(new_color)
        if new_data:
            verticesHolder.vertices = np.append(verticesHolder.vertices, new_data).astype('f4')


