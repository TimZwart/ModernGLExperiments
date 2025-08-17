import sys
import pygame
from src.geometry.VerticesHolder import verticesHolder
import numpy as np
from src.camera.Camera import Camera
import random
from src.configuration.loadconfig import relative_movement

class Game:
    def __init__(self, width: int, height: int, initial_filename: str = None):
        self.width, self.height = width, height
        self.relative_movement = relative_movement
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.selected_vertices = set()
        self.edit_mode = False
        self.edit_text = ""
        self.edit_rect = pygame.Rect(10, self.height - 35, 290, 30)
        # Add-vertex editing variables
        self.add_vertex_mode = False
        self.add_vertex_text = ""
        self.add_vertex_rect = pygame.Rect(10, self.height - 105, 350, 30)
        self.add_vertex_error = ""
        # Filename editing variables
        self.filename_edit_mode = False
        self.filename_text = initial_filename or "assets/bom.vertices"
        self.filename_edit_purpose = 'save'
        self.filename_rect = pygame.Rect(10, self.height - 140, 350, 30)
        # Open file clickable area
        self.open_rect = pygame.Rect(10, self.height - 175, 350, 30)
        self.camera = Camera()
        from src.renderer.UIOverlayCreator import UIOverlayCreator
        self.uiOverlayCreator = UIOverlayCreator(width, height, self)
        from src.renderer.Renderer import Renderer
        self.renderer = Renderer(width, height, self.uiOverlayCreator, self.camera)
        initial_count = len(verticesHolder.vertices) // 6
        if initial_count > 0:
            if initial_count % 3 == 0:
                self.current_color = self.random_color()
            else:
                last_vertex = verticesHolder.vertices[-6:]
                self.current_color = last_vertex[3:6].tolist()
        else:
            self.current_color = self.random_color()
        self.scroll_speed = 3
        self.yellow_highlights = set()
        self.help_mode = False

        from src.event_handler import EventHandler
        self.event_handler = EventHandler(self)

    def random_color(self):
        return [random.random() for _ in range(3)]

    def run(self):
        running = True
        while running:
            running = self.event_handler.handle_events()
            self.renderer.render()
        pygame.quit()