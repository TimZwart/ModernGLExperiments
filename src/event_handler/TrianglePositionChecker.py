import numpy as np
from src.geometry.VerticesHolder import verticesHolder


class TrianglePositionChecker:
    """
    Cleanup helper: check whether the positions of exactly 3 selected vertices form a triangle
    somewhere in the mesh (order-independent, tolerance-based via rounding).
    """

    def __init__(self, round_decimals: int = 6):
        self.round_decimals = int(round_decimals)

    def _pos_key(self, p):
        d = self.round_decimals
        return (round(float(p[0]), d), round(float(p[1]), d), round(float(p[2]), d))

    def check_selected_vertices_form_triangle(self, game) -> None:
        try:
            rows = verticesHolder.vertices.reshape(-1, 6)
        except Exception:
            game.cleanup_position_overlays = []
            game.cleanup_position_wireframes = []
            game.set_status("No vertices available", 180)
            return

        selected_indices = sorted([i for i in game.selected_vertices if 0 <= i < len(rows)])
        if len(selected_indices) != 3:
            game.set_status("Select exactly 3 vertices to check triangle-by-position", 240)
            return

        pos = rows[:, :3]
        sel_keys = sorted([self._pos_key(pos[i]) for i in selected_indices])

        num_tri = len(rows) // 3
        if num_tri == 0:
            game.set_status("No triangles to inspect", 180)
            return

        matches = []
        overlays = []
        for t in range(num_tri):
            i0 = t * 3
            tri_indices = [i0 + 0, i0 + 1, i0 + 2]
            if any(idx >= len(pos) for idx in tri_indices):
                continue
            tri_pos = pos[tri_indices]
            tri_keys = sorted([self._pos_key(tri_pos[0]), self._pos_key(tri_pos[1]), self._pos_key(tri_pos[2])])
            if tri_keys != sel_keys:
                continue
            matches.append(int(t))
            screen_pts = game.renderer.renderer3D.world_to_screen(tri_pos)
            if np.isnan(screen_pts).any():
                continue
            centroid = np.mean(screen_pts, axis=0)
            overlays.append({
                'triangle_index': int(t),
                'screen_pts': [(float(screen_pts[0][0]), float(screen_pts[0][1])),
                               (float(screen_pts[1][0]), float(screen_pts[1][1])),
                               (float(screen_pts[2][0]), float(screen_pts[2][1]))],
                'color': (255, 255, 0, 140),  # yellow
                'labels': [f"Match tri {int(t)}"],
                'label_pos': (float(centroid[0]), float(centroid[1])),
            })

        # Reuse cleanup overlay slots for visualization; do not draw wireframes here.
        game.cleanup_position_overlays = overlays
        game.cleanup_position_wireframes = []

        if matches:
            head = ", ".join(str(m) for m in matches[:10])
            more = "" if len(matches) <= 10 else f" (+{len(matches) - 10} more)"
            game.set_status(f"Triangle-by-position exists: {len(matches)} match(es): {head}{more}", 360)
        else:
            game.set_status("Triangle-by-position NOT found (no triangle matches these 3 positions)", 360)


