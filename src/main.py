import pygame
import sys
import os
from src.geometry.VerticesHolder import verticesHolder
from game import Game
from src.renderer.UIOverlayCreator import UIOverlayCreator
from src.renderer.Renderer import Renderer
from src.geometry.loader import load_vertices
from src.camera.Camera import Camera
from src.configuration.session_store import get_last_file, set_last_file
from src.configuration import loadconfig  # Ensure config is initialized and console verbosity applied
if __name__ == '__main__':
    width, height = 800, 600
    pygame.init()
    pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF)
    # Resolve file to open: CLI arg > last opened > default
    this_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(this_dir)
    default_file = os.path.join(project_root, "assets", "bom.vertices")
    last_file = get_last_file()
    vertex_file = None
    if len(sys.argv) > 1:
        vertex_file = sys.argv[1]
    elif last_file:
        vertex_file = last_file
    else:
        vertex_file = default_file
    verticesHolder.vertices = load_vertices(vertex_file)
    print(f"Loaded vertices from {vertex_file}: count={(len(verticesHolder.vertices)//6)}")
    game = Game(width, height, initial_filename=vertex_file)
    # Persist the current file path at startup
    try:
        set_last_file(vertex_file)
    except Exception:
        pass
    game.run()

