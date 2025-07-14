import sys
import pygame
from src.geometry.VerticesHolder import verticesHolder
import numpy as np
from src.camera.Camera import Camera
import random
from src.configuration.loadconfig import relative_movement

class Game:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.relative_movement = relative_movement
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.selected_vertex = None  # Add this line
        self.edit_mode = False
        self.edit_text = ""
        self.edit_rect = pygame.Rect(10, self.height - 35, 290, 30)
        # Filename editing variables
        self.filename_edit_mode = False
        self.filename_text = "assets/scout.vertices"
        self.filename_rect = pygame.Rect(10, self.height - 140, 350, 30)
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
        self.scroll_speed = 3  # Number of vertices to scroll per mouse wheel event

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