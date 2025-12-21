from src.geometry.VerticesHolder import verticesHolder


class EdgeExistenceChecker:
    """Cleanup utility to check if the selected edge exists among triangle edges."""

    def check_selected_edge_exists(self, game) -> None:
        rows = verticesHolder.vertices.reshape(-1, 6)
        if len(game.selected_vertices) != 2:
            game.set_status("Select exactly two vertices to check edge", 180)
            return
        i_a, i_b = sorted(list(game.selected_vertices))
        if i_a < 0 or i_b >= len(rows):
            game.set_status("Selected vertex indices out of range", 180)
            return
        pos_a = rows[i_a, :3]
        pos_b = rows[i_b, :3]

        def same_point(p, q, tol=1e-6):
            return (abs(float(p[0]) - float(q[0])) <= tol and
                    abs(float(p[1]) - float(q[1])) <= tol and
                    abs(float(p[2]) - float(q[2])) <= tol)

        highlight_indices = set()
        num_tri = len(rows) // 3
        found_count = 0
        for t in range(num_tri):
            i0 = t * 3
            tri_positions = [rows[i0 + 0, :3], rows[i0 + 1, :3], rows[i0 + 2, :3]]
            edges = [(0, 1), (1, 2), (2, 0)]
            for e0, e1 in edges:
                p = tri_positions[e0]
                q = tri_positions[e1]
                if (same_point(p, pos_a) and same_point(q, pos_b)) or (same_point(p, pos_b) and same_point(q, pos_a)):
                    found_count += 1
                    highlight_indices.update({i0 + e0, i0 + e1})

        if found_count > 0:
            game.yellow_highlights = highlight_indices
            game.uiOverlayCreator.scroll_offset = min(highlight_indices)
            game.set_status(f"Edge exists; found in {found_count} triangle edge(s)", 240)
        else:
            game.set_status("No edge exists between selected vertices", 240)


