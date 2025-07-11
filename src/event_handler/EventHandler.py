import pygame
from src.geometry.VerticesHolder import verticesHolder

class EventHandler:
    def __init__(self, game):
        self.game = game

    def handle_events(self):
        continue_running = True
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                continue_running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    x, y = event.pos
                    if self.game.filename_rect and self.game.filename_rect.collidepoint(x, y):
                        self.game.filename_edit_mode = True
                    elif self.game.edit_rect and self.game.edit_rect.collidepoint(x, y) and self.game.selected_vertex is not None:
                        self.game.edit_mode = True
                        self.game.edit_text = f"{list(verticesHolder.vertices[self.game.selected_vertex*6:self.game.selected_vertex*6+3])}"
                    elif self.game.handle_vertex_list_click(x, y):
                        pass # Vertex in the list was clicked, no need to do anything else
                    else:
                        nearest_vertex = self.game.find_nearest_vertex(x, y)
                        if nearest_vertex is not None:
                            self.game.selected_vertex = nearest_vertex
                            self.game.edit_mode = False
                            self.game.edit_text = ""
                        else:
                            print("No vertex nearby")
            elif event.type == pygame.KEYDOWN:
                if self.game.filename_edit_mode:
                    if event.key == pygame.K_RETURN:
                        self.game.apply_filename_edit()
                    elif event.key == pygame.K_BACKSPACE:
                        self.game.filename_text = self.game.filename_text[:-1]
                    else:
                        self.game.filename_text += event.unicode
                elif self.game.edit_mode:
                    if event.key == pygame.K_RETURN:
                        self.game.apply_edit()
                    elif event.key == pygame.K_BACKSPACE:
                        self.game.edit_text = self.game.edit_text[:-1]
                    else:
                        self.game.edit_text += event.unicode
                elif event.key == pygame.K_p:  # 'P' key to add a vertex
                    self.game.add_vertex(0.0, 0.0, 0.0)  # Add a vertex at (0, 0, 0)
                elif event.key == pygame.K_o:  # 'O' key to save vertices
                    self.game.save_vertices()
                elif event.key == pygame.K_c:  # 'C' key to change filename
                    self.game.filename_edit_mode = True
                elif event.key == pygame.K_w:
                    self.game.camera.forward()
                elif event.key == pygame.K_s:
                    self.game.camera.backward()
                elif event.key == pygame.K_a:
                    self.game.camera.left()
                elif event.key == pygame.K_d:
                    self.game.camera.right()
                elif event.key == pygame.K_q:
                    self.game.camera.upwards()
                elif event.key == pygame.K_e:
                    self.game.camera.downwards()
            elif event.type == pygame.MOUSEWHEEL:
                self.game.handle_scroll(event.y)
        
        return continue_running 