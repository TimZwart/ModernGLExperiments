import numpy as np
from src.geometry.VerticesHolder import verticesHolder


class InternalEdgeRemover:
    """
    Cleanup utility that attempts to remove triangles incident to edges classified as fully internal,
    using raycasts from sampled points along each edge in a fixed set of directions.

    This was extracted from EventHandler.remove_internal_edges_via_raycasts for organization.
    """

    def __init__(self, log_path: str = "cleanup_internal_edge_debug.log"):
        self.log_path = str(log_path or "cleanup_internal_edge_debug.log")

    def _log_lines(self, lines):
        """Best-effort append to the internal-edge debug log."""
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                for line in lines:
                    f.write(str(line) + "\n")
        except Exception:
            pass

    def remove_internal_edges_via_raycasts(self, game) -> None:
        # Reset log per invocation (append a header for this run)
        try:
            import datetime as _dt
            ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log_lines([
                "",
                f"=== internal-edge cleanup run {ts} ===",
            ])
        except Exception:
            pass

        rows = verticesHolder.vertices.reshape(-1, 6)
        num_rows = len(rows)
        if num_rows < 3:
            game.set_status("No triangles to process", 180)
            return
        num_tri = num_rows // 3

        # Precompute triangle positions (float64 for robustness)
        # Only operate on complete triangles to avoid reshape errors when rows % 3 != 0
        tri_rows = rows[:num_tri * 3]
        if num_tri == 0:
            game.set_status("No triangles to process", 180)
            return
        tri_pos = tri_rows.reshape(num_tri, 3, 6)[:, :, :3].astype(np.float64)

        # Map edges (by rounded position pairs) to triangles that contain them
        def round_triplet(p):
            return (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))

        # Fast membership test for "does this vertex position exist in the mesh?"
        # Used for additional diagnostics when raycasts miss.
        vertex_pos_set = set()
        try:
            for p in tri_pos.reshape(-1, 3):
                vertex_pos_set.add(round_triplet(p))
        except Exception:
            vertex_pos_set = set()

        edge_to_tris = {}
        for t in range(num_tri):
            p0, p1, p2 = tri_pos[t]
            edges = [(p0, p1), (p1, p2), (p2, p0)]
            for a, b in edges:
                ra, rb = round_triplet(a), round_triplet(b)
                key = tuple(sorted([ra, rb]))
                edge_to_tris.setdefault(key, set()).add(t)

        # Directions: 26-ish directions (axes, face diagonals, space diagonals)
        dirs = []
        base = [
            (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1),
            (1, 1, 0), (1, -1, 0), (-1, 1, 0), (-1, -1, 0),
            (1, 0, 1), (1, 0, -1), (-1, 0, 1), (-1, 0, -1),
            (0, 1, 1), (0, 1, -1), (0, -1, 1), (0, -1, -1),
            (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
            (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1),
        ]
        for dx, dy, dz in base:
            v = np.array([dx, dy, dz], dtype=np.float64)
            n = np.linalg.norm(v)
            if n > 0:
                dirs.append(v / n)
        dirs = np.array(dirs)

        def ray_intersects_triangle(origin, direction, v0, v1, v2, eps=1e-8):
            # Moller-Trumbore
            edge1 = v1 - v0
            edge2 = v2 - v0
            pvec = np.cross(direction, edge2)
            det = np.dot(edge1, pvec)
            if -eps < det < eps:
                return False, None
            inv_det = 1.0 / det
            tvec = origin - v0
            u = np.dot(tvec, pvec) * inv_det
            if u < 0.0 - eps or u > 1.0 + eps:
                return False, None
            qvec = np.cross(tvec, edge1)
            v = np.dot(direction, qvec) * inv_det
            if v < 0.0 - eps or u + v > 1.0 + eps:
                return False, None
            t = np.dot(edge2, qvec) * inv_det
            if t <= eps:
                return False, None
            return True, t

        def edge_is_internal(pa, pb, exclude_tris: set):
            def fmt3(p):
                return f"({float(p[0]):.3f}, {float(p[1]):.3f}, {float(p[2]):.3f})"

            def _detect_axis_aligned_box_diagonal(a, b):
                """
                Heuristic: detect whether edge a->b is a diagonal of an axis-aligned box/rectangle
                whose corner vertices all exist in the current mesh (based on rounded positions).

                Returns a dict with classification info, or None if not detected.
                """
                if not vertex_pos_set:
                    return None

                ra = round_triplet(a)
                rb = round_triplet(b)

                xmin, xmax = (min(ra[0], rb[0]), max(ra[0], rb[0]))
                ymin, ymax = (min(ra[1], rb[1]), max(ra[1], rb[1]))
                zmin, zmax = (min(ra[2], rb[2]), max(ra[2], rb[2]))

                dx = abs(rb[0] - ra[0])
                dy = abs(rb[1] - ra[1])
                dz = abs(rb[2] - ra[2])

                def present(pt):
                    return pt in vertex_pos_set

                # Space diagonal of an axis-aligned box: endpoints are opposite corners, and all 8 corners exist.
                if dx > 0.0 and dy > 0.0 and dz > 0.0:
                    c0 = (xmin, ymin, zmin)
                    c7 = (xmax, ymax, zmax)
                    if (ra == c0 and rb == c7) or (ra == c7 and rb == c0):
                        corners = [
                            (xmin, ymin, zmin),
                            (xmax, ymin, zmin),
                            (xmin, ymax, zmin),
                            (xmax, ymax, zmin),
                            (xmin, ymin, zmax),
                            (xmax, ymin, zmax),
                            (xmin, ymax, zmax),
                            (xmax, ymax, zmax),
                        ]
                        missing = [c for c in corners if not present(c)]
                        if not missing:
                            return {
                                "kind": "space",
                                "xmin": xmin, "xmax": xmax,
                                "ymin": ymin, "ymax": ymax,
                                "zmin": zmin, "zmax": zmax,
                                "corners": corners,
                                "missing": [],
                            }
                        return {
                            "kind": "space_partial",
                            "xmin": xmin, "xmax": xmax,
                            "ymin": ymin, "ymax": ymax,
                            "zmin": zmin, "zmax": zmax,
                            "corners": corners,
                            "missing": missing,
                        }

                # Face diagonal of an axis-aligned rectangle (one axis constant): endpoints differ in exactly 2 axes.
                diffs = int(dx > 0.0) + int(dy > 0.0) + int(dz > 0.0)
                if diffs == 2:
                    # Identify constant axis and build the 4 rectangle corners
                    if dx == 0.0:
                        x = ra[0]
                        corners = [(x, ymin, zmin), (x, ymax, zmin), (x, ymin, zmax), (x, ymax, zmax)]
                    elif dy == 0.0:
                        y = ra[1]
                        corners = [(xmin, y, zmin), (xmax, y, zmin), (xmin, y, zmax), (xmax, y, zmax)]
                    else:
                        z = ra[2]
                        corners = [(xmin, ymin, z), (xmax, ymin, z), (xmin, ymax, z), (xmax, ymax, z)]
                    missing = [c for c in corners if not present(c)]
                    if not missing:
                        return {
                            "kind": "face",
                            "corners": corners,
                            "missing": [],
                        }
                    return {
                        "kind": "face_partial",
                        "corners": corners,
                        "missing": missing,
                    }

                return None

            # Sample points along the edge (avoid endpoints)
            samples = [0.25, 0.5, 0.75]
            for alpha in samples:
                origin = (1.0 - alpha) * pa + alpha * pb
                # Require a hit in every sampled direction to consider interior
                for d in dirs:
                    hit_any = False
                    closest_t = None
                    closest_tri = None
                    for t_idx in range(num_tri):
                        if t_idx in exclude_tris:
                            continue
                        v0, v1, v2 = tri_pos[t_idx]
                        hit, t = ray_intersects_triangle(origin, d, v0, v1, v2)
                        if hit:
                            hit_any = True
                            if (closest_t is None) or (t is not None and t < closest_t):
                                closest_t = float(t) if t is not None else closest_t
                                closest_tri = int(t_idx)
                            break
                    if not hit_any:
                        print(
                            f"[internal-edge] ray miss for edge {fmt3(pa)} -> {fmt3(pb)} "
                            f"at alpha={alpha:.2f}, dir=({float(d[0]):.3f}, {float(d[1]):.3f}, {float(d[2]):.3f})"
                        )
                        # Also log to file so we can analyze failures.
                        self._log_lines([
                            f"[miss] edge {fmt3(pa)} -> {fmt3(pb)} len={float(np.linalg.norm(pb - pa)):.6f} "
                            f"shared_tris={len(exclude_tris)} alpha={alpha:.2f} "
                            f"dir=({float(d[0]):.6f},{float(d[1]):.6f},{float(d[2]):.6f}) "
                            f"closest_hit_tri={closest_tri} closest_t={closest_t}",
                        ])
                        # Additional heuristic: if this edge looks like a diagonal inside an axis-aligned box/rectangle,
                        # log it explicitly so we can investigate why the raycast-based test missed.
                        diag_info = _detect_axis_aligned_box_diagonal(pa, pb)
                        if diag_info is not None:
                            try:
                                ra = round_triplet(pa)
                                rb = round_triplet(pb)
                                kind = diag_info.get("kind", "unknown")
                                corners = diag_info.get("corners", [])
                                missing = diag_info.get("missing", [])
                                self._log_lines([
                                    f"[diag-box] kind={kind} edge={ra}->{rb} "
                                    f"alpha={alpha:.2f} dir=({float(d[0]):.6f},{float(d[1]):.6f},{float(d[2]):.6f})",
                                    f"[diag-box] corners_present={len(corners) - len(missing)}/{len(corners)} "
                                    f"missing={missing}",
                                ])
                            except Exception:
                                pass
                        return False
            return True

        triangles_to_remove = set()
        internal_edge_count = 0
        # Evaluate each unique edge once
        for key, tri_set in edge_to_tris.items():
            ra, rb = key
            pa = np.array(ra, dtype=np.float64)
            pb = np.array(rb, dtype=np.float64)
            # Skip degenerate (zero-length) edges
            length = np.linalg.norm(pb - pa)
            if length < 1e-9:
                continue
            print(
                f"[internal-edge] checking edge {pa[0]:.3f},{pa[1]:.3f},{pa[2]:.3f} -> "
                f"{pb[0]:.3f},{pb[1]:.3f},{pb[2]:.3f}; length={length:.3f}; shared_tris={len(tri_set)}"
            )
            self._log_lines([
                f"[check] edge ({pa[0]:.6f},{pa[1]:.6f},{pa[2]:.6f}) -> ({pb[0]:.6f},{pb[1]:.6f},{pb[2]:.6f}) "
                f"len={float(length):.6f} shared_tris={len(tri_set)} tri_set={sorted(list(tri_set))}",
            ])

            if edge_is_internal(pa, pb, tri_set):
                internal_edge_count += 1
                self._log_lines([
                    f"[internal] edge ({pa[0]:.6f},{pa[1]:.6f},{pa[2]:.6f}) -> ({pb[0]:.6f},{pb[1]:.6f},{pb[2]:.6f}) "
                    f"tri_set={sorted(list(tri_set))}",
                ])
                for t_idx in tri_set:
                    triangles_to_remove.add(t_idx)

        if not triangles_to_remove:
            game.set_status("No internal edges found", 240)
            return

        # Remove triangles (3 rows per triangle)
        mask = np.ones(num_rows, dtype=bool)
        for t_idx in triangles_to_remove:
            i0 = t_idx * 3
            mask[i0:i0 + 3] = False
        new_rows = rows[mask]
        verticesHolder.vertices = new_rows.astype('f4').flatten()

        # Reset selection/UI and keep color continuity
        game.selected_vertices.clear()
        game.edit_mode = False
        game.edit_text = ""
        game.yellow_highlights.clear()

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
        removed_tris = len(triangles_to_remove)
        game.set_status(f"Removed {removed_tris} triangles from {internal_edge_count} internal edge(s)", 300)
        # Clear last selected after geometry changes
        game.last_selected_vertex_index = None


