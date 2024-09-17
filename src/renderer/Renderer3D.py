import numpy as np
from moderngl import Context, TRIANGLE_STRIP, TRIANGLES
import pygame
from pyrr import Matrix44

from src.configuration.loadconfig import rotate_object
from src.geometry.VerticesHolder import verticesHolder
from src.camera.Camera import Camera
from src.geometry.WorldScreenSpaceConverter import WorldScreenSpaceConverter


class Renderer3D:
    def __init__(self, ctx:Context, width, height, camera: Camera):
        self.prog = ctx.program(
            vertex_shader=self.load_shader('src/shaders/vertex_shader.glsl'),
            fragment_shader=self.load_shader('src/shaders/fragment_shader.glsl')
        )
        self.vbo = ctx.buffer(reserve=10000)
        self.update_vertex_buffer()
        self.vao = ctx.simple_vertex_array(self.prog, self.vbo, 'in_vert', 'in_color')
        self.ctx = ctx
        self.width = width
        self.height = height
        self.camera = camera

        # Initialize uniform locations, checking if they exist
        self.mvp = self.prog['mvp']
        self.model = self.prog['model'] if 'model' in self.prog else None
        self.eye_position = self.prog['eye_position'] if 'eye_position' in self.prog else None

    def load_shader(self, shader_path):
        with open(shader_path, 'r') as shader_file:
            return shader_file.read()

    def update_vertex_buffer(self):
        self.vbo.write(verticesHolder.vertices)

    def world_to_screen(self, world_coords):
        mvp = self.get_mvp_matrix(pygame.time.get_ticks() * 0.001)
        converter:WorldScreenSpaceConverter = WorldScreenSpaceConverter(mvp, self.width, self.height, mvp, world_coords, self.camera)
        return converter.compute()

    def render3D(self):
        time = pygame.time.get_ticks() * 0.001
        mvp_matrix = self.get_mvp_matrix(time)
        self.mvp.write(mvp_matrix)
        
        if self.model is not None:
            model_matrix = self.get_model_matrix(time)
            self.model.write(model_matrix)
        
        if self.eye_position is not None:
            # Convert the eye position to a numpy array and then to float32
            eye_pos = np.array(self.camera.eye, dtype='f4')
            self.eye_position.write(eye_pos)
        
        self.vao.render(TRIANGLES)
        if self.ctx.error != 'GL_NO_ERROR':
            print("OpenGL error:")
            print(self.ctx.error)
            exit(1)

    def get_model_matrix(self, time):
        if rotate_object:
            return Matrix44.from_eulers((0, time * 0.5, 0)).astype('f4')
        else:
            return Matrix44.identity().astype('f4')

    def get_mvp_matrix(self, time):
        model = self.get_model_matrix(time)
        view = Matrix44.look_at(
            self.camera.eye,
            self.camera.look_at,
            self.camera.up,
        )
        proj = Matrix44.perspective_projection(45.0, self.width / self.height, 0.1, 100.0)
        return (proj * view * model).astype('f4')