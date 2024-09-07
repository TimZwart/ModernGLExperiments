import moderngl
import pygame
from pyrr import Matrix44
import sys
from src.configuration.loadconfig import rotate_object
from src.geometry.loader import load_vertices


class Renderer3D:
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

        vertices = load_vertices(vertex_file)

        self.vbo = self.ctx.buffer(vertices)
        self.vao = self.ctx.simple_vertex_array(self.prog, self.vbo, 'in_vert', 'in_color')

        self.mvp = self.prog['mvp']
        
        self.width = width
        self.height = height

    def get_mvp_matrix(self, time):
        proj = Matrix44.perspective_projection(45.0, self.width / self.height, 0.1, 100.0)
        view = Matrix44.look_at(
            (4, 3, 2),  # eye
            (0, 0, 0),  # target
            (0, 1, 0),  # up
        )
        if rotate_object:
            model = Matrix44.from_eulers((0, time * 0.5, 0))
            final_matrix = proj * view * model
        else:
            final_matrix = proj * view
        return (final_matrix).astype('f4')

    def render(self):
        self.ctx.clear(0.2, 0.3, 0.3)
        self.mvp.write(self.get_mvp_matrix(pygame.time.get_ticks() * 0.001))
        self.vao.render(moderngl.TRIANGLE_STRIP)
        pygame.display.flip()



