import numpy as np
import os
import datetime as _dt
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
            # For visualization only: make rays "feel" infinite by extending far past the mesh bounds.
            # (Intersection test itself is still unbounded along +direction.)
            ray_len = max(50.0, diag * 20.0)
        except Exception:
            ray_len = 200.0

        dirs = self._remover._build_directions()

        failing = []
        summary_lines = []
        all_ok = True
        even_failures = 0
        closest_points = []

        for di, d in enumerate(dirs):
            d = np.array(d, dtype=np.float64)
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
                        'dir': [float(d[0]), float(d[1]), float(d[2])],
                    })
                    summary_lines.append(f"d{di:02d}: hits=0 (miss)")
                else:
                    even_failures += 1
                    summary_lines.append(f"d{di:02d}: hits={hit_count} (even)")

        game.internal_triangle_debug_triangle = int(tri_idx)
        if all_ok:
            game.internal_triangle_debug_rays = []
            game.internal_triangle_debug_closest_points = []
            game.internal_triangle_debug_closest_triangles = set()
            game.internal_triangle_debug_lines = []
            game.set_status(f"Triangle {int(tri_idx)} is INTERNAL (odd hits in all directions)", 300)
            return

        # Not internal: show missed (0-hit) rays; still report even-parity failures in the text list.
        game.internal_triangle_debug_rays = failing
        game.internal_triangle_debug_closest_points = []
        game.internal_triangle_debug_closest_triangles = set()
        # Keep the on-screen list short; still show counts for each failing dir
        game.internal_triangle_debug_lines = summary_lines[:18]
        if failing:
            # Save a distance report for missed rays: for each triangle, distance to the missed ray.
            try:
                log_dir = "logs"
                os.makedirs(log_dir, exist_ok=True)
                ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                out_path = os.path.join(log_dir, f"internal_triangle_missed_ray_distances_tri{int(tri_idx)}_{ts}.csv")

                # Precompute triangle vertices array: (num_tri, 3, 3)
                tri_vertices = tri_pos.astype(np.float64)

                def _closest_point_on_triangle(p, a, b, c):
                    # From "Real-Time Collision Detection" (Christer Ericson)
                    ab = b - a
                    ac = c - a
                    ap = p - a
                    d1 = float(np.dot(ab, ap))
                    d2 = float(np.dot(ac, ap))
                    if d1 <= 0.0 and d2 <= 0.0:
                        return a
                    bp = p - b
                    d3 = float(np.dot(ab, bp))
                    d4 = float(np.dot(ac, bp))
                    if d3 >= 0.0 and d4 <= d3:
                        return b
                    vc = d1 * d4 - d3 * d2
                    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
                        v = d1 / (d1 - d3) if (d1 - d3) != 0.0 else 0.0
                        return a + v * ab
                    cp = p - c
                    d5 = float(np.dot(ab, cp))
                    d6 = float(np.dot(ac, cp))
                    if d6 >= 0.0 and d5 <= d6:
                        return c
                    vb = d5 * d2 - d1 * d6
                    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
                        w = d2 / (d2 - d6) if (d2 - d6) != 0.0 else 0.0
                        return a + w * ac
                    va = d3 * d6 - d5 * d4
                    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
                        w = (d4 - d3) / ((d4 - d3) + (d5 - d6)) if ((d4 - d3) + (d5 - d6)) != 0.0 else 0.0
                        return b + w * (c - b)
                    # Inside face region
                    denom = (va + vb + vc)
                    if denom == 0.0:
                        return a
                    v = vb / denom
                    w = vc / denom
                    return a + ab * v + ac * w

                def _point_triangle_distance(p, a, b, c) -> float:
                    q = _closest_point_on_triangle(p, a, b, c)
                    return float(np.linalg.norm(p - q))

                def _point_in_triangle_2d(p, a, b, c) -> bool:
                    # Barycentric sign method in 2D
                    def cross2(u, v):
                        return u[0] * v[1] - u[1] * v[0]
                    ab = (b[0] - a[0], b[1] - a[1])
                    bc = (c[0] - b[0], c[1] - b[1])
                    ca = (a[0] - c[0], a[1] - c[1])
                    ap = (p[0] - a[0], p[1] - a[1])
                    bp = (p[0] - b[0], p[1] - b[1])
                    cp = (p[0] - c[0], p[1] - c[1])
                    c1 = cross2(ab, ap)
                    c2 = cross2(bc, bp)
                    c3 = cross2(ca, cp)
                    has_neg = (c1 < 0) or (c2 < 0) or (c3 < 0)
                    has_pos = (c1 > 0) or (c2 > 0) or (c3 > 0)
                    return not (has_neg and has_pos)

                def _dist_point_seg_2d(p, a, b) -> float:
                    ax, ay = a
                    bx, by = b
                    px, py = p
                    vx = bx - ax
                    vy = by - ay
                    wx = px - ax
                    wy = py - ay
                    vv = vx * vx + vy * vy
                    if vv <= 1e-12:
                        dx = px - ax
                        dy = py - ay
                        return float((dx * dx + dy * dy) ** 0.5)
                    t = (wx * vx + wy * vy) / vv
                    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
                    cx = ax + t * vx
                    cy = ay + t * vy
                    dx = px - cx
                    dy = py - cy
                    return float((dx * dx + dy * dy) ** 0.5)

                def _dist_ray_seg_2d(o, d, a, b) -> float:
                    # Min distance between ray o+t d (t>=0) and segment a+u(b-a) (u in [0,1])
                    ox, oy = o
                    dx, dy = d
                    ax, ay = a
                    bx, by = b
                    sx = bx - ax
                    sy = by - ay
                    rx = ox - ax
                    ry = oy - ay
                    a00 = dx * dx + dy * dy
                    a01 = -(dx * sx + dy * sy)
                    a11 = sx * sx + sy * sy
                    b0 = dx * rx + dy * ry
                    b1 = -(sx * rx + sy * ry)
                    det = a00 * a11 - a01 * a01

                    # Default to checking endpoints if degenerate
                    if a00 <= 1e-12 or a11 <= 1e-12:
                        # Ray degenerate -> point-segment distance
                        return _dist_point_seg_2d((ox, oy), (ax, ay), (bx, by))

                    t = 0.0
                    u = 0.0
                    if abs(det) > 1e-12:
                        t = (a01 * b1 - a11 * b0) / det
                        u = (a01 * b0 - a00 * b1) / det
                    # Clamp to constraints
                    if t < 0.0:
                        t = 0.0
                        # minimize over u with t=0 -> closest point on segment to origin point
                        # u = clamp( dot((o-a),(b-a))/|b-a|^2 )
                        denom = a11
                        if denom > 1e-12:
                            u = (-(b1)) / denom  # since b1 = -(s·(o-a))
                            u = 0.0 if u < 0.0 else 1.0 if u > 1.0 else u
                        else:
                            u = 0.0
                    else:
                        if u < 0.0:
                            u = 0.0
                            # minimize over t with u=0 => distance ray to point a
                            # t = max(0, dot(d, a-o)/|d|^2)
                            dotv = dx * (ax - ox) + dy * (ay - oy)
                            t = dotv / a00
                            if t < 0.0:
                                t = 0.0
                        elif u > 1.0:
                            u = 1.0
                            dotv = dx * (bx - ox) + dy * (by - oy)
                            t = dotv / a00
                            if t < 0.0:
                                t = 0.0

                    cx = ox + t * dx
                    cy = oy + t * dy
                    qx = ax + u * sx
                    qy = ay + u * sy
                    ddx = cx - qx
                    ddy = cy - qy
                    return float((ddx * ddx + ddy * ddy) ** 0.5)

                def _closest_points_ray_segment(O, d_unit, A, B):
                    # Closest points between ray (O + t d, t>=0) and segment (A + u (B-A), u in [0,1])
                    # Returns (t,u,Pr,Pq,dist)
                    O = O.astype(np.float64)
                    d = d_unit.astype(np.float64)
                    A = A.astype(np.float64)
                    B = B.astype(np.float64)
                    s = (B - A)
                    w0 = (O - A)
                    a00 = float(np.dot(d, d))
                    a01 = float(np.dot(d, s))
                    a11 = float(np.dot(s, s))
                    b0 = float(np.dot(d, w0))
                    b1 = float(np.dot(s, w0))
                    det = a00 * a11 - a01 * a01

                    # Defaults
                    t = 0.0
                    u = 0.0

                    if a11 <= 1e-12:
                        # Segment is a point
                        u = 0.0
                        t = -b0 / a00 if a00 > 1e-12 else 0.0
                        if t < 0.0:
                            t = 0.0
                    elif abs(det) > 1e-12:
                        # Solve unconstrained for lines:
                        # t = (a01*b1 - a11*b0)/det ; u = (a01*b0 - a00*b1)/det
                        t = (a01 * b1 - a11 * b0) / det
                        u = (a01 * b0 - a00 * b1) / det
                    else:
                        # Parallel; fall back
                        t = 0.0
                        u = b1 / a11

                    # Clamp to constraints t>=0, u in [0,1], with a few iterations
                    for _ in range(3):
                        if t < 0.0:
                            t = 0.0
                        if u < 0.0:
                            u = 0.0
                        elif u > 1.0:
                            u = 1.0

                        Pr = O + d * t
                        Pq = A + s * u
                        r = Pr - Pq
                        # Recompute best t for fixed u
                        denom_t = a00
                        if denom_t > 1e-12:
                            t = -float(np.dot(d, (O - (A + s * u)))) / denom_t
                        # Recompute best u for fixed t
                        denom_u = a11
                        if denom_u > 1e-12:
                            u = float(np.dot(s, (O + d * t - A))) / denom_u

                    # Final clamp and points
                    if t < 0.0:
                        t = 0.0
                    if u < 0.0:
                        u = 0.0
                    elif u > 1.0:
                        u = 1.0
                    Pr = O + d * t
                    Pq = A + s * u
                    dist = float(np.linalg.norm(Pr - Pq))
                    return t, u, Pr, Pq, dist

                def _ray_triangle_closest_points(O, d_unit, a3, b3, c3):
                    # Returns (dist, pt_ray, pt_tri)
                    hit, tt = self._remover._ray_intersects_triangle(O, d_unit, a3, b3, c3)
                    if hit and tt is not None:
                        P = O + d_unit * float(tt)
                        return 0.0, P, P

                    best_dist = float('inf')
                    best_pr = O.copy()
                    best_pt = _closest_point_on_triangle(O, a3, b3, c3)
                    best_dist = float(np.linalg.norm(best_pr - best_pt))

                    # Edge candidates
                    edges = [(a3, b3), (b3, c3), (c3, a3)]
                    for e0, e1 in edges:
                        _t, _u, Pr, Pq, dist = _closest_points_ray_segment(O, d_unit, e0, e1)
                        if dist < best_dist:
                            best_dist = dist
                            best_pr = Pr
                            best_pt = Pq

                    # Plane-intersection candidate (if t>=0)
                    n = np.cross(b3 - a3, c3 - a3)
                    nn = float(np.linalg.norm(n))
                    if nn > 1e-12:
                        n = n / nn
                        denom = float(np.dot(n, d_unit))
                        s0 = float(np.dot(n, (O - a3)))
                        if abs(denom) > 1e-12:
                            t_plane = -s0 / denom
                            if t_plane >= 0.0:
                                P = O + d_unit * t_plane
                                Q = _closest_point_on_triangle(P, a3, b3, c3)
                                dist = float(np.linalg.norm(P - Q))
                                if dist < best_dist:
                                    best_dist = dist
                                    best_pr = P
                                    best_pt = Q

                    return best_dist, best_pr, best_pt

                def _ray_triangle_distance(O, d_unit, a3, b3, c3) -> float:
                    # True minimum distance between ray (O + t d, t>=0) and triangle (a,b,c).
                    # 0 if intersects.
                    hit, _t = self._remover._ray_intersects_triangle(O, d_unit, a3, b3, c3)
                    if hit:
                        return 0.0
                    n = np.cross(b3 - a3, c3 - a3)
                    nn = float(np.linalg.norm(n))
                    if nn <= 1e-12:
                        # Degenerate triangle -> min distance to its segments/points
                        return min(
                            float(np.linalg.norm(np.cross((a3 - O), d_unit))),  # line distance (approx)
                            float(np.linalg.norm(np.cross((b3 - O), d_unit))),
                            float(np.linalg.norm(np.cross((c3 - O), d_unit))),
                        )
                    n = n / nn
                    denom = float(np.dot(n, d_unit))
                    s0 = float(np.dot(n, (O - a3)))
                    if abs(denom) > 1e-12:
                        # Ray intersects plane at t_plane
                        t_plane = -s0 / denom
                        if t_plane >= 0.0:
                            P = O + d_unit * t_plane
                            # distance from plane intersection point to triangle (in-plane)
                            # if inside triangle => 0; else min edge distance in plane == point-triangle distance in 3D (since coplanar)
                            return _point_triangle_distance(P, a3, b3, c3)
                        # Plane intersection behind origin: closest ray point to plane is origin
                        return _point_triangle_distance(O, a3, b3, c3)
                    # Ray parallel to plane: distance decomposes into plane offset and in-plane distance
                    plane_dist = abs(s0)
                    # Build orthonormal basis (u,v) in plane
                    ref = np.array([1.0, 0.0, 0.0], dtype=np.float64)
                    if abs(float(np.dot(ref, n))) > 0.9:
                        ref = np.array([0.0, 1.0, 0.0], dtype=np.float64)
                    u = np.cross(n, ref)
                    un = float(np.linalg.norm(u))
                    if un <= 1e-12:
                        return plane_dist
                    u = u / un
                    v = np.cross(n, u)
                    # Project ray origin onto plane
                    Oproj = O - s0 * n
                    # 2D coords
                    o2 = (float(np.dot(Oproj, u)), float(np.dot(Oproj, v)))
                    d2 = (float(np.dot(d_unit, u)), float(np.dot(d_unit, v)))
                    d2n = (d2[0] * d2[0] + d2[1] * d2[1]) ** 0.5
                    if d2n <= 1e-12:
                        # No in-plane movement -> constant point above plane
                        # In-plane distance is point-to-triangle (2D)
                        a2 = (float(np.dot(a3, u)), float(np.dot(a3, v)))
                        b2 = (float(np.dot(b3, u)), float(np.dot(b3, v)))
                        c2 = (float(np.dot(c3, u)), float(np.dot(c3, v)))
                        if _point_in_triangle_2d(o2, a2, b2, c2):
                            inplane = 0.0
                        else:
                            inplane = min(_dist_point_seg_2d(o2, a2, b2), _dist_point_seg_2d(o2, b2, c2), _dist_point_seg_2d(o2, c2, a2))
                        return float((plane_dist * plane_dist + inplane * inplane) ** 0.5)
                    d2u = (d2[0] / d2n, d2[1] / d2n)
                    a2 = (float(np.dot(a3, u)), float(np.dot(a3, v)))
                    b2 = (float(np.dot(b3, u)), float(np.dot(b3, v)))
                    c2 = (float(np.dot(c3, u)), float(np.dot(c3, v)))
                    # If ray (in-plane) intersects triangle, in-plane distance 0
                    # Simple check: if origin inside triangle
                    if _point_in_triangle_2d(o2, a2, b2, c2):
                        inplane = 0.0
                    else:
                        inplane = min(
                            _dist_ray_seg_2d(o2, d2u, a2, b2),
                            _dist_ray_seg_2d(o2, d2u, b2, c2),
                            _dist_ray_seg_2d(o2, d2u, c2, a2),
                        )
                    return float((plane_dist * plane_dist + inplane * inplane) ** 0.5)

                with open(out_path, "w", encoding="utf-8") as f:
                    f.write("selected_triangle,ray_dir_index,ray_dx,ray_dy,ray_dz,triangle_index,triangle_ray_distance\n")
                    O = centroid.astype(np.float64)
                    for r in failing:
                        di = int(r.get("dir_index", -1))
                        d = np.array(r.get("dir", [0.0, 0.0, 1.0]), dtype=np.float64)
                        dn = float(np.linalg.norm(d))
                        if dn <= 1e-12:
                            continue
                        d = d / dn
                        best = None
                        for ti in range(num_tri):
                            # Exclude the inspected triangle itself from "closest triangle to this ray" analysis
                            # (otherwise it will usually win with distance ~0 because the ray starts on it).
                            if int(ti) == int(tri_idx):
                                continue
                            a3, b3, c3 = tri_vertices[ti]
                            dist = _ray_triangle_distance(O, d, a3, b3, c3)
                            f.write(f"{int(tri_idx)},{di},{float(d[0])},{float(d[1])},{float(d[2])},{ti},{float(dist)}\n")
                            if best is None or dist < best[0]:
                                # Also compute closest points for the closest triangle (for visualization)
                                dd, pr, pt = _ray_triangle_closest_points(O, d, a3, b3, c3)
                                best = (float(dist), int(ti), pr, pt, float(dd))
                        if best is not None:
                            closest_points.append({
                                'ray_dir_index': int(di),
                                'closest_triangle': int(best[1]),
                                'pt_ray': [float(best[2][0]), float(best[2][1]), float(best[2][2])],
                                'pt_tri': [float(best[3][0]), float(best[3][1]), float(best[3][2])],
                                'distance': float(best[4]),
                            })
                # Store closest point visualization for the overlay
                try:
                    game.internal_triangle_debug_closest_points = list(closest_points)
                    game.internal_triangle_debug_closest_triangles = set([int(p.get('closest_triangle')) for p in closest_points if p.get('closest_triangle') is not None])
                except Exception:
                    game.internal_triangle_debug_closest_points = []
                    game.internal_triangle_debug_closest_triangles = set()
                game.set_status(
                    f"Triangle {int(tri_idx)} is NOT internal. Showing {len(failing)} missed rays (0 hits). Saved distances to {out_path}",
                    420
                )
                return
            except Exception:
                pass
            game.set_status(
                f"Triangle {int(tri_idx)} is NOT internal. Showing {len(failing)} missed rays (0 hits).",
                360
            )
        else:
            game.set_status(
                f"Triangle {int(tri_idx)} is NOT internal. No missed rays; parity failed in {even_failures} direction(s).",
                360
            )


