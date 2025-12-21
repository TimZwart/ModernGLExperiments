import numpy as np
from src.geometry.VerticesHolder import verticesHolder


class PositionMatchInspector:
    """
    Cleanup helper: builds overlay/wireframe lists for triangles composed only of positions matching
    the currently selected vertex positions.
    """

    def show_triangles_matching_selected_positions(self, game) -> None:
        try:
            rows = verticesHolder.vertices.reshape(-1, 6)
        except Exception:
            game.cleanup_position_overlays = []
            game.cleanup_position_wireframes = []
            game.set_status("No vertices available", 180)
            return

        selected_indices = [i for i in game.selected_vertices if 0 <= i < len(rows)]
        game.cleanup_position_overlays = []
        game.cleanup_position_wireframes = []

        if not selected_indices:
            game.set_status("Select at least one vertex to inspect", 180)
            return

        pos = rows[:, :3]
        num_tri = len(rows) // 3
        if num_tri == 0:
            game.set_status("No triangles to inspect", 180)
            return

        def pos_key(p):
            return (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))

        selected_keys = {pos_key(pos[i]) for i in selected_indices}
        overlays = []
        wireframes = []
        colors = [
            (255, 0, 0, 120),     # red
            (0, 255, 0, 120),     # green
            (0, 0, 255, 120),     # blue
            (255, 255, 0, 120),   # yellow
            (255, 0, 255, 120),   # magenta
            (0, 255, 255, 120),   # cyan
            (255, 128, 0, 120),   # orange
            (128, 0, 255, 120),   # purple
            (128, 128, 128, 120), # gray
        ]

        color_index = 0
        overlay_tri_indices = set()
        for t in range(num_tri):
            i0 = t * 3
            tri_indices = [i0 + 0, i0 + 1, i0 + 2]
            if any(idx >= len(pos) for idx in tri_indices):
                continue
            tri_pos = pos[tri_indices]
            if not all(pos_key(p) in selected_keys for p in tri_pos):
                continue
            screen_pts = game.renderer.renderer3D.world_to_screen(tri_pos)
            if np.isnan(screen_pts).any():
                continue
            color = colors[color_index % len(colors)]
            color_index += 1
            overlay_tri_indices.add(t)
            label_lines = [
                f"p0 [{tri_pos[0][0]:.4f}, {tri_pos[0][1]:.4f}, {tri_pos[0][2]:.4f}]",
                f"p1 [{tri_pos[1][0]:.4f}, {tri_pos[1][1]:.4f}, {tri_pos[1][2]:.4f}]",
                f"p2 [{tri_pos[2][0]:.4f}, {tri_pos[2][1]:.4f}, {tri_pos[2][2]:.4f}]",
            ]
            centroid = np.mean(screen_pts, axis=0)
            overlays.append({
                'triangle_index': t,
                'screen_pts': [(float(screen_pts[0][0]), float(screen_pts[0][1])),
                               (float(screen_pts[1][0]), float(screen_pts[1][1])),
                               (float(screen_pts[2][0]), float(screen_pts[2][1]))],
                'color': color,
                'labels': label_lines,
                'label_pos': (float(centroid[0]), float(centroid[1])),
            })

        # Build wireframe overlays for non-matching triangles
        for t in range(num_tri):
            if t in overlay_tri_indices:
                continue
            i0 = t * 3
            tri_indices = [i0 + 0, i0 + 1, i0 + 2]
            if any(idx >= len(pos) for idx in tri_indices):
                continue
            tri_pos = pos[tri_indices]
            screen_pts = game.renderer.renderer3D.world_to_screen(tri_pos)
            if np.isnan(screen_pts).any():
                continue
            wireframes.append([
                (float(screen_pts[0][0]), float(screen_pts[0][1])),
                (float(screen_pts[1][0]), float(screen_pts[1][1])),
                (float(screen_pts[2][0]), float(screen_pts[2][1])),
            ])

        game.cleanup_position_overlays = overlays
        game.cleanup_position_wireframes = wireframes
        game.set_status(f"Found {len(overlays)} triangle(s) using selected positions", 240)


