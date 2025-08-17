import numpy as np
import os


def load_vertices_from_file(filename):
    vertices = []
    try:
        with open(filename, 'r') as file:
            for line in file:
                # Assuming each line has 6 values: x, y, z, r, g, b
                values = list(map(float, line.strip().split()))
                if len(values) == 6:
                    vertices.extend(values)
                else:
                    print(f"Warning: Skipping invalid line in {filename}: {line.strip()}")
    except FileNotFoundError:
        print(f"File not found: {filename}. Starting with empty vertices.")
        return np.array([], dtype='f4')
    except Exception as e:
        print(f"Error reading {filename}: {e}. Starting with empty vertices.")
        return np.array([], dtype='f4')
    return np.array(vertices, dtype='f4')


def load_vertices(vertex_file):
    # Load vertices from file if provided, otherwise use default sample
    if vertex_file:
        return load_vertices_from_file(vertex_file)
    return np.array([
        # x, y, z, r, g, b
        -1.0, -1.0, -1.0, 1.0, 0.0, 0.0,
        1.0, -1.0, -1.0, 0.0, 1.0, 0.0,
        0.0, 1.0, -1.0, 0.0, 0.0, 1.0,
        0.0, 0.0, 1.0, 1.0, 1.0, 1.0,
    ], dtype='f4')