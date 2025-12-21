import ast
import numpy as np
from src.geometry.VerticesHolder import verticesHolder


class VertexEditController:
    """Add/edit/delete/clear vertex operations and related UI text helpers."""

    def __init__(self, game):
        self.game = game

    def get_add_vertex_default_text(self):
        try:
            idx = getattr(self.game, 'last_selected_vertex_index', None)
            if idx is not None:
                coords = verticesHolder.vertices[idx * 6:idx * 6 + 3]
                if len(coords) == 3:
                    x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                    return f"[{x}, {y}, {z}]"
            if len(self.game.selected_vertices) == 1:
                selected = next(iter(self.game.selected_vertices))
                coords = verticesHolder.vertices[selected * 6:selected * 6 + 3]
                if len(coords) == 3:
                    x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                    return f"[{x}, {y}, {z}]"
        except Exception:
            pass
        return "[0.0, 0.0, 0.0]"

    def fmt_triplet(self, values) -> str:
        try:
            x, y, z = float(values[0]), float(values[1]), float(values[2])
            return f"[{x:.3f}, {y:.3f}, {z:.3f}]"
        except Exception:
            try:
                return f"[{values[0]}, {values[1]}, {values[2]}]"
            except Exception:
                return "[0.000, 0.000, 0.000]"

    def get_add_vertex_default_texts(self):
        # Position
        try:
            idx = getattr(self.game, 'last_selected_vertex_index', None)
            if idx is not None:
                rows = verticesHolder.vertices.reshape(-1, 6)
                if 0 <= idx < len(rows):
                    pos = rows[idx, :3].astype(float)
                    pos_str = self.fmt_triplet(pos)
                else:
                    pos_str = "[0.000, 0.000, 0.000]"
            elif len(self.game.selected_vertices) == 1:
                selected = next(iter(self.game.selected_vertices))
                rows = verticesHolder.vertices.reshape(-1, 6)
                if 0 <= selected < len(rows):
                    pos = rows[selected, :3].astype(float)
                    pos_str = self.fmt_triplet(pos)
                else:
                    pos_str = "[0.000, 0.000, 0.000]"
            else:
                pos_str = "[0.000, 0.000, 0.000]"
        except Exception:
            pos_str = "[0.000, 0.000, 0.000]"
        # Color from current_color
        try:
            col = getattr(self.game, 'current_color', [0.0, 0.0, 0.0])
            col_str = self.fmt_triplet(col)
        except Exception:
            col_str = "[1.000, 1.000, 1.000]"
        return pos_str, col_str

    def prefill_edit_fields(self, selected_index: int):
        try:
            rows = verticesHolder.vertices.reshape(-1, 6)
            if 0 <= selected_index < len(rows):
                pos = rows[selected_index, :3].astype(float)
                col = rows[selected_index, 3:6].astype(float)
                self.game.edit_pos_text = self.fmt_triplet(pos)
                self.game.edit_color_text = self.fmt_triplet(col)
                self.game.edit_text = f"{self.game.edit_pos_text} {self.game.edit_color_text}"
                self.game.edit_focus = 'pos'
            else:
                self.game.edit_pos_text = "[0.000, 0.000, 0.000]"
                self.game.edit_color_text = self.fmt_triplet(self.game.current_color)
        except Exception:
            self.game.edit_pos_text = "[0.000, 0.000, 0.000]"
            self.game.edit_color_text = self.fmt_triplet(self.game.current_color)

    def apply_edit(self):
        selected_count = len(self.game.selected_vertices)
        if selected_count == 0:
            self.game.edit_mode = False
            return
        try:
            rows = verticesHolder.vertices.reshape(-1, 6)
            if selected_count == 1:
                selected = list(self.game.selected_vertices)[0]
                if not (0 <= selected < len(rows)):
                    print("Selected index out of bounds")
                    self.game.edit_mode = False
                    return
                # Parse position
                pos_text = (self.game.edit_pos_text or "").strip()
                if pos_text:
                    pos_list = ast.literal_eval(pos_text)
                    if not (isinstance(pos_list, (list, tuple)) and len(pos_list) == 3):
                        raise ValueError("Enter [x, y, z] for position")
                    px, py, pz = float(pos_list[0]), float(pos_list[1]), float(pos_list[2])
                else:
                    px, py, pz = rows[selected, :3].astype(float)
                # Parse color (optional)
                color_text = (self.game.edit_color_text or "").strip()
                print(f"Processing color text: '{color_text}'")
                if color_text:
                    col_list = ast.literal_eval(color_text)
                    if not (isinstance(col_list, (list, tuple)) and len(col_list) == 3):
                        raise ValueError("Enter [r, g, b] for color")
                    cr, cg, cb = float(col_list[0]), float(col_list[1]), float(col_list[2])
                    print(f"Parsed color from text: [{cr}, {cg}, {cb}]")
                else:
                    cr, cg, cb = rows[selected, 3:6].astype(float)
                    print(f"Using existing color: [{cr}, {cg}, {cb}]")
                # Snapshot before edit
                self.game.push_undo_snapshot("Edit vertex")
                rows[selected, :3] = [px, py, pz]
                rows[selected, 3:6] = [cr, cg, cb]
                verticesHolder.vertices = rows.astype('f4').flatten()
                self.game.current_color = [cr, cg, cb]
                print(f"Updated vertex {selected} to pos={[px,py,pz]} color={[cr,cg,cb]}")
            else:
                # Multi-select: apply color to all selected vertices; ignore position
                color_text = (self.game.edit_color_text or "").strip()
                print(f"Processing bulk color text: '{color_text}' for {selected_count} vertices")
                if not color_text:
                    self.game.edit_mode = False
                    self.game.edit_text = ""
                    self.game.edit_pos_text = ""
                    self.game.edit_color_text = ""
                    return
                col_list = ast.literal_eval(color_text)
                if not (isinstance(col_list, (list, tuple)) and len(col_list) == 3):
                    raise ValueError("Enter [r, g, b] for color")
                cr, cg, cb = float(col_list[0]), float(col_list[1]), float(col_list[2])
                self.game.push_undo_snapshot("Edit vertex colors")
                indices = sorted(list(self.game.selected_vertices))
                rows[indices, 3:6] = [cr, cg, cb]
                verticesHolder.vertices = rows.astype('f4').flatten()
                self.game.current_color = [cr, cg, cb]
                print(f"Updated {len(indices)} vertices' colors to {[cr, cg, cb]}")
            self.game.edit_mode = False
            self.game.edit_text = ""
            self.game.edit_pos_text = ""
            self.game.edit_color_text = ""
            self.game.renderer.renderer3D.update_vertex_buffer()
        except Exception as e:
            print(f"Invalid edit input: {e}")
            raise

    def apply_add_vertex(self):
        pos_text = (self.game.add_vertex_pos_text or "").strip()
        color_text = (self.game.add_vertex_color_text or "").strip()
        try:
            pos = ast.literal_eval(pos_text)
        except Exception:
            self.game.add_vertex_error = "Invalid position. Use [x, y, z]."
            return
        if not (isinstance(pos, (list, tuple)) and len(pos) == 3):
            self.game.add_vertex_error = "Position must be [x, y, z]."
            return
        try:
            x, y, z = float(pos[0]), float(pos[1]), float(pos[2])
        except Exception:
            self.game.add_vertex_error = "Coordinates must be numbers."
            return
        color_specified = False
        if color_text:
            try:
                col = ast.literal_eval(color_text)
            except Exception:
                self.game.add_vertex_error = "Invalid color. Use [r, g, b]."
                return
            if not (isinstance(col, (list, tuple)) and len(col) == 3):
                self.game.add_vertex_error = "Color must be [r, g, b]."
                return
            try:
                cr, cg, cb = float(col[0]), float(col[1]), float(col[2])
                color_specified = True
            except Exception:
                self.game.add_vertex_error = "Color values must be numbers."
                return
        else:
            cr, cg, cb = self.game.current_color if hasattr(self.game, 'current_color') else (1.0, 1.0, 1.0)

        self.game.push_undo_snapshot("Add vertex")
        current_count = len(verticesHolder.vertices) // 6
        if not color_specified:
            if current_count % 3 == 0:
                self.game.current_color = self.game.random_color()
            cr, cg, cb = self.game.current_color
        else:
            self.game.current_color = [cr, cg, cb]

        new_vertex = [x, y, z, cr, cg, cb]
        verticesHolder.vertices = np.append(verticesHolder.vertices, new_vertex).astype('f4')
        self.remove_trailing_duplicate_vertices()
        self.game.renderer.renderer3D.update_vertex_buffer()
        print(f"New vertex added: {[x, y, z]} color={[cr, cg, cb]}")
        self.game.add_vertex_mode = False
        self.game.add_vertex_text = ""
        self.game.add_vertex_pos_text = ""
        self.game.add_vertex_color_text = ""
        self.game.add_vertex_error = ""

    def remove_trailing_duplicate_vertices(self) -> int:
        try:
            rows = verticesHolder.vertices.reshape(-1, 6)
            if len(rows) <= 1:
                return 0

            def round_triplet(p):
                return (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))

            removed = 0
            keep_until = len(rows)
            seen_prior = {round_triplet(rows[i, :3]) for i in range(len(rows) - 1)}
            for i in range(len(rows) - 1, -1, -1):
                pos_key = round_triplet(rows[i, :3])
                if pos_key in seen_prior:
                    keep_until = i
                    removed += 1
                else:
                    break
            if removed > 0:
                rows = rows[:keep_until]
                verticesHolder.vertices = rows.astype('f4').flatten()
            return removed
        except Exception:
            return 0

    def add_vertex(self, x: float, y: float, z: float):
        assert isinstance(x, float), "x must be float"
        assert isinstance(y, float), "y must be float"
        assert isinstance(z, float), "z must be float"

        self.game.push_undo_snapshot("Add vertex")
        current_count = len(verticesHolder.vertices) // 6
        if current_count % 3 == 0:
            self.game.current_color = self.game.random_color()

        new_vertex = [x, y, z] + self.game.current_color
        verticesHolder.vertices = np.append(verticesHolder.vertices, new_vertex).astype('f4')
        self.remove_trailing_duplicate_vertices()
        self.game.renderer.renderer3D.update_vertex_buffer()
        print(f"New vertex added: {new_vertex[:3]}")

    def delete_selected_vertices(self):
        if not self.game.selected_vertices:
            return
        try:
            self.game.push_undo_snapshot("Delete selected vertices")
            vertices = verticesHolder.vertices
            if vertices.size == 0:
                return
            vertex_rows = vertices.reshape(-1, 6)
            max_index = len(vertex_rows) - 1
            indices_to_delete = sorted([i for i in self.game.selected_vertices if 0 <= i <= max_index])
            if not indices_to_delete:
                return
            keep_mask = np.ones(len(vertex_rows), dtype=bool)
            keep_mask[indices_to_delete] = False
            new_rows = vertex_rows[keep_mask]
            verticesHolder.vertices = new_rows.astype('f4').flatten()

            self.game.selected_vertices.clear()
            self.game.edit_mode = False
            self.game.edit_text = ""
            self.game.yellow_highlights.clear()

            total_vertices = len(verticesHolder.vertices) // 6
            max_offset = max(0, total_vertices - self.game.uiOverlayCreator.max_visible_vertices)
            self.game.uiOverlayCreator.scroll_offset = min(self.game.uiOverlayCreator.scroll_offset, max_offset)

            if total_vertices > 0:
                if total_vertices % 3 == 0:
                    self.game.current_color = self.game.random_color()
                else:
                    last_vertex_color = verticesHolder.vertices[-3:]
                    self.game.current_color = last_vertex_color.tolist()
            else:
                self.game.current_color = self.game.random_color()

            self.game.renderer.renderer3D.update_vertex_buffer()
        except Exception as e:
            print(f"Error deleting vertices: {e}")
        finally:
            self.game.last_selected_vertex_index = None

    def clear_all_vertices(self):
        try:
            verticesHolder.vertices = np.array([], dtype='f4')
            self.game.selected_vertices.clear()
            self.game.yellow_highlights.clear()
            self.game.uiOverlayCreator.scroll_offset = 0
            self.game.current_color = self.game.random_color()
            self.game.edit_mode = False
            self.game.edit_text = ""
            self.game.renderer.renderer3D.update_vertex_buffer()
            print("All vertices cleared")
        except Exception as e:
            print(f"Error clearing all vertices: {e}")
        finally:
            self.game.last_selected_vertex_index = None


