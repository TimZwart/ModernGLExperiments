import moderngl
import pygame
import numpy as np
class OverlayRenderer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.text_texture = None
        self.text_vao = None
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

    def render_text_texture(self):
        if self.text_texture is None or self.text_vao is None:
            print("Text texture or VAO is None, skipping text render")
            return

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

    def create_text_texture(self, surface):
        texture = self.ctx.texture(surface.get_size(), 4, pygame.image.tostring(surface, "RGBA", 1))
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        texture.swizzle = 'RGBA'  # Ensure correct channel order
        print(f"Created text texture with size: {surface.get_size()}, components: {texture.components}")
        return texture