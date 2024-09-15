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
        print("Camera position:", self.camera.eye)
        print("Look at position:", self.camera.look_at)
        print("Up vector:", self.camera.up)
        
        print("World coordinates:")
        for i, coord in enumerate(world_coords):
            print(f"Vertex {i}: {coord}")
        
        print("\nMVP matrix:")
        print(mvp)
        
        clip_coords = np.dot(np.column_stack((world_coords, np.ones(world_coords.shape[0]))), np.array(mvp))
        
        print("\nClip coordinates:")
        for i, coord in enumerate(clip_coords):
            print(f"Vertex {i}: {coord}")
        
        # Check clip space coordinates
        assert np.all(np.abs(clip_coords[:, :3]) <= np.abs(clip_coords[:, 3:4])), "Clip space coordinates are outside the canonical view volume"
        
        # Perform perspective division
        ndc_coords = clip_coords[:, :3] / clip_coords[:, 3:]
        
        # Check NDC coordinates
        assert np.all(np.abs(ndc_coords) <= 1), "NDC coordinates are outside the [-1, 1] range"
        
        # Convert NDC to screen coordinates
        screen_coords = np.column_stack((
            (ndc_coords[:, 0] + 1) * 0.5 * self.width,
            (1 - ndc_coords[:, 1]) * 0.5 * self.height
        ))
        
        # Check screen coordinates
        assert np.all(screen_coords >= 0) and np.all(screen_coords[:, 0] <= self.width) and np.all(screen_coords[:, 1] <= self.height), "Screen coordinates are outside the screen boundaries"
        
        print(f"World coordinates shape: {world_coords.shape}")
        print(f"Screen coordinates shape: {screen_coords.shape}")
        print(f"Clip coordinate ranges: X ({clip_coords[:, 0].min():.2f}, {clip_coords[:, 0].max():.2f}), Y ({clip_coords[:, 1].min():.2f}, {clip_coords[:, 1].max():.2f}), Z ({clip_coords[:, 2].min():.2f}, {clip_coords[:, 2].max():.2f}), W ({clip_coords[:, 3].min():.2f}, {clip_coords[:, 3].max():.2f})")
        print(f"NDC coordinate ranges: X ({ndc_coords[:, 0].min():.2f}, {ndc_coords[:, 0].max():.2f}), Y ({ndc_coords[:, 1].min():.2f}, {ndc_coords[:, 1].max():.2f}), Z ({ndc_coords[:, 2].min():.2f}, {ndc_coords[:, 2].max():.2f})")
        print(f"Screen coordinate ranges: X ({screen_coords[:, 0].min():.2f}, {screen_coords[:, 0].max():.2f}), Y ({screen_coords[:, 1].min():.2f}, {screen_coords[:, 1].max():.2f})")
        
        return screen_coords
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