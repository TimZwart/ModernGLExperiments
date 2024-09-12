import moderngl
from src.renderer.Renderer3D import Renderer3D
from src.renderer.TextRenderer import TextRenderer
import pygame
from src.camera.Camera import Camera

from src.renderer.UIOverlayCreator import UIOverlayCreator


class Renderer:
    def __init__(self, width, height, uiOverlayCreator: UIOverlayCreator, camera: Camera):
        self.ctx = moderngl.create_context()
        self.renderer3D : Renderer3D = Renderer3D(self.ctx, width, height, camera)
        self.uiOverlayCreator = uiOverlayCreator
        self.text_renderer : TextRenderer = TextRenderer(self.ctx)

    def render(self):
        self.uiOverlayCreator.draw_ui_overlay()
        self.text_renderer.update_text_texture(self.uiOverlayCreator.overlay)

        self.ctx.clear(0.2, 0.3, 0.3)
        self.renderer3D.render3D()
        self.text_renderer.render_text_texture()
        pygame.display.flip()
