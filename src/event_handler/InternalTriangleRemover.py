import numpy as np
from src.geometry.VerticesHolder import verticesHolder


class InternalTriangleRemover:
    """
    Cleanup utility that attempts to remove triangles whose area lies fully inside the solid,
    even if their edges aren't classified as internal.

    Heuristic approach:
    - For each triangle, raycast from its centroid in many directions.
    - Count intersections with *other* triangles.
    - If a majority of directions have an odd number of hits (and enough directions have hits),
      treat the triangle as internal and remove it.
    """

    def __init__(self):
        pass

    def _build_directions(self) -> np.ndarray:
        # Same 26-direction set used by InternalEdgeRemover (axes, face diagonals, space diagonals)
        base = [
            (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1),
            (1, 1, 0), (1, -1, 0), (-1, 1, 0), (-1, -1, 0),
            (1, 0, 1), (1, 0, -1), (-1, 0, 1), (-1, 0, -1),
            (0, 1, 1), (0, 1, -1), (0, -1, 1), (0, -1, -1),
            (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
            (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1),
        ]
        dirs = []
        for dx, dy, dz in base:
            v = np.array([dx, dy, dz], dtype=np.float64)
            n = np.linalg.norm(v)
            if n > 0:
                dirs.append(v / n)
        return np.array(dirs, dtype=np.float64)

    def _ray_intersects_triangle(self, origin, direction, v0, v1, v2, eps=1e-8):
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

    def _is_triangle_internal(self, tri_index: int, tri_pos: np.ndarray, dirs: np.ndarray) -> bool:
        # tri_pos: (num_tri, 3, 3) float64 positions
        num_tri = tri_pos.shape[0]
        t = int(tri_index)
        v0, v1, v2 = tri_pos[t]
        centroid = (v0 + v1 + v2) / 3.0
        # Strict criterion (very conservative):
        # For a point to be inside a closed mesh, a ray in *any* direction should intersect
        # the surface an odd number of times. If any direction misses or yields even parity,
        # treat as not-internal (avoid false positives).
        for d in dirs:
            hit_count = 0
            for j in range(num_tri):
                if j == t:
                    continue
                a, b, c = tri_pos[j]
                hit, _t = self._ray_intersects_triangle(centroid, d, a, b, c)
                if hit:
                    hit_count += 1
            if hit_count == 0:
                return False
            if (hit_count % 2) == 0:
                return False
        return True

    def remove_internal_triangles_via_centroid_raycast(self, game) -> None:
        rows = verticesHolder.vertices.reshape(-1, 6)
        num_rows = len(rows)
        if num_rows < 3:
            game.set_status("No triangles to process", 180)
            return

        num_tri = num_rows // 3
        tri_rows = rows[:num_tri * 3]
        if num_tri == 0:
            game.set_status("No triangles to process", 180)
            return

        tri_pos = tri_rows.reshape(num_tri, 3, 6)[:, :, :3].astype(np.float64)
        dirs = self._build_directions()

        internal_tris = set()
        for t in range(num_tri):
            try:
                if self._is_triangle_internal(t, tri_pos, dirs):
                    internal_tris.add(t)
            except Exception:
                continue

        if not internal_tris:
            game.set_status("No internal triangles found", 240)
            return

        try:
            game.push_undo_snapshot("Remove internal triangles (centroid raycast)")
        except Exception:
            pass

        mask = np.ones(num_rows, dtype=bool)
        for t in internal_tris:
            i0 = int(t) * 3
            mask[i0:i0 + 3] = False

        new_rows = rows[mask]
        verticesHolder.vertices = new_rows.astype('f4').flatten()

        # Reset selection/UI similar to other cleanup tools
        game.selected_vertices.clear()
        game.selected_triangles = set()
        game.triangle_highlights = set()
        game.yellow_highlights.clear()
        game.edit_mode = False
        game.edit_text = ""
        game.edit_pos_text = ""
        game.edit_color_text = ""
        game.last_selected_vertex_index = None
        game.last_selected_triangle_index = None

        total_vertices = len(verticesHolder.vertices) // 6
        if total_vertices > 0:
            if total_vertices % 3 == 0:
                game.current_color = game.random_color()
            else:
                last_vertex_color = verticesHolder.vertices[-3:]
                game.current_color = last_vertex_color.tolist()
        else:
            game.current_color = game.random_color()

        game.renderer.renderer3D.update_vertex_buffer()
        game.set_status(f"Removed {len(internal_tris)} internal triangle(s)", 300)


