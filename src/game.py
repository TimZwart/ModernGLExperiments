import sys
import pygame
from src.renderer.Renderer3D import Renderer3D
from src.geometry.loader import load_vertices
from src.geometry.VerticesHolder import verticesHolder
class Game:
    def __init__(self, renderer: Renderer3D):
        self.renderer = renderer
        self.width, self.height = renderer.width, renderer.height
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

    def render(self):
        # Clear the overlay
        self.overlay.fill((0, 0, 0, 0))
        
        # Render text on the overlay
        font = pygame.font.Font(None, 24)
        debug_text = font.render(f"Vertices count: {len(verticesHolder.vertices)}", True, (255, 0, 0))
        self.overlay.blit(debug_text, (10, 10))
        
        vertices_text = [font.render(f"Vertex {i}: {verticesHolder.vertices[i*6:i*6+3]}", True, (255, 255, 255)) for i in range(min(20, len(verticesHolder.vertices) // 6))]
        for i, text in enumerate(vertices_text):
            self.overlay.blit(text, (10, 40 + i * 30))
        
        print(f"Created overlay with size: {self.overlay.get_size()}")
        print(f"Number of text items rendered: {len(vertices_text) + 1}")
        
        # Update the text texture
        self.renderer.update_text_texture(self.overlay)
        
        # Render OpenGL content and text texture
        self.renderer.render()
        
        # Update the display
        pygame.display.flip()
        print("Display flipped")

    def run(self):
        running = True
        frame_count = 0
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            self.render()
            frame_count += 1
            if frame_count % 60 == 0:  # Print every 60 frames
                print(f"Rendered {frame_count} frames")
        pygame.quit()

if __name__ == '__main__':
    width, height = 800, 600
    pygame.init()
    pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF)
    vertex_file = None
    if len(sys.argv) > 1:
        vertex_file = sys.argv[1]
    verticesHolder.vertices = load_vertices(vertex_file)
    renderer = Renderer3D(width, height)
    game = Game(renderer)
    game.run()

