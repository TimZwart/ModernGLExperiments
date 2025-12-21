import numpy as np
from src.geometry.VerticesHolder import verticesHolder


class BackfaceTriangleFixer:
    """
    Cleanup utility:
    - Flips inward-facing triangles by winding (object-centric heuristic).
    - Removes duplicate triangles (same 3 positions, order-agnostic).

    Extracted from EventHandler.remove_backfacing_triangles for organization.
    """

    def fix_backfaces_and_remove_duplicates(self, game) -> None:
        vertices = verticesHolder.vertices
        if vertices.size == 0:
            return
        rows = vertices.reshape(-1, 6)
        num_tri = len(rows) // 3
        if num_tri == 0:
            return

        # Object-centric orientation: outward is away from object bounding-box center
        all_positions = rows[:, :3]
        if len(all_positions) > 0:
            mins = np.min(all_positions, axis=0)
            maxs = np.max(all_positions, axis=0)
            object_center = (mins + maxs) * 0.5
        else:
            object_center = np.array([0.0, 0.0, 0.0])

        def tri_outward(t_index: int) -> bool:
            i0 = t_index * 3
            p0 = np.array(rows[i0, :3], dtype=float)
            p1 = np.array(rows[i0 + 1, :3], dtype=float)
            p2 = np.array(rows[i0 + 2, :3], dtype=float)
            normal = np.cross(p1 - p0, p2 - p0)
            norm_len = np.linalg.norm(normal)
            if norm_len == 0:
                return False
            tri_center = (p0 + p1 + p2) / 3.0
            from_object_center = tri_center - object_center
            dot = float(np.dot(normal, from_object_center))
            eps = 1e-8 * (np.linalg.norm(from_object_center) * norm_len + 1.0)
            return dot >= -eps

        flipped = 0
        for t in range(num_tri):
            if not tri_outward(t):
                i0 = t * 3
                # Swap rows i0+1 and i0+2 to flip winding
                tmp = rows[i0 + 1].copy()
                rows[i0 + 1] = rows[i0 + 2]
                rows[i0 + 2] = tmp
                flipped += 1

        # Remove duplicate triangles (same three positions, ignoring order and colors)
        num_tri_after = len(rows) // 3
        seen = set()
        keep_row_indices = []
        duplicates_removed = 0

        def canonical_key(p0, p1, p2):
            def round_triplet(p):
                return (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))

            pts = sorted([round_triplet(p0), round_triplet(p1), round_triplet(p2)])
            return tuple(pts)

        for t in range(num_tri_after):
            i0 = t * 3
            p0 = rows[i0, :3]
            p1 = rows[i0 + 1, :3]
            p2 = rows[i0 + 2, :3]
            key = canonical_key(p0, p1, p2)
            if key in seen:
                duplicates_removed += 1
                continue
            seen.add(key)
            keep_row_indices.extend([i0, i0 + 1, i0 + 2])

        if duplicates_removed > 0:
            rows = rows[keep_row_indices]

        if flipped == 0 and duplicates_removed == 0:
            print("No inward-facing triangles to fix or duplicate triangles to remove.")
            return

        if duplicates_removed > 0:
            print(f"Removed {duplicates_removed} duplicate triangle(s).")

        verticesHolder.vertices = rows.astype('f4').flatten()

        # Clear selection and editing state
        game.selected_vertices.clear()
        game.edit_mode = False
        game.edit_text = ""
        game.yellow_highlights.clear()

        # Maintain current color for subsequent additions
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
        print(f"Fixed winding for {flipped} inward-facing triangle(s).")
        # Clear last selected after geometry reorientation
        game.last_selected_vertex_index = None


