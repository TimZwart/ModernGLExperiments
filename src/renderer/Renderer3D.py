import moderngl
import pygame
from pyrr import Matrix44
import numpy as np
from src.configuration.loadconfig import rotate_object
from src.geometry.loader import load_vertices
from src.geometry.VerticesHolder import verticesHolder



class Renderer3D:
    def __init__(self, width, height):
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


        self.vbo = self.ctx.buffer(verticesHolder.vertices)
        self.vao = self.ctx.simple_vertex_array(self.prog, self.vbo, 'in_vert', 'in_color')

        self.mvp = self.prog['mvp']
        
        self.width = width
        self.height = height

        # Add these lines for text rendering
        self.text_prog = self.ctx.program(
            vertex_shader='''
                #version 330
                in vec2 in_vert;
                in vec2 in_texcoord;
                out vec2 v_texcoord;
                void main() {
                    gl_Position = vec4(in_vert, 0.0, 1.0);
                    v_texcoord = in_texcoord;
                }
            ''',
            fragment_shader='''
                #version 330
                uniform sampler2D texture0;
                in vec2 v_texcoord;
                out vec4 f_color;
                void main() {
                    f_color = texture(texture0, v_texcoord);
                }
            '''
        )
        self.text_texture = None
        self.text_vao = None

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

    def create_text_texture(self, surface):
        texture = self.ctx.texture(surface.get_size(), 4, pygame.image.tostring(surface, "RGBA", 1))
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        texture.swizzle = 'RGBA'  # Ensure correct channel order
        print(f"Created text texture with size: {surface.get_size()}, components: {texture.components}")
        return texture

    def render_text_texture(self):
        if self.text_texture is None or self.text_vao is None:
            print("Text texture or VAO is None, skipping text render")
            return

        print("Rendering text texture")
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.ctx.blend_equation = moderngl.FUNC_ADD
        self.text_texture.use(0)
        self.text_vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.disable(moderngl.BLEND)

    def update_text_texture(self, surface):
        pygame.image.save(surface, "text_texture.png")
        if self.text_texture is None:
            self.text_texture = self.create_text_texture(surface)
        else:
            self.text_texture.write(pygame.image.tostring(surface, "RGBA", 1))

        if self.text_vao is None:
            vertices = np.array([
                -1.0, 1.0, 0.0, 1.0,
                1.0, 1.0, 1.0, 1.0,
                -1.0, -1.0, 0.0, 0.0,
                1.0, -1.0, 1.0, 0.0,
            ], dtype='f4')
            self.text_vbo = self.ctx.buffer(vertices)
            self.text_vao = self.ctx.simple_vertex_array(self.text_prog, self.text_vbo, 'in_vert', 'in_texcoord')

    def render(self):
        self.ctx.clear(0.2, 0.3, 0.3)
        self.mvp.write(self.get_mvp_matrix(pygame.time.get_ticks() * 0.001))
        self.vao.render(moderngl.TRIANGLE_STRIP)
        self.render_text_texture()



