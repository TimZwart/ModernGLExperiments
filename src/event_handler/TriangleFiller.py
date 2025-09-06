from src.geometry.VerticesHolder import verticesHolder
import itertools
import numpy as np

class TriangleFiller:
    def __init__(self, game):
        self.game = game
        self.ensure_outward = False

    def form_triangles_from_selected(self):
        if len(self.game.selected_vertices) < 3:
            return

        self.game.yellow_highlights.clear()

        selected = sorted(list(self.game.selected_vertices))
        # make it a two dimensional array [[x, y, z, r, g, b]]
        vertices = verticesHolder.vertices.reshape(-1, 6)

        selected = self.ensure_vertices_are_not_selected_more_than_once(vertices, selected)

        existing_triangles = self.compute_existing_triangles(vertices)

        new_triangles = []
        duplicate_triangle_indices = []
        for comb in itertools.combinations(selected, 3):
            pos = [tuple(vertices[i, :3]) for i in comb]
            # Skip degenerate triangles caused by duplicate positions
            pos_set = set(pos)
            if len(pos_set) < 3:
                continue
            # Skip near-zero-area triangles (collinear points)
            p0 = np.array(pos[0], dtype=float)
            p1 = np.array(pos[1], dtype=float)
            p2 = np.array(pos[2], dtype=float)
            if np.linalg.norm(np.cross(p1 - p0, p2 - p0)) < 1e-8:
                continue
            if pos_set not in existing_triangles:
                new_triangles.append(pos)
            else:
                t = existing_triangles.index(pos_set)
                duplicate_triangle_indices.append(t)

        self.highlight_duplicates(duplicate_triangle_indices)
        
        # Object-centric orientation: outward is away from object bounding-box center
        object_center = self.compute_object_center(verticesHolder.vertices)

        new_data = []
        flipped_count = 0
        for tri_pos in new_triangles:
            # Ensure outward orientation by flipping winding if needed
            if self.ensure_outward and not self.is_outward(tri_pos[0], tri_pos[1], tri_pos[2], object_center):
                tri_pos = [tri_pos[0], tri_pos[2], tri_pos[1]]
                flipped_count += 1
            new_color = self.game.random_color()
            for pos in tri_pos:
                new_data.extend(pos)
                new_data.extend(new_color)

        if new_data:
            verticesHolder.vertices = np.append(verticesHolder.vertices, new_data).astype('f4')
            self.game.renderer.renderer3D.update_vertex_buffer() 
        if flipped_count:
            print(f"Flipped winding for {flipped_count} triangle(s) during fill to face outward.")

    def highlight_duplicates(self,duplicate_triangle_indices:list):
        if duplicate_triangle_indices:
            highlighted_vertices = set()
            for t in duplicate_triangle_indices:
                highlighted_vertices.update([t*3, t*3+1, t*3+2])
            self.game.yellow_highlights = highlighted_vertices

            min_vertex = min(highlighted_vertices)
            self.game.uiOverlayCreator.scroll_offset = min_vertex

        # Deduplicate selection by position (rounded) to avoid creating degenerate triangles
    def round_triplet(self, p):
        return (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))

    def ensure_vertices_are_not_selected_more_than_once(self, vertices, selected):
        unique_map = {}
        for i in selected:
            key = self.round_triplet(vertices[i, :3])
            if key not in unique_map:
                unique_map[key] = i
        selected = sorted(unique_map.values())
        return selected

    def compute_existing_triangles(self, vertices):
        existing_triangles = []
        num_tri = len(vertices) // 3
        for t in range(num_tri):
            tri_pos = set(tuple(vertices[t*3 + i, :3]) for i in range(3))
            existing_triangles.append(tri_pos)
        return existing_triangles
        
    def compute_object_center(self, vertices):
        all_positions = vertices.reshape(-1, 6)[:, :3]
        if len(all_positions) > 0:
            mins = np.min(all_positions, axis=0)
            maxs = np.max(all_positions, axis=0)
            object_center = (mins + maxs) * 0.5
        else:
            object_center = np.array([0.0, 0.0, 0.0])
        return object_center

    def is_outward(self, p0, p1, p2, object_center):
        p0 = np.array(p0, dtype=float)
        p1 = np.array(p1, dtype=float)
        p2 = np.array(p2, dtype=float)
        normal = np.cross(p1 - p0, p2 - p0)
        norm_len = np.linalg.norm(normal)
        if norm_len == 0:
            return False
        tri_center = (p0 + p1 + p2) / 3.0
        from_object_center = tri_center - object_center
        dot = float(np.dot(normal, from_object_center))
        # Tolerance to avoid flipping near-zero ambiguous cases
        eps = 1e-8 * (np.linalg.norm(from_object_center) * norm_len + 1.0)
        return dot >= -eps
 