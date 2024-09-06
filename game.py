import moderngl
import moderngl_window as mglw
import numpy as np
from pyrr import Matrix44

class BasicWindow(mglw.WindowConfig):
    gl_version = (3, 3)
    window_size = (800, 600)
    title = "ModernGL 3D Setup"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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

        # Define vertices in 3D space
        vertices = np.array([
            # x, y, z, r, g, b
            -1.0, -1.0, -1.0, 1.0, 0.0, 0.0,  # red
             1.0, -1.0, -1.0, 0.0, 1.0, 0.0,  # green
             0.0,  1.0, -1.0, 0.0, 0.0, 1.0,  # blue
             0.0,  0.0,  1.0, 1.0, 1.0, 1.0,  # white
        ], dtype='f4')

        self.vbo = self.ctx.buffer(vertices)
        self.vao = self.ctx.simple_vertex_array(self.prog, self.vbo, 'in_vert', 'in_color')

        # Create and set up the MVP matrix
        self.mvp = self.prog['mvp']
        self.mvp.write(self.get_mvp_matrix())

    def get_mvp_matrix(self):
        proj = Matrix44.perspective_projection(45.0, self.aspect_ratio, 0.1, 100.0)
        view = Matrix44.look_at(
            (4, 3, 2),  # eye
            (0, 0, 0),  # target
            (0, 1, 0),  # up
        )
        import time
        model = Matrix44.from_eulers((0, time.time() * 0.5, 0))
        return (proj * view * model).astype('f4')

    def render(self, time, frame_time):
        self.ctx.clear(0.2, 0.3, 0.3)
        self.mvp.write(self.get_mvp_matrix())
        self.vao.render(moderngl.TRIANGLE_STRIP)

if __name__ == '__main__':
    mglw.run_window_config(BasicWindow)