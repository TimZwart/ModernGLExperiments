import moderngl
import moderngl_window as mglw
import array

class BasicWindow(mglw.WindowConfig):
    gl_version = (3, 3)
    window_size = (800, 600)
    title = "ModernGL Basic Setup"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.prog = self.ctx.program(
            vertex_shader='''
                #version 330
                in vec2 in_vert;
                in vec3 in_color;
                out vec3 v_color;
                void main() {
                    gl_Position = vec4(in_vert, 0.0, 1.0);
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

        vertices = array.array('f', [
            -0.6, -0.6,  1.0, 0.0, 0.0,
             0.6, -0.6,  0.0, 1.0, 0.0,
             0.0,  0.6,  0.0, 0.0, 1.0,
             0.0,  0.6,  0.0, 0.0, 1.0,
             0.9,  0.9,  0.5, 0.5, 0.0,
             0.6, -0.6,  0.0, 1.0, 0.0
        ])
        self.vbo = self.ctx.buffer(vertices.tobytes())
        self.vao = self.ctx.simple_vertex_array(self.prog, self.vbo, 'in_vert', 'in_color')

    def render(self, time, frame_time):
        self.ctx.clear(0.2, 0.3, 0.3)
        self.vao.render(moderngl.TRIANGLES, 6)

if __name__ == '__main__':
    mglw.run_window_config(BasicWindow)