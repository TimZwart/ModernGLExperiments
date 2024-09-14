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
        mvp = self.get_mvp_matrix(pygame.time.get_ticks() * 0.001, debug=True)
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
        mvp_matrix = self.get_mvp_matrix(pygame.time.get_ticks() * 0.001)
        print("MVP matrix in render3D:")
        print(mvp_matrix)
        self.mvp.write(mvp_matrix)
        self.vao.render(TRIANGLES)
        if self.ctx.error != 'GL_NO_ERROR':
            print("OpenGL error:")
            print(self.ctx.error)
            exit(1)

    def get_mvp_matrix(self, time, debug=False):
        proj = Matrix44.perspective_projection(45.0, self.width / self.height, 0.1, 100.0)
        assert isinstance(proj, Matrix44), "Projection matrix is not a Matrix44 object"
        if debug:
            print("Projection matrix:")
            print(proj)
        view = Matrix44.look_at(
            self.camera.eye,  # eye
            self.camera.look_at,  # target
            self.camera.up,  # up
        )
        assert isinstance(view, Matrix44), "View matrix is not a Matrix44 object"
        if debug:
            print("View matrix:")
            print(view)
        if rotate_object:
            model = Matrix44.from_eulers((0, time * 0.5, 0))
            assert isinstance(model, Matrix44), "Model matrix is not a Matrix44 object"
            if debug:
                print("Model matrix:")
                print(model)
            final_matrix = proj * view * model
        else:
            final_matrix = proj * view
        assert isinstance(final_matrix, Matrix44), "Final MVP matrix is not a Matrix44 object"
        return final_matrix.astype('f4')