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

