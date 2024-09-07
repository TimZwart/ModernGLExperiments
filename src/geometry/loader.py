import numpy as np


def load_vertices_from_file(filename):
    vertices = []
    with open(filename, 'r') as file:
        for line in file:
            # Assuming each line has 6 values: x, y, z, r, g, b
            values = list(map(float, line.strip().split()))
            if len(values) == 6:
                vertices.extend(values)
            else:
                print(f"Warning: Skipping invalid line in {filename}: {line.strip()}")
    return np.array(vertices, dtype='f4')


def load_vertices(vertex_file):
    # Load vertices from file if provided, otherwise use default
    if vertex_file:
        vertices = load_vertices_from_file(vertex_file)
    else:
        vertices = np.array([
            # x, y, z, r, g, b
            -1.0, -1.0, -1.0, 1.0, 0.0, 0.0,
            1.0, -1.0, -1.0, 0.0, 1.0, 0.0,
            0.0, 1.0, -1.0, 0.0, 0.0, 1.0,
            0.0, 0.0, 1.0, 1.0, 1.0, 1.0,
        ], dtype='f4')
    return vertices