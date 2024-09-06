import moderngl
import pygame
import numpy as np
from pyrr import Matrix44
import sys

class Game:
    def __init__(self, width, height, vertex_file=None):
        pygame.init()
        pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF)
        self.ctx = moderngl.create_context()
        
        self.prog = self.ctx.program(
            vertex_shader='''
                #version 330
                in vec3 in_vert;
                in vec3 in_color;
                out vec3 v_color;
                uniform mat4 mvp;
                void main() {
                    gl_Position = mvp * vec4(in_vert, 1.0);
                    v_color = in_color;
                }
            ''',
            fragment_shader='''
                #version 330
                in vec3 v_color;
                out vec4 f_color;
                void main() {
                    f_color = vec4(v_color, 1.0);
                }
            '''
        )

        # Load vertices from file if provided, otherwise use default
        if vertex_file:
            vertices = self.load_vertices_from_file(vertex_file)
        else:
            vertices = np.array([
                # x, y, z, r, g, b
                -1.0, -1.0, -1.0, 1.0, 0.0, 0.0,
                 1.0, -1.0, -1.0, 0.0, 1.0, 0.0,
                 0.0,  1.0, -1.0, 0.0, 0.0, 1.0,
                 0.0,  0.0,  1.0, 1.0, 1.0, 1.0,
            ], dtype='f4')

        self.vbo = self.ctx.buffer(vertices)
        self.vao = self.ctx.simple_vertex_array(self.prog, self.vbo, 'in_vert', 'in_color')

        self.mvp = self.prog['mvp']
        
        self.width = width
        self.height = height

    def load_vertices_from_file(self, filename):
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

    def get_mvp_matrix(self, time):
        proj = Matrix44.perspective_projection(45.0, self.width / self.height, 0.1, 100.0)
        view = Matrix44.look_at(
            (4, 3, 2),  # eye
            (0, 0, 0),  # target
            (0, 1, 0),  # up
        )
        model = Matrix44.from_eulers((0, time * 0.5, 0))
        return (proj * view * model).astype('f4')

    def render(self):
        self.ctx.clear(0.2, 0.3, 0.3)
        self.mvp.write(self.get_mvp_matrix(pygame.time.get_ticks() * 0.001))
        self.vao.render(moderngl.TRIANGLE_STRIP)
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            self.render()
        
        pygame.quit()

if __name__ == '__main__':
    width, height = 800, 600
    vertex_file = None
    if len(sys.argv) > 1:
        vertex_file = sys.argv[1]
    game = Game(width, height, vertex_file)
    game.run()