import pygame
import sys
from src.geometry.VerticesHolder import verticesHolder
from game import Game
from src.renderer.UIOverlayCreator import UIOverlayCreator
from src.renderer.Renderer import Renderer
from src.geometry.loader import load_vertices
from src.camera.Camera import Camera
if __name__ == '__main__':
    width, height = 800, 600
    pygame.init()
    pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF)
    vertex_file = None
    if len(sys.argv) > 1:
        vertex_file = sys.argv[1]
    verticesHolder.vertices = load_vertices(vertex_file)
    camera = Camera()
    game = Game(width, height, camera)
    uiOverlayCreator = UIOverlayCreator(width, height, game)
    renderer = Renderer(width, height, uiOverlayCreator, camera)
    game.renderer = renderer
    game.run()

