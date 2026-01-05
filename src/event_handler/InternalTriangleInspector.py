import numpy as np
from src.geometry.VerticesHolder import verticesHolder
from src.event_handler.InternalTriangleRemover import InternalTriangleRemover


class InternalTriangleInspector:
    """
    Inspect whether a selected triangle is internal by centroid ray parity.

    If the triangle is NOT internal, store debug rays for all failing directions:
    - miss: 0 hits
    - even: even hit count (outside / ambiguous)
    and label each ray with its hit count.
    """

    def __init__(self):
        self._remover = InternalTriangleRemover()

    def inspect_selected_triangle(self, game) -> None:
        tri_idx = getattr(game, 'last_selected_triangle_index', None)
        if tri_idx is None:
            # Fallback if exactly one triangle is selected
            try:
                sel = list(getattr(game, 'selected_triangles', set()))
                if len(sel) == 1:
                    tri_idx = int(sel[0])
            except Exception:
                tri_idx = None
        if tri_idx is None:
            game.set_status("No triangle selected (use Triangle Select tool to pick one)", 240)
            return

        rows = verticesHolder.vertices.reshape(-1, 6)
        num_rows = len(rows)
        num_tri = num_rows // 3
        if num_tri <= 0:
            game.set_status("No triangles to inspect", 180)
            return
        if int(tri_idx) < 0 or int(tri_idx) >= num_tri:
            game.set_status("Selected triangle out of range", 180)
            return

        tri_rows = rows[:num_tri * 3]
        tri_pos = tri_rows.reshape(num_tri, 3, 6)[:, :, :3].astype(np.float64)
        v0, v1, v2 = tri_pos[int(tri_idx)]
        centroid = (v0 + v1 + v2) / 3.0

        # Ray length: a bit bigger than the mesh bounding box diagonal
        try:
            pmin = np.min(tri_pos.reshape(-1, 3), axis=0)
            pmax = np.max(tri_pos.reshape(-1, 3), axis=0)
            diag = float(np.linalg.norm(pmax - pmin))
            ray_len = max(5.0, diag * 2.0)
        except Exception:
            ray_len = 50.0

        dirs = self._remover._build_directions()

        failing = []
        summary_lines = []
        all_ok = True
        even_failures = 0

        for di, d in enumerate(dirs):
            hit_count = 0
            for j in range(num_tri):
                if j == int(tri_idx):
                    continue
                a, b, c = tri_pos[j]
                hit, _t = self._remover._ray_intersects_triangle(centroid, d, a, b, c)
                if hit:
                    hit_count += 1

            ok = (hit_count > 0) and ((hit_count % 2) == 1)
            if not ok:
                all_ok = False
                # Only treat 0-hit rays as "missed rays" for visualization.
                # Even hit counts (e.g., 2) still fail the parity test, but aren't misses.
                if hit_count == 0:
                    end = centroid + d * ray_len
                    failing.append({
                        'origin': [float(centroid[0]), float(centroid[1]), float(centroid[2])],
                        'end': [float(end[0]), float(end[1]), float(end[2])],
                        'hits': 0,
                        'reason': "miss",
                        'color': (255, 0, 0, 220),
                        'dir_index': int(di),
                    })
                    summary_lines.append(f"d{di:02d}: hits=0 (miss)")
                else:
                    even_failures += 1
                    summary_lines.append(f"d{di:02d}: hits={hit_count} (even)")

        game.internal_triangle_debug_triangle = int(tri_idx)
        if all_ok:
            game.internal_triangle_debug_rays = []
            game.internal_triangle_debug_lines = []
            game.set_status(f"Triangle {int(tri_idx)} is INTERNAL (odd hits in all directions)", 300)
            return

        # Not internal: show missed (0-hit) rays; still report even-parity failures in the text list.
        game.internal_triangle_debug_rays = failing
        # Keep the on-screen list short; still show counts for each failing dir
        game.internal_triangle_debug_lines = summary_lines[:18]
        if failing:
            game.set_status(
                f"Triangle {int(tri_idx)} is NOT internal. Showing {len(failing)} missed rays (0 hits).",
                360
            )
        else:
            game.set_status(
                f"Triangle {int(tri_idx)} is NOT internal. No missed rays; parity failed in {even_failures} direction(s).",
                360
            )


