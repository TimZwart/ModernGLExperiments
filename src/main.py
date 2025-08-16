import pygame
import sys
import os
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
    # Resolve default vertex file relative to project root (parent of this file's directory)
    this_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(this_dir)
    vertex_file = os.path.join(project_root, "assets", "bom.vertices")
    if len(sys.argv) > 1:
        vertex_file = sys.argv[1]
    verticesHolder.vertices = load_vertices(vertex_file)
    print(f"Loaded vertices from {vertex_file}: count={(len(verticesHolder.vertices)//6)}")
    game = Game(width, height, initial_filename=vertex_file)
    game.run()

