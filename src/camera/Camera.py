import numpy as np
import math

class Camera:
    def __init__(self):
        self.eye = (4, 3, 2)
        self.look_at = (0, 0, 0)
        self.up = (0, 1, 0)

    def forward(self):
        x, y, z = self.eye
        x+=1
        self.eye = (x, y, z)
        lx, ly, lz = self.look_at
        lx += 1
        self.look_at = (lx, ly, lz)

    def backward(self):
        x, y, z = self.eye
        x-=1
        self.eye = (x, y, z)
        lx, ly, lz = self.look_at
        lx -= 1
        self.look_at = (lx, ly, lz)

    def left(self):
        x, y, z = self.eye
        z+=1
        self.eye = (x, y, z)
        lx, ly, lz = self.look_at
        lz += 1
        self.look_at = (lx, ly, lz)

    def right(self):
        x, y, z = self.eye
        z-=1
        self.eye = (x, y, z)
        lx, ly, lz = self.look_at
        lz -= 1
        self.look_at = (lx, ly, lz)

    def upwards(self):
        x, y, z = self.eye
        y+=1
        self.eye = (x, y, z)
        lx, ly, lz = self.look_at
        ly += 1
        self.look_at = (lx, ly, lz)

    def downwards(self):
        x, y, z = self.eye
        y-=1
        self.eye = (x, y, z)
        lx, ly, lz = self.look_at
        ly -= 1
        self.look_at = (lx, ly, lz)

    def rotate_vector(self, vec, axis, angle):
        axis = axis / np.linalg.norm(axis)
        cos = math.cos(angle)
        sin = math.sin(angle)
        dot = np.dot(axis, vec)
        cross = np.cross(axis, vec)
        return cos * vec + sin * cross + (1 - cos) * dot * axis

    def yaw(self, angle):
        dir = np.array(self.look_at) - np.array(self.eye)
        axis = np.array([0, 1, 0])
        new_dir = self.rotate_vector(dir, axis, angle)
        self.look_at = tuple(np.array(self.eye) + new_dir)

    def pitch(self, angle):
        dir = np.array(self.look_at) - np.array(self.eye)
        right = np.cross(dir, np.array([0, 1, 0]))
        right = right / np.linalg.norm(right)
        new_dir = self.rotate_vector(dir, right, angle)
        self.look_at = tuple(np.array(self.eye) + new_dir)

    def relative_forward(self, speed=1):
        dir = np.array(self.look_at) - np.array(self.eye)
        dir = dir / np.linalg.norm(dir)
        self.eye = tuple(np.array(self.eye) + dir * speed)
        self.look_at = tuple(np.array(self.look_at) + dir * speed)

    def relative_backward(self, speed=1):
        dir = np.array(self.look_at) - np.array(self.eye)
        dir = dir / np.linalg.norm(dir)
        self.eye = tuple(np.array(self.eye) - dir * speed)
        self.look_at = tuple(np.array(self.look_at) - dir * speed)

    def relative_right(self, speed=1):
        dir = np.array(self.look_at) - np.array(self.eye)
        dir = dir / np.linalg.norm(dir)
        right = np.cross(dir, np.array(self.up))
        right = right / np.linalg.norm(right)
        self.eye = tuple(np.array(self.eye) + right * speed)
        self.look_at = tuple(np.array(self.look_at) + right * speed)

    def relative_left(self, speed=1):
        dir = np.array(self.look_at) - np.array(self.eye)
        dir = dir / np.linalg.norm(dir)
        right = np.cross(dir, np.array(self.up))
        right = right / np.linalg.norm(right)
        self.eye = tuple(np.array(self.eye) - right * speed)
        self.look_at = tuple(np.array(self.look_at) - right * speed)

    def relative_upwards(self, speed=1):
        up = np.array(self.up) / np.linalg.norm(self.up)
        self.eye = tuple(np.array(self.eye) + up * speed)
        self.look_at = tuple(np.array(self.look_at) + up * speed)

    def relative_downwards(self, speed=1):
        up = np.array(self.up) / np.linalg.norm(self.up)
        self.eye = tuple(np.array(self.eye) - up * speed)
        self.look_at = tuple(np.array(self.look_at) - up * speed)

