from pyrr import Matrix44

class Camera:
    def __init__(self):
        self.eye = (4, 3, 2)
        self.look_at = (0, 0, 0)
        self.up = (0, 1, 0)

    def forward(self):
        x, y, z = self.eye
        x+=1
        self.eye = (x, y, z)

    def backward(self):
        x, y, z = self.eye
        x-=1
        self.eye = (x, y, z)

    def left(self):
        x, y, z = self.eye
        z+=1
        self.eye = (x, y, z)

    def right(self):
        x, y, z = self.eye
        z-=1
        self.eye = (x, y, z)

    def up(self):
        x, y, z = self.eye
        y+=1
        self.eye = (x, y, z)

    def down(self):
        x, y, z = self.eye
        y-=1
        self.eye = (x, y, z)

