import os
import numpy as np

from src.geometry.VerticesHolder import verticesHolder


class VerticesAnalyzeExporter:
    """
    Export the current mesh to a human-friendly `.vertices.analyze` file.

    Format:
    - For each triangle: 3 vertex lines: "x y z <coordLabel>"
    - Then an edge-length summary line: "<a>-<b> len L1, <b>-<c> len L2, <c>-<a> len L3"
    - Then a blank line
    - Then a triangle label line: "A", "B", ... or "A'", "A''", ... for parallel matches
    - Vertex coordinate labels are lowercase letters starting at 'n' for the first unique coordinate.
      For vertices of a parallel triangle A', the vertex labels are derived from A's vertex labels by
      appending the same number of primes (n -> n', etc), using best-effort correspondence matching.
    """

    def __init__(self, tol_pos: float = 1e-6, tol_parallel: float = 1e-6, tol_plane: float = 1e-6):
        self.tol_pos = float(tol_pos)
        self.tol_parallel = float(tol_parallel)
        self.tol_plane = float(tol_plane)

    def _fmt_num(self, x: float) -> str:
        try:
            x = float(x)
        except Exception:
            return str(x)
        # avoid "-0"
        if abs(x) < 1e-12:
            x = 0.0
        if abs(x - round(x)) <= 1e-9:
            return str(int(round(x)))
        s = f"{x:.6f}".rstrip("0").rstrip(".")
        return s if s else "0"

    def _pos_key(self, p) -> tuple:
        return (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))

    def _letter_sequence(self, start_char: str = "n"):
        # n..z then aa..az then ba..bz ...
        alphabet = [chr(c) for c in range(ord("a"), ord("z") + 1)]
        start_idx = alphabet.index(start_char) if start_char in alphabet else 0
        # first pass from start_char to z
        for i in range(start_idx, len(alphabet)):
            yield alphabet[i]
        # then two-letter sequences
        n = 1
        while True:
            for a in alphabet:
                for b in alphabet:
                    yield a * n + b
            n += 1

    def _tri_label_sequence(self):
        # A..Z, AA..AZ, BA..BZ ...
        alphabet = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        for a in alphabet:
            yield a
        n = 1
        while True:
            for a in alphabet:
                for b in alphabet:
                    yield a * n + b
            n += 1

    def _plane_from_tri(self, p0, p1, p2):
        v0 = p1 - p0
        v1 = p2 - p0
        n = np.cross(v0, v1)
        ln = float(np.linalg.norm(n))
        if ln <= 1e-12:
            return None
        n = n / ln
        # canonicalize direction
        idx = int(np.argmax(np.abs(n)))
        if n[idx] < 0:
            n = -n
        d = -float(np.dot(n, p0))
        return n, d

    def _normal_key(self, n: np.ndarray) -> tuple:
        return (round(float(n[0]), 6), round(float(n[1]), 6), round(float(n[2]), 6))

    def _basis_from_normal(self, n: np.ndarray):
        # pick a helper axis not parallel to n
        ax = np.array([1.0, 0.0, 0.0], dtype=float)
        if abs(float(np.dot(ax, n))) > 0.9:
            ax = np.array([0.0, 1.0, 0.0], dtype=float)
        u = np.cross(n, ax)
        un = float(np.linalg.norm(u))
        if un <= 1e-12:
            ax = np.array([0.0, 0.0, 1.0], dtype=float)
            u = np.cross(n, ax)
            un = float(np.linalg.norm(u))
        u = u / max(un, 1e-12)
        v = np.cross(n, u)
        v = v / max(float(np.linalg.norm(v)), 1e-12)
        return u, v

    def _match_vertices_by_projection(self, base_tri: np.ndarray, tri: np.ndarray, n: np.ndarray):
        """Return a permutation mapping tri vertices -> base vertices by closest 2D projection."""
        u, v = self._basis_from_normal(n)
        base2 = np.stack([base_tri.dot(u), base_tri.dot(v)], axis=1)
        tri2 = np.stack([tri.dot(u), tri.dot(v)], axis=1)
        perms = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]
        best = None
        best_cost = None
        for perm in perms:
            cost = 0.0
            for i, j in enumerate(perm):
                d = tri2[i] - base2[j]
                cost += float(d[0] * d[0] + d[1] * d[1])
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best = perm
        return best, best_cost

    def export(self, game) -> str:
        # determine output path
        base = (getattr(game, "filename_text", "") or "untitled.vertices").strip()
        if base.lower().endswith(".vertices.analyze"):
            out_path = base
        elif base.lower().endswith(".vertices"):
            out_path = base + ".analyze"
        else:
            out_path = base + ".vertices.analyze"
        out_path = os.path.normpath(out_path)

        rows = verticesHolder.vertices.reshape(-1, 6)
        num_tri = len(rows) // 3
        tri_rows = rows[:num_tri * 3]
        tri_pos = tri_rows.reshape(num_tri, 3, 6)[:, :, :3].astype(np.float64)

        # coordinate labels
        coord_gen = self._letter_sequence("n")
        coord_label_by_pos = {}
        special_label_by_pos = {}  # for primed labels

        def get_or_assign_coord_label(pos_key):
            if pos_key in special_label_by_pos:
                return special_label_by_pos[pos_key]
            if pos_key in coord_label_by_pos:
                return coord_label_by_pos[pos_key]
            lbl = next(coord_gen)
            coord_label_by_pos[pos_key] = lbl
            return lbl

        # triangle labels with parallel detection
        tri_label_gen = self._tri_label_sequence()
        tri_label = [None] * num_tri
        tri_plane = [None] * num_tri
        base_tri_indices_by_normal = {}  # normal_key -> list of base triangles (indices)
        prime_count_by_base = {}         # base idx -> count

        for i in range(num_tri):
            p = tri_pos[i]
            plane = self._plane_from_tri(p[0], p[1], p[2])
            tri_plane[i] = plane
            if plane is None:
                tri_label[i] = next(tri_label_gen)
                continue
            n, d = plane
            nk = self._normal_key(n)
            # find best matching earlier base triangle with same normal (closest plane offset), if any
            best_base = None
            best_dd = None
            for b in base_tri_indices_by_normal.get(nk, []):
                pb = tri_plane[b]
                if pb is None:
                    continue
                _, db = pb
                dd = abs(float(d - db))
                if dd <= self.tol_plane:
                    continue  # coplanar, not "parallel triangle"
                if best_dd is None or dd < best_dd:
                    best_dd = dd
                    best_base = b
            if best_base is not None:
                k = prime_count_by_base.get(best_base, 0) + 1
                prime_count_by_base[best_base] = k
                tri_label[i] = (tri_label[best_base] or "A") + ("'" * k)
            else:
                tri_label[i] = next(tri_label_gen)
                base_tri_indices_by_normal.setdefault(nk, []).append(i)

        # Now emit file
        lines = []
        for i in range(num_tri):
            tri = tri_pos[i]
            lbl = tri_label[i] or "A"

            # Determine if this is a prime triangle (contains ')
            if "'" in lbl:
                # Find base label (strip primes)
                base_lbl = lbl.rstrip("'")
                prime_suffix = lbl[len(base_lbl):]
                # Find base triangle index by label
                try:
                    base_idx = next(j for j in range(i) if (tri_label[j] == base_lbl))
                except StopIteration:
                    base_idx = None
                if base_idx is not None and tri_plane[i] is not None and tri_plane[base_idx] is not None:
                    n, _ = tri_plane[base_idx]
                    base_tri = tri_pos[base_idx]
                    perm, _ = self._match_vertices_by_projection(base_tri, tri, n)
                    if perm is None:
                        perm = (0, 1, 2)
                    # Ensure base vertex labels exist
                    base_vertex_labels = []
                    for j in range(3):
                        pk = self._pos_key(base_tri[j])
                        base_vertex_labels.append(get_or_assign_coord_label(pk))
                    # Assign special labels to this triangle's vertices based on matching
                    for v_i in range(3):
                        base_j = perm[v_i]
                        derived = base_vertex_labels[base_j] + prime_suffix
                        special_label_by_pos[self._pos_key(tri[v_i])] = derived

            # Write triangle label above its vertices
            lines.append(lbl)
            # Write vertex lines
            tri_vertex_labels = []
            for v in range(3):
                pk = self._pos_key(tri[v])
                coord_lbl = get_or_assign_coord_label(pk)
                tri_vertex_labels.append(coord_lbl)
                x, y, z = tri[v]
                lines.append(f"{self._fmt_num(x)} {self._fmt_num(y)} {self._fmt_num(z)} {coord_lbl}")
            # Edge lengths (use the same vertex labels we just emitted)
            try:
                a, b, c = tri_vertex_labels[0], tri_vertex_labels[1], tri_vertex_labels[2]
                ab = float(np.linalg.norm(tri[1] - tri[0]))
                bc = float(np.linalg.norm(tri[2] - tri[1]))
                ca = float(np.linalg.norm(tri[0] - tri[2]))
                lines.append(
                    f"{a}-{b} len {self._fmt_num(ab)}, {b}-{c} len {self._fmt_num(bc)}, {c}-{a} len {self._fmt_num(ca)}"
                )
            except Exception:
                pass
            lines.append("")  # blank line per triangle

        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

        try:
            game.set_status(f"Wrote analysis file: {out_path}", 240)
        except Exception:
            pass
        return out_path



