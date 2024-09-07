import sys
import pygame
from src.renderer.Renderer3D import Renderer3D
class Game:
    def __init__(self, renderer: Renderer3D):
        self.renderer = renderer

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            self.render()
        pygame.quit()

    def render(self):
        self.renderer.render()

if __name__ == '__main__':
    width, height = 800, 600
    vertex_file = None
    if len(sys.argv) > 1:
        vertex_file = sys.argv[1]
    renderer = Renderer3D(width, height, vertex_file)
    game = Game(renderer)
    game.run()

