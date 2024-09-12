import numpy as np
from moderngl import Context, TRIANGLE_STRIP, TRIANGLES
import pygame
from pyrr import Matrix44

from src.configuration.loadconfig import rotate_object
from src.geometry.VerticesHolder import verticesHolder
from src.camera.Camera import Camera


class Renderer3D:
    def __init__(self, ctx:Context, width, height, camera: Camera):
        self.prog = ctx.program(
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
        self.vbo = ctx.buffer(reserve=10000)
        self.update_vertex_buffer()
        self.vao = ctx.simple_vertex_array(self.prog, self.vbo, 'in_vert', 'in_color')
        self.ctx = ctx
        self.mvp = self.prog['mvp']
        self.width = width
        self.height = height
        self.camera = camera

    def update_vertex_buffer(self):
        self.vbo.write(verticesHolder.vertices)

    def world_to_screen(self, world_coords):
        mvp = self.get_mvp_matrix(pygame.time.get_ticks() * 0.001)
        clip_coords = np.dot(np.column_stack((world_coords, np.ones(world_coords.shape[0]))), mvp.T)
        ndc_coords = clip_coords[:, :3] / clip_coords[:, 3:]
        screen_coords = (ndc_coords[:, :2] + 1) * 0.5 * np.array([self.width, self.height])
        return screen_coords
    def render3D(self):
        self.mvp.write(self.get_mvp_matrix(pygame.time.get_ticks() * 0.001))
        self.vao.render(TRIANGLES)
        if self.ctx.error != 'GL_NO_ERROR':
            print("OpenGL error:")
            print(self.ctx.error)
            exit(1)

    def get_mvp_matrix(self, time):
        proj = Matrix44.perspective_projection(45.0, self.width / self.height, 0.1, 100.0)
        view = Matrix44.look_at(
            self.camera.eye,  # eye
            self.camera.look_at,  # target
            self.camera.up,  # up
        )
        if rotate_object:
            model = Matrix44.from_eulers((0, time * 0.5, 0))
            final_matrix = proj * view * model
        else:
            final_matrix = proj * view
        return (final_matrix).astype('f4')