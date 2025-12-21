import numpy as np
from src.geometry.VerticesHolder import verticesHolder


class CoveredTriangleRemover:
    """Utility that removes triangles fully covered by other coplanar triangles.

    Notes on behavior (kept identical to inlined version):
    - Triangles are grouped into plane buckets using a rounded plane key
      (unit normal and offset rounded to 1e-6). This can merge nearly-coplanar
      triangles.
    - Each bucket is projected to 2D by dropping the dominant component of the
      bucket's normal.
    - A triangle is considered fully covered if all of its interior sample
      points (barycentric grid) are contained within the union of other
      triangles in the same bucket.
    - Sampling density is modest (steps=6) and inclusion uses a small tolerance.
    """

    def __init__(self, debug: bool = True):
        # Debug logging is enabled by default per user request to analyze bucketing
        self.debug = bool(debug)

    def remove_fully_covered_triangles(self, game) -> None:
        try:
            tri_pos = self.create_triangle_positions_array(game)
        except Exception:
            game.set_status("No triangles to process", 180)
            return
        # Also keep original rows/num_rows for removal phase
        rows = verticesHolder.vertices.reshape(-1, 6)
        num_rows = len(rows)

        # First, mark degenerate triangles (zero area or repeated vertices)
        triangles_to_remove = set()
        for t in range(len(tri_pos)):
            p0, p1, p2 = tri_pos[t]
            # Repeat check
            if (np.allclose(p0, p1, atol=1e-9) or
                    np.allclose(p1, p2, atol=1e-9) or
                    np.allclose(p0, p2, atol=1e-9)):
                triangles_to_remove.add(t)
                try:
                    i0 = t * 3
                    i1 = i0 + 1
                    i2 = i0 + 2
                    msg = (
                        f"[degenerate] removing tri {t} rows [{i0},{i1},{i2}] due to repeated vertex"
                    )
                    self._log_lines([msg])
                except Exception:
                    pass
                continue
            # Zero-area check (collinear)
            area = np.linalg.norm(np.cross(p1 - p0, p2 - p0))
            if area <= 1e-12:
                triangles_to_remove.add(t)
                try:
                    i0 = t * 3
                    i1 = i0 + 1
                    i2 = i0 + 2
                    msg = (
                        f"[degenerate] removing tri {t} rows [{i0},{i1},{i2}] due to zero area"
                    )
                    self._log_lines([msg])
                except Exception:
                    pass

        # Build plane buckets
        #Plane buckets = groups of triangles that lie on (approximately) the same plane.
        plane_to_tri_indices = {}
        num_tri = len(tri_pos)
        for t in range(num_tri):
            if t in triangles_to_remove:
                continue  # already marked degenerate
            p0, p1, p2 = tri_pos[t]
            key = self._plane_key(p0, p1, p2)
            if key is None:
                continue
            plane_to_tri_indices.setdefault(key, []).append(t)
        self.debug_print(plane_to_tri_indices, tri_pos)

        # Projection and coverage test per bucket
        for plane_key, tri_indices in plane_to_tri_indices.items():
            if len(tri_indices) <= 1:
                continue
            nx, ny, nz, _ = plane_key
            plane_normal = np.array([nx, ny, nz], dtype=np.float64)
            dominant_axis = int(np.argmax(np.abs(plane_normal)))
            # Project to 2D by dropping the dominant axis
            keep_axes = [i for i in (0, 1, 2) if i != dominant_axis]

            # Prepare 2D triangle polygons for this bucket
            tri2d_list = []
            for t in tri_indices:
                a, b, c = tri_pos[t]
                tri2 = np.array([
                    [a[keep_axes[0]], a[keep_axes[1]]],
                    [b[keep_axes[0]], b[keep_axes[1]]],
                    [c[keep_axes[0]], c[keep_axes[1]]],
                ], dtype=np.float64)
                tri2d_list.append((t, tri2))

            def _point_in_triangle_2d(point: np.ndarray, tri2: np.ndarray, eps: float = 1e-10) -> bool:
                a, b, c = tri2[0], tri2[1], tri2[2]
                v0 = c - a
                v1 = b - a
                v2 = point - a
                dot00 = float(np.dot(v0, v0))
                dot01 = float(np.dot(v0, v1))
                dot02 = float(np.dot(v0, v2))
                dot11 = float(np.dot(v1, v1))
                dot12 = float(np.dot(v1, v2))
                denom = dot00 * dot11 - dot01 * dot01
                if abs(denom) <= eps:
                    return False
                inv = 1.0 / denom
                u = (dot11 * dot02 - dot01 * dot12) * inv
                v = (dot00 * dot12 - dot01 * dot02) * inv
                return (u >= -1e-8) and (v >= -1e-8) and (u + v <= 1.0 + 1e-8)

            def _generate_interior_samples(tri2: np.ndarray):
                samples = []
                steps = 6  # Sampling density kept the same
                for i in range(1, steps):
                    for j in range(1, steps - i):
                        a = i / steps
                        b = j / steps
                        c = 1.0 - a - b
                        point = a * tri2[0] + b * tri2[1] + c * tri2[2]
                        samples.append(point)
                return samples

            # Union-of-others coverage test, but only using triangles that remain alive (no removed-as-justification).
            # We greedily remove triangles; a triangle can be removed only if, for every sample, there exists a covering
            # triangle that is still kept at the moment of decision.
            alive = set(t for (t, _) in tri2d_list)
            for tri_index, tri2 in tri2d_list:
                if tri_index not in alive:
                    continue
                samples = _generate_interior_samples(tri2)
                if not samples:
                    continue
                fully_covered_by_alive = True
                coverers_used = set()
                for sample in samples:
                    found_coverer = False
                    for other_index, other_tri2 in tri2d_list:
                        if other_index == tri_index or other_index not in alive:
                            continue
                        if _point_in_triangle_2d(sample, other_tri2):
                            found_coverer = True
                            coverers_used.add(other_index)
                            break
                    if not found_coverer:
                        fully_covered_by_alive = False
                        break
                if fully_covered_by_alive:
                    triangles_to_remove.add(tri_index)
                    alive.discard(tri_index)
                    try:
                        i0 = tri_index * 3
                        i1 = i0 + 1
                        i2 = i0 + 2
                        p0 = tri_pos[tri_index][0]
                        p1 = tri_pos[tri_index][1]
                        p2 = tri_pos[tri_index][2]
                        nx, ny, nz, d_key = plane_key
                        msg = (
                            f"[covered] removing tri {tri_index} bucket n=({nx:.6f},{ny:.6f},{nz:.6f}) d={d_key:.6f}; "
                            f"rows [{i0},{i1},{i2}] "
                            f"pos0=({p0[0]:.6f},{p0[1]:.6f},{p0[2]:.6f}) "
                            f"pos1=({p1[0]:.6f},{p1[1]:.6f},{p1[2]:.6f}) "
                            f"pos2=({p2[0]:.6f},{p2[1]:.6f},{p2[2]:.6f}); "
                            f"covered_by_alive={sorted(list(coverers_used))}"
                        )
                        self._log_lines([msg])
                    except Exception:
                        pass

        if not triangles_to_remove:
            game.set_status("No fully covered triangles found", 240)
            return

        # Remove marked triangles
        keep_mask = np.ones(num_rows, dtype=bool)
        for t_idx in triangles_to_remove:
            i0 = t_idx * 3
            keep_mask[i0:i0 + 3] = False
        new_rows = rows[keep_mask]
        verticesHolder.vertices = new_rows.astype('f4').flatten()

        # Reset UI state and keep color continuity
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
        game.set_status(f"Removed {len(triangles_to_remove)} covered/degenerate triangle(s)", 300)
        game.last_selected_vertex_index = None

    def create_triangle_positions_array(self, game):
        rows = verticesHolder.vertices.reshape(-1, 6)
        num_rows = len(rows)
        if num_rows < 3:
            game.set_status("No triangles to process", 180)
            raise ValueError("No triangles to process")
        num_tri = num_rows // 3
        tri_rows = rows[:num_tri * 3]
        if num_tri == 0:
            game.set_status("No triangles to process", 180)
            raise ValueError("No triangles to process")
        tri_pos = tri_rows.reshape(num_tri, 3, 6)[:, :, :3].astype(np.float64)
        return tri_pos

    def _plane_key(self, p0: np.ndarray, p1: np.ndarray, p2: np.ndarray):
        v0 = p1 - p0
        v1 = p2 - p0
        n = np.cross(v0, v1)
        ln = np.linalg.norm(n)
        if ln <= 1e-12:
            return None
        n = n / ln
        # Canonicalize normal direction (largest magnitude component positive)
        idx = int(np.argmax(np.abs(n)))
        if n[idx] < 0:
            n = -n
        d = -float(np.dot(n, p0))
        r = lambda x: round(float(x), 6)
        return (r(n[0]), r(n[1]), r(n[2]), r(d))

    def debug_print(self, plane_to_tri_indices, tri_pos):
        # Minimal debug logging: write bucket counts and a few indices to a log file (no behavior change)
        try:
            lines = []
            lines.append(f"[covered] plane bucket count: {len(plane_to_tri_indices)}")
            for key, idxs in plane_to_tri_indices.items():
                nx, ny, nz, d_key = key
                shown = ", ".join(map(str, idxs[:6])) + (" ..." if len(idxs) > 6 else "")
                extra = []
                if abs(ny) > 1e-12:
                    try:
                        extra.append(f"y≈{-float(d_key)/float(ny):.6f}")
                    except Exception:
                        pass
                if abs(nx) > 1e-12:
                    try:
                        extra.append(f"x≈{-float(d_key)/float(nx):.6f}")
                    except Exception:
                        pass
                extras = (" "+", ".join(extra)) if extra else ""
                lines.append(f"[covered] bucket n=({nx:.6f},{ny:.6f},{nz:.6f}) d={d_key:.6f} count={len(idxs)} idx=[{shown}]{extras}")
                # Detail: for each triangle in this bucket, list its vertex row indices and positions
                try:
                    for t in idxs:
                        i0 = t * 3
                        i1 = i0 + 1
                        i2 = i0 + 2
                        p0 = tri_pos[t][0]
                        p1 = tri_pos[t][1]
                        p2 = tri_pos[t][2]
                        lines.append(
                            f"  tri {t}: rows [{i0},{i1},{i2}] pos0=({p0[0]:.6f},{p0[1]:.6f},{p0[2]:.6f}) pos1=({p1[0]:.6f},{p1[1]:.6f},{p1[2]:.6f}) pos2=({p2[0]:.6f},{p2[1]:.6f},{p2[2]:.6f})"
                        )
                except Exception:
                    pass
            self._log_lines(lines)
        except Exception:
            pass

    def _log_lines(self, lines):
        try:
            log_path = getattr(self, 'log_path', 'cleanup_covered_debug.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                for line in lines:
                    f.write(line + "\n")
        except Exception:
            pass
