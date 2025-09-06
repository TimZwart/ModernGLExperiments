import pygame
from src.event_handler.TriangleFiller import TriangleFiller
from src.geometry.VerticesHolder import verticesHolder
from src.geometry.loader import load_vertices_from_file
from src.configuration.session_store import set_last_file

import numpy as np
import itertools
from src.configuration.loadconfig import keybindings, mouse_rotation_button
import ast

class EventHandler:
    def __init__(self, game):
        self.game = game
        self.rotation_button = mouse_rotation_button
        self.mouse_button_rotation_held = False
        self.rotate_key_held = False
        self.triangle_filler = TriangleFiller(game)
        self.alternate_keys = {
            'forward': pygame.K_UP,
            'backward': pygame.K_DOWN,
            'left': pygame.K_LEFT,
            'right': pygame.K_RIGHT,
            'up': pygame.K_PAGEUP,
            'down': pygame.K_PAGEDOWN,
            'add_vertex': pygame.K_INSERT,
            'save_vertices': pygame.K_F5,
            'change_filename': pygame.K_F6,
            'new_file': pygame.K_F9,
            'form_triangles': pygame.K_F7,
            'open_file': pygame.K_F3,
            'remove_backfaces': pygame.K_F10,
            'yaw_left': pygame.K_KP4,
            'yaw_right': pygame.K_KP6,
            'pitch_up': pygame.K_KP8,
            'pitch_down': pygame.K_KP2,
            'toggle_wireframe': pygame.K_F8,
            'help': pygame.K_F1,
            'check_edge': pygame.K_F11,
            'remove_internal_edges': pygame.K_F12,
        }
        self.rotation_speed = 0.1

    def handle_events(self):
        continue_running = True
        for event in pygame.event.get():
            # Modal: Shapes input flows have precedence over other inputs except QUIT
            if getattr(self.game, 'shapes_mode', False) and getattr(self.game, 'shape_input_mode', None) is not None:
                if event.type == pygame.QUIT:
                    continue_running = False
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.apply_shape_step()
                        continue
                    elif event.key == pygame.K_BACKSPACE:
                        self.backspace_shape_text()
                        continue
                    else:
                        self.append_shape_text(event.unicode)
                        continue
                # Swallow all other events while in shape entry flow
                continue
            # While entering a new vertex's coordinates, disable all other controls except text entry and QUIT
            if self.game.add_vertex_mode:
                if event.type == pygame.QUIT:
                    continue_running = False
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.apply_add_vertex()
                    elif event.key == pygame.K_BACKSPACE:
                        self.game.add_vertex_text = self.game.add_vertex_text[:-1]
                        self.game.add_vertex_error = ""
                    else:
                        # Clear placeholder on first typed character
                        if self.game.add_vertex_text == "[0.0, 0.0, 0.0]":
                            self.game.add_vertex_text = ""
                        self.game.add_vertex_text += event.unicode
                        self.game.add_vertex_error = ""
                # Swallow all other events during add-vertex edit mode
                continue
            # While entering extrude offset, disable all other controls except text entry and QUIT
            if self.game.extrude_mode:
                if event.type == pygame.QUIT:
                    continue_running = False
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.apply_extrude()
                    elif event.key == pygame.K_BACKSPACE:
                        self.game.extrude_text = self.game.extrude_text[:-1]
                        self.game.extrude_error = ""
                    else:
                        # Clear placeholder on first typed character
                        if self.game.extrude_text == "[0.0, 0.0, 0.0]":
                            self.game.extrude_text = ""
                        self.game.extrude_text += event.unicode
                        self.game.extrude_error = ""
                continue
            # While editing the save filename, disable all other controls except text entry and QUIT
            if self.game.filename_edit_mode:
                if event.type == pygame.QUIT:
                    continue_running = False
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.apply_filename_edit()
                    elif event.key == pygame.K_BACKSPACE:
                        self.game.filename_text = self.game.filename_text[:-1]
                    else:
                        self.game.filename_text += event.unicode
                # Swallow all other events during filename edit mode
                continue
            if event.type == pygame.QUIT:
                continue_running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mods = pygame.key.get_mods()
                    ctrl_pressed = mods & pygame.KMOD_CTRL
                    x, y = event.pos
                    if self.game.add_vertex_rect and self.game.add_vertex_rect.collidepoint(x, y):
                        self.game.add_vertex_mode = True
                        # Prefill with last selected vertex coords if available
                        self.game.add_vertex_text = self._get_add_vertex_default_text()
                        self.game.add_vertex_error = ""
                        self.mouse_button_rotation_held = False
                        self.rotate_key_held = False
                    # Disable click activation for open/save/new; use keybindings only
                    elif self.game.filename_rect and self.game.filename_rect.collidepoint(x, y):
                        pass
                    elif self.game.extrude_rect and self.game.extrude_rect.collidepoint(x, y):
                        # Activate extrude input; default to last selected coords
                        if len(self.game.selected_vertices) == 0:
                            self.game.set_status("Select vertices to extrude", 180)
                        else:
                            self.game.extrude_mode = True
                            self.game.extrude_text = self._get_add_vertex_default_text()
                            self.game.extrude_error = ""
                            self.mouse_button_rotation_held = False
                            self.rotate_key_held = False
                    elif self.game.edit_rect and self.game.edit_rect.collidepoint(x, y) and len(self.game.selected_vertices) == 1:
                        self.game.edit_mode = True
                        selected = list(self.game.selected_vertices)[0]
                        self.game.edit_text = f"{list(verticesHolder.vertices[selected*6:selected*6+3])}"
                    elif self.handle_vertex_list_click(x, y, ctrl_pressed):
                        pass # Vertex in the list was clicked, no need to do anything else
                    else:
                        nearest_vertex = self.find_nearest_vertex(x, y)
                        if nearest_vertex is not None:
                            if ctrl_pressed:
                                if nearest_vertex in self.game.selected_vertices:
                                    self.game.selected_vertices.remove(nearest_vertex)
                                else:
                                    self.game.selected_vertices.add(nearest_vertex)
                            else:
                                self.game.selected_vertices = {nearest_vertex}
                            # Track the last vertex the user interacted with
                            self.game.last_selected_vertex_index = nearest_vertex
                        else:
                            if not ctrl_pressed:
                                self.game.selected_vertices.clear()
                        # After selection change, check if should enter edit_mode
                        if len(self.game.selected_vertices) == 1:
                            self.game.edit_mode = True
                            selected = list(self.game.selected_vertices)[0]
                            self.game.edit_text = f"{list(verticesHolder.vertices[selected*6:selected*6+3])}"
                        else:
                            self.game.edit_mode = False
                            self.game.edit_text = ""
                elif event.button == self.rotation_button:
                    self.mouse_button_rotation_held = True

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == self.rotation_button:
                    self.mouse_button_rotation_held = False

            elif event.type == pygame.MOUSEMOTION:
                if self.mouse_button_rotation_held or self.rotate_key_held:
                    dx, dy = event.rel
                    sensitivity = 0.005  # Adjust sensitivity as needed
                    self.game.camera.yaw(-dx * sensitivity)
                    self.game.camera.pitch(-dy * sensitivity)
            elif event.type == pygame.KEYUP:
                # Release rotation when the configured rotate key is released
                if 'rotate' in keybindings and event.key == pygame.key.key_code(keybindings['rotate']):
                    self.rotate_key_held = False
            elif event.type == pygame.KEYDOWN:
                # Toggle shapes mode irrespective of other modes except text editing ones handled above
                if event.key == pygame.key.key_code(keybindings.get('shapes_mode', 'm')):
                    self.toggle_shapes_mode()
                    continue
                if self.game.filename_edit_mode:
                    if event.key == pygame.K_RETURN:
                        self.apply_filename_edit()
                    elif event.key == pygame.K_BACKSPACE:
                        self.game.filename_text = self.game.filename_text[:-1]
                    else:
                        self.game.filename_text += event.unicode
                elif self.game.edit_mode:
                    if event.key == pygame.K_RETURN:
                        self.apply_edit()
                    elif event.key == pygame.K_BACKSPACE:
                        self.game.edit_text = self.game.edit_text[:-1]
                    else:
                        self.game.edit_text += event.unicode
                # Only allow deletion when not in any text-editing mode
                if not (self.game.filename_edit_mode or self.game.add_vertex_mode or self.game.edit_mode):
                    if event.key == pygame.K_DELETE:
                        self.delete_selected_vertices()
                    # Clear all vertices via configured key (e.g., X)
                    if 'clear_vertices' in keybindings and event.key == pygame.key.key_code(keybindings['clear_vertices']):
                        self.clear_all_vertices()
                # Press-and-hold keyboard rotate key acts like holding the mouse rotation button
                if 'rotate' in keybindings and event.key == pygame.key.key_code(keybindings['rotate']):
                    self.rotate_key_held = True
                # Shape entry hotkeys only active when shapes mode is enabled
                if getattr(self.game, 'shapes_mode', False):
                    if event.key == pygame.key.key_code(keybindings.get('shape_rectangle', 'r')):
                        self.start_rectangle_flow()
                        continue
                    if event.key == pygame.key.key_code(keybindings.get('shape_ngon', 'g')):
                        self.start_ngon_flow()
                        continue

                if event.key == pygame.key.key_code(keybindings['add_vertex']) or event.key == self.alternate_keys['add_vertex']:
                    # Enter add-vertex input mode; prefill from last selected when possible
                    self.game.add_vertex_mode = True
                    self.game.add_vertex_text = self._get_add_vertex_default_text()
                    self.game.add_vertex_error = ""
                    self.mouse_button_rotation_held = False
                    self.rotate_key_held = False
                if event.key == pygame.key.key_code(keybindings['save_vertices']) or event.key == self.alternate_keys['save_vertices']:
                    self.save_vertices()
                if (('extrude' in keybindings) and event.key == pygame.key.key_code(keybindings['extrude'])):
                    if len(self.game.selected_vertices) == 0:
                        self.game.set_status("Select vertices to extrude", 180)
                    else:
                        self.game.extrude_mode = True
                        self.game.extrude_text = self._get_add_vertex_default_text()
                        self.game.extrude_error = ""
                        self.mouse_button_rotation_held = False
                        self.rotate_key_held = False
                if event.key == pygame.key.key_code(keybindings['change_filename']) or event.key == self.alternate_keys['change_filename']:
                    self.game.filename_edit_mode = True
                    self.game.filename_edit_purpose = 'save'
                    self.mouse_button_rotation_held = False
                    self.rotate_key_held = False
                if (('new_file' in keybindings) and event.key == pygame.key.key_code(keybindings['new_file'])) or event.key == self.alternate_keys['new_file']:
                    self.game.filename_edit_mode = True
                    self.game.filename_edit_purpose = 'new'
                    self.mouse_button_rotation_held = False
                    self.rotate_key_held = False
                if (('open_file' in keybindings) and event.key == pygame.key.key_code(keybindings['open_file'])) or event.key == self.alternate_keys['open_file']:
                    self.game.filename_edit_mode = True
                    self.game.filename_edit_purpose = 'open'
                    self.mouse_button_rotation_held = False
                    self.rotate_key_held = False
                if event.key == pygame.key.key_code(keybindings['form_triangles']) or event.key == self.alternate_keys['form_triangles']:
                    self.triangle_filler.form_triangles_from_selected()
                if (('remove_backfaces' in keybindings) and event.key == pygame.key.key_code(keybindings['remove_backfaces'])) or event.key == self.alternate_keys['remove_backfaces']:
                    self.remove_backfacing_triangles()
                if event.key == pygame.key.key_code(keybindings['forward']) or event.key == self.alternate_keys['forward']:
                    if self.game.relative_movement:
                        self.game.camera.relative_forward()
                    else:
                        self.game.camera.forward()
                if event.key == pygame.key.key_code(keybindings['backward']) or event.key == self.alternate_keys['backward']:
                    if self.game.relative_movement:
                        self.game.camera.relative_backward()
                    else:
                        self.game.camera.backward()
                if event.key == pygame.key.key_code(keybindings['left']) or event.key == self.alternate_keys['left']:
                    if self.game.relative_movement:
                        self.game.camera.relative_left()
                    else:
                        self.game.camera.left()
                if event.key == pygame.key.key_code(keybindings['right']) or event.key == self.alternate_keys['right']:
                    if self.game.relative_movement:
                        self.game.camera.relative_right()
                    else:
                        self.game.camera.right()
                if event.key == pygame.key.key_code(keybindings['up']) or event.key == self.alternate_keys['up']:
                    if self.game.relative_movement:
                        self.game.camera.relative_upwards()
                    else:
                        self.game.camera.upwards()
                if event.key == pygame.key.key_code(keybindings['down']) or event.key == self.alternate_keys['down']:
                    if self.game.relative_movement:
                        self.game.camera.relative_downwards()
                    else:
                        self.game.camera.downwards()
                if event.key == pygame.key.key_code(keybindings['yaw_left']) or event.key == self.alternate_keys['yaw_left']:
                    self.game.camera.yaw(self.rotation_speed)
                if event.key == pygame.key.key_code(keybindings['yaw_right']) or event.key == self.alternate_keys['yaw_right']:
                    self.game.camera.yaw(-self.rotation_speed)
                if event.key == pygame.key.key_code(keybindings['pitch_up']) or event.key == self.alternate_keys['pitch_up']:
                    self.game.camera.pitch(self.rotation_speed)
                if event.key == pygame.key.key_code(keybindings['pitch_down']) or event.key == self.alternate_keys['pitch_down']:
                    self.game.camera.pitch(-self.rotation_speed)
                if event.key == pygame.key.key_code(keybindings['toggle_wireframe']) or event.key == self.alternate_keys['toggle_wireframe']:
                    self.game.renderer.renderer3D.toggle_wireframe()
                if event.key == pygame.key.key_code(keybindings['help']) or event.key == self.alternate_keys['help']:
                    self.game.help_mode = not self.game.help_mode
                if (('check_edge' in keybindings) and event.key == pygame.key.key_code(keybindings['check_edge'])) or event.key == self.alternate_keys['check_edge']:
                    self.check_selected_edge_exists()
                if (('remove_internal_edges' in keybindings) and event.key == pygame.key.key_code(keybindings['remove_internal_edges'])) or event.key == self.alternate_keys['remove_internal_edges']:
                    self.remove_internal_edges_via_raycasts()
            elif event.type == pygame.MOUSEWHEEL:
                self.handle_scroll(event.y)
        
        return continue_running 

    def _get_add_vertex_default_text(self):
        try:
            idx = getattr(self.game, 'last_selected_vertex_index', None)
            if idx is not None:
                coords = verticesHolder.vertices[idx*6:idx*6+3]
                if len(coords) == 3:
                    x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                    return f"[{x}, {y}, {z}]"
            if len(self.game.selected_vertices) == 1:
                selected = next(iter(self.game.selected_vertices))
                coords = verticesHolder.vertices[selected*6:selected*6+3]
                if len(coords) == 3:
                    x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                    return f"[{x}, {y}, {z}]"
        except Exception:
            pass
        return "[0.0, 0.0, 0.0]"

    # ===================== Shapes Mode / Input Flow =====================
    def toggle_shapes_mode(self):
        # Exit any existing shape input flow when toggling
        self.game.shapes_mode = not self.game.shapes_mode
        if not self.game.shapes_mode:
            self.cancel_shape_flow(clear_error=True)
            self.game.set_status("Shapes Mode OFF", 120)
        else:
            self.cancel_shape_flow(clear_error=True)
            self.game.set_status("Shapes Mode ON", 120)

    def cancel_shape_flow(self, clear_error:bool=False):
        self.game.shape_input_mode = None
        self.game.shape_step = None
        self.game.shape_primary_text = ""
        self.game.shape_secondary_text = ""
        if clear_error:
            self.game.shape_error = ""

    def start_rectangle_flow(self):
        self.game.shape_input_mode = 'rectangle'
        self.game.shape_step = 'point'
        self.game.shape_primary_text = ""
        self.game.shape_secondary_text = ""
        self.game.shape_error = "Enter start point [x, y, z]"

    def start_ngon_flow(self):
        self.game.shape_input_mode = 'ngon'
        self.game.shape_step = 'point'
        self.game.shape_primary_text = ""
        self.game.shape_secondary_text = ""
        self.game.shape_error = "Enter center/start point [x, y, z]"

    def backspace_shape_text(self):
        if self.game.shape_step in ('point', 'width', 'sides'):
            self.game.shape_primary_text = self.game.shape_primary_text[:-1]
        elif self.game.shape_step == 'length':
            self.game.shape_secondary_text = self.game.shape_secondary_text[:-1]
        self.game.shape_error = ""

    def append_shape_text(self, ch:str):
        if not ch:
            return
        if self.game.shape_step in ('point', 'width', 'sides'):
            self.game.shape_primary_text += ch
        elif self.game.shape_step == 'length':
            self.game.shape_secondary_text += ch
        self.game.shape_error = ""

    def apply_shape_step(self):
        mode = self.game.shape_input_mode
        step = self.game.shape_step
        if mode is None or step is None:
            return
        try:
            if step == 'point':
                # Expect [x, y, z]
                point = ast.literal_eval((self.game.shape_primary_text or '').strip())
                if not (isinstance(point, (list, tuple)) and len(point) == 3):
                    raise ValueError("Enter [x, y, z]")
                px, py, pz = float(point[0]), float(point[1]), float(point[2])
                self._shape_tmp_point = (px, py, pz)
                if mode == 'rectangle':
                    self.game.shape_step = 'width'
                    self.game.shape_primary_text = ""
                    self.game.shape_error = "Enter width (number)"
                elif mode == 'ngon':
                    self.game.shape_step = 'sides'
                    self.game.shape_primary_text = ""
                    self.game.shape_error = "Enter number of sides (>=3)"
                return
            if mode == 'rectangle':
                if step == 'width':
                    width = float(ast.literal_eval((self.game.shape_primary_text or '0').strip()))
                    if not np.isfinite(width) or width <= 0:
                        raise ValueError("Width must be > 0")
                    self._shape_tmp_width = width
                    self.game.shape_step = 'length'
                    self.game.shape_secondary_text = ""
                    self.game.shape_error = "Enter length (number)"
                    return
                if step == 'length':
                    length = float(ast.literal_eval((self.game.shape_secondary_text or '0').strip()))
                    if not np.isfinite(length) or length <= 0:
                        raise ValueError("Length must be > 0")
                    self._shape_tmp_length = length
                    self._commit_rectangle()
                    return
            if mode == 'ngon':
                if step == 'sides':
                    sides_val = int(ast.literal_eval((self.game.shape_primary_text or '0').strip()))
                    if sides_val < 3:
                        raise ValueError("Sides must be >= 3")
                    self._shape_tmp_sides = sides_val
                    self._commit_ngon()
                    return
        except Exception as e:
            self.game.shape_error = f"{e}"

    def _commit_rectangle(self):
        px, py, pz = self._shape_tmp_point
        width = float(self._shape_tmp_width)
        length = float(self._shape_tmp_length)
        # axis-aligned rectangle in XY plane for simplicity
        p0 = (px, py, pz)
        p1 = (px + width, py, pz)
        p2 = (px + width, py + length, pz)
        p3 = (px, py + length, pz)
        # Add as two triangles (p0,p1,p2) and (p0,p2,p3)
        color = self.game.random_color()
        for tri in [(p0, p1, p2), (p0, p2, p3)]:
            for pos in tri:
                self._append_vertex_with_color(pos, color)
        self.game.renderer.renderer3D.update_vertex_buffer()
        self.game.set_status("Rectangle added", 180)
        self.cancel_shape_flow(clear_error=True)

    def _commit_ngon(self):
        px, py, pz = self._shape_tmp_point
        n = int(self._shape_tmp_sides)
        # Create a unit circle polygon in XY plane centered at starting point; use radius 1.0
        radius = 1.0
        vertices = []
        for k in range(n):
            angle = 2.0 * np.pi * (k / n)
            x = px + radius * np.cos(angle)
            y = py + radius * np.sin(angle)
            z = pz
            vertices.append((x, y, z))
        # Triangulate fan around center point (px,py,pz) forming n triangles
        color = self.game.random_color()
        center = (px, py, pz)
        for k in range(n):
            a = vertices[k]
            b = vertices[(k + 1) % n]
            for pos in (center, a, b):
                self._append_vertex_with_color(pos, color)
        self.game.renderer.renderer3D.update_vertex_buffer()
        self.game.set_status(f"{n}-gon added", 180)
        self.cancel_shape_flow(clear_error=True)

    def _append_vertex_with_color(self, pos_tuple, color_rgb):
        x, y, z = float(pos_tuple[0]), float(pos_tuple[1]), float(pos_tuple[2])
        new_vertex = [x, y, z] + list(color_rgb)
        from src.geometry.VerticesHolder import verticesHolder
        verticesHolder.vertices = np.append(verticesHolder.vertices, new_vertex).astype('f4')

    def _fill_among_indices(self, indices):
        if len(indices) < 3:
            return
        vertices = verticesHolder.vertices.reshape(-1, 6)
        existing_triangles = []
        num_tri = len(vertices) // 3
        for t in range(num_tri):
            tri_pos = set(tuple(vertices[t*3 + i, :3]) for i in range(3))
            existing_triangles.append(tri_pos)

        # Deduplicate input indices by position (rounded) to avoid duplicates producing degenerate triangles
        def round_triplet(p):
            return (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))

        unique_by_pos = {}
        for i in sorted(indices):
            key = round_triplet(vertices[i, :3])
            if key not in unique_by_pos:
                unique_by_pos[key] = i
        indices = sorted(unique_by_pos.values())

        new_triangles = []
        for comb in itertools.combinations(sorted(indices), 3):
            pos = [tuple(vertices[i, :3]) for i in comb]
            # Skip degenerate triangles: duplicate positions within the triad
            if len(set(pos)) < 3:
                continue
            # Skip near-zero-area triangles (collinear or extremely tiny)
            p0 = np.array(pos[0], dtype=float)
            p1 = np.array(pos[1], dtype=float)
            p2 = np.array(pos[2], dtype=float)
            if np.linalg.norm(np.cross(p1 - p0, p2 - p0)) < 1e-8:
                continue
            pos_set = set(pos)
            if pos_set not in existing_triangles:
                new_triangles.append(pos)

        if not new_triangles:
            return
        new_data = []
        for tri_pos in new_triangles:
            new_color = self.game.random_color()
            for pos in tri_pos:
                new_data.extend(pos)
                new_data.extend(new_color)
        if new_data:
            verticesHolder.vertices = np.append(verticesHolder.vertices, new_data).astype('f4')
            self.game.renderer.renderer3D.update_vertex_buffer()

    def find_nearest_vertex(self, x, y):
        if verticesHolder.vertices.size == 0:
            return None
        vertices = verticesHolder.vertices.reshape(-1, 6)
        screen_coords = self.game.renderer.renderer3D.world_to_screen(vertices[:, :3])
        
        print(f"Total vertices: {len(vertices)}")
        print(f"Screen coordinates shape: {screen_coords.shape}")
        
        # Calculate distances for all vertices
        distances = np.sqrt(np.sum((screen_coords - np.array([x, y])) ** 2, axis=1))
        
        # Find the index of the nearest vertex
        nearest_index = np.argmin(distances)
        nearest_distance = distances[nearest_index]
        
        # Set a maximum distance threshold (e.g., 500 pixels)
        max_distance = 500
        
        print(f"Click position: ({x}, {y})")
        print("Vertex positions:")
        for i, (sx, sy) in enumerate(screen_coords):
            print(f"Vertex {i}: ({sx:.2f}, {sy:.2f}), distance: {distances[i]:.2f}")
        
        print(f"Nearest vertex screen position: ({screen_coords[nearest_index][0]:.2f}, {screen_coords[nearest_index][1]:.2f})")
        print(f"Distance to nearest vertex: {nearest_distance:.2f}")
        
        if nearest_distance > max_distance:
            print(f"No vertex within {max_distance} pixels")
            return None
        
        print(f"Selected vertex index: {nearest_index}")
        
        return nearest_index

    def apply_edit(self):
        if len(self.game.selected_vertices) != 1:
            print("Cannot edit multiple vertices")
            self.game.edit_mode = False
            return
        selected = list(self.game.selected_vertices)[0]
        try:
            new_coords = eval(self.game.edit_text)
            if isinstance(new_coords, (list, tuple)) and len(new_coords) == 3:
                verticesHolder.vertices[selected*6:selected*6+3] = new_coords
                print(f"New vertex coordinates set to: {new_coords}")
                self.game.edit_mode = False
                print("edit mode deactivated")
                self.game.renderer.renderer3D.update_vertex_buffer()
            else:
                print(f"Invalid input: {self.game.edit_text}")
        except:
            print("Invalid input. Please enter coordinates as [x, y, z]")
            raise

    def apply_add_vertex(self):
        # Safely parse and validate input like [x, y, z]
        text = (self.game.add_vertex_text or "").strip()
        # If user accidentally typed a second list after the placeholder, keep the last list
        if text.count('[') > 1:
            last_open = text.rfind('[')
            last_close = text.rfind(']')
            if last_close != -1 and last_close > last_open:
                text = text[last_open:last_close+1]
            else:
                text = text[last_open:]
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            self.game.add_vertex_error = "Invalid format. Use [x, y, z] with numbers."
            print(f"Invalid add-vertex input: {text}")
            return

        if not (isinstance(parsed, (list, tuple)) and len(parsed) == 3):
            self.game.add_vertex_error = "Enter exactly three numbers like [1.0, 2.0, 3.0]."
            print(f"Invalid add-vertex input (not 3 items): {parsed}")
            return

        try:
            x, y, z = (float(parsed[0]), float(parsed[1]), float(parsed[2]))
        except (TypeError, ValueError):
            self.game.add_vertex_error = "Coordinates must be numbers."
            print(f"Invalid add-vertex input (non-numeric): {parsed}")
            return

        self.add_vertex(x, y, z)
        print(f"Added vertex at: {[x, y, z]}")
        self.game.add_vertex_mode = False
        self.game.add_vertex_text = ""
        self.game.add_vertex_error = ""

    def add_vertex(self, x:float, y:float, z:float):
        assert isinstance(x, float), "x must be float"
        assert isinstance(y, float), "y must be float"
        assert isinstance(z, float), "z must be float"
        
        current_count = len(verticesHolder.vertices) // 6
        if current_count % 3 == 0:
            self.game.current_color = self.game.random_color()
        
        new_vertex = [x, y, z] + self.game.current_color
        verticesHolder.vertices = np.append(verticesHolder.vertices, new_vertex).astype('f4')
        self.game.renderer.renderer3D.update_vertex_buffer()
        print(f"New vertex added: {new_vertex[:3]}")

    def apply_extrude(self):
        text = (self.game.extrude_text or "").strip()
        if text.count('[') > 1:
            last_open = text.rfind('[')
            last_close = text.rfind(']')
            if last_close != -1 and last_close > last_open:
                text = text[last_open:last_close+1]
            else:
                text = text[last_open:]
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            self.game.extrude_error = "Invalid format. Use [x, y, z] with numbers."
            return
        if not (isinstance(parsed, (list, tuple)) and len(parsed) == 3):
            self.game.extrude_error = "Enter exactly three numbers like [1.0, 2.0, 3.0]."
            return
        try:
            px, py, pz = (float(parsed[0]), float(parsed[1]), float(parsed[2]))
        except (TypeError, ValueError):
            self.game.extrude_error = "Coordinates must be numbers."
            return

        if len(self.game.selected_vertices) == 0:
            self.game.extrude_mode = False
            self.game.extrude_text = ""
            self.game.extrude_error = ""
            return

        last_idx = None
        if self.game.last_selected_vertex_index is not None:
            last_idx = self.game.last_selected_vertex_index
        elif len(self.game.selected_vertices) > 0:
            last_idx = max(self.game.selected_vertices)
        vertices = verticesHolder.vertices.reshape(-1, 6)
        if last_idx is None or last_idx < 0 or last_idx >= len(vertices):
            self.game.extrude_error = "Invalid last selected vertex."
            return
        P = vertices[last_idx, :3].astype(float)
        Pprime = np.array([px, py, pz], dtype=float)
        offset = Pprime - P

        selected = sorted(list(self.game.selected_vertices))
        if not selected:
            self.game.extrude_error = "No vertices selected."
            return

        # Copy selected to the end with translation; keep original colors for copies
        new_rows = []
        for i in selected:
            pos = vertices[i, :3].astype(float) + offset
            color = vertices[i, 3:6].astype(float)
            new_rows.append(np.concatenate([pos, color]))
        new_rows = np.array(new_rows, dtype=np.float32)

        # Append to verticesHolder
        if new_rows.size:
            verticesHolder.vertices = np.append(verticesHolder.vertices, new_rows.flatten()).astype('f4')

        # Build side faces between corresponding old/new vertices when possible
        # We attempt to form triangles from quads (i,j) -> (i',j') where edges existed in selection
        old_vertices = verticesHolder.vertices.reshape(-1, 6)
        total_before = len(old_vertices) - len(new_rows)
        index_map = {old_idx: total_before + k for k, old_idx in enumerate(selected)}

        # Reuse the existing 'form triangles' logic for caps and sides
        rows = verticesHolder.vertices.reshape(-1, 6)
        used_fallback_for_sides = False
        saved_selection = set(self.game.selected_vertices)
        try:
            # Cap the extruded copy by selecting only the new indices and forming triangles
            new_indices = [index_map[i] for i in selected if i in index_map]
            if len(new_indices) >= 3:
                self.game.selected_vertices = set(new_indices)
                self.triangle_filler.form_triangles_from_selected()

            # Order the original selected vertices around their centroid to walk the perimeter
            if len(selected) >= 3:
                sel_positions = np.array([rows[i, :3].astype(float) for i in selected], dtype=np.float64)
                centroid = sel_positions.mean(axis=0)
                centered = sel_positions - centroid
                if np.linalg.norm(centered) > 0:
                    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
                    u_axis = Vt[0]
                    v_axis = Vt[1] if Vt.shape[0] > 1 else np.array([0.0, 1.0, 0.0])
                    proj_u = centered.dot(u_axis)
                    proj_v = centered.dot(v_axis)
                    pts2 = np.stack([proj_u, proj_v], axis=1)
                    sorted_idx = sorted(range(len(pts2)), key=lambda i: (pts2[i][0], pts2[i][1]))
                    def cross(o, a, b):
                        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
                    lower = []
                    for i in sorted_idx:
                        while len(lower) >= 2 and cross(pts2[lower[-2]], pts2[lower[-1]], pts2[i]) <= 0:
                            lower.pop()
                        lower.append(i)
                    upper = []
                    for i in reversed(sorted_idx):
                        while len(upper) >= 2 and cross(pts2[upper[-2]], pts2[upper[-1]], pts2[i]) <= 0:
                            upper.pop()
                        upper.append(i)
                    hull_idx = lower[:-1] + upper[:-1]
                    if len(hull_idx) < 3:
                        angles = np.arctan2(pts2[:,1], pts2[:,0])
                        hull_idx = list(np.argsort(angles))
                    ordered = [selected[int(k)] for k in hull_idx]

                    # For each edge on the perimeter, select the quad's four vertices and form triangles
                    for i in range(len(ordered)):
                        a = ordered[i]
                        b = ordered[(i + 1) % len(ordered)]
                        a2 = index_map.get(a)
                        b2 = index_map.get(b)
                        if a2 is None or b2 is None:
                            continue
                        self.game.selected_vertices = {a, b, a2, b2}
                        self.triangle_filler.form_triangles_from_selected()
                    used_fallback_for_sides = True
        finally:
            # Restore selection
            self.game.selected_vertices = saved_selection

        # After using the generic filling, skip the raycast cleanup which can be aggressive
        # and may remove freshly created boundary faces.
        if not used_fallback_for_sides:
            self.remove_internal_edges_via_raycasts()

        # Done; update GPU and exit mode
        self.game.renderer.renderer3D.update_vertex_buffer()
        self.game.extrude_mode = False
        self.game.extrude_text = ""
        self.game.extrude_error = ""

    def save_vertices(self):
        filename = self.game.filename_text
        vertices = verticesHolder.vertices.reshape(-1, 6)
        with open(filename, 'w') as file:
            for vertex in vertices:
                file.write(f"{' '.join(map(str, vertex))}\n")
        print(f"Vertices saved to {filename}")

    def apply_filename_edit(self):
        # Exit filename edit mode and immediately save to the new file
        self.game.filename_edit_mode = False
        purpose = getattr(self.game, 'filename_edit_purpose', 'save')
        if purpose == 'new':
            print(f"New file name set to: {self.game.filename_text}. Clearing all vertices.")
            try:
                verticesHolder.vertices = np.array([], dtype='f4')
                self.game.selected_vertices.clear()
                self.game.yellow_highlights.clear()
                self.game.uiOverlayCreator.scroll_offset = 0
                self.game.current_color = self.game.random_color()
                self.game.renderer.renderer3D.update_vertex_buffer()
                set_last_file(self.game.filename_text)
            except Exception as e:
                print(f"Error clearing vertices for new file {self.game.filename_text}: {e}")
            finally:
                self.game.filename_edit_purpose = 'save'
                # Reset last selected vertex reference on new file
                self.game.last_selected_vertex_index = None
        elif purpose == 'open':
            print(f"Opening file: {self.game.filename_text}")
            try:
                loaded = load_vertices_from_file(self.game.filename_text)
                verticesHolder.vertices = loaded
                self.game.selected_vertices.clear()
                self.game.yellow_highlights.clear()
                self.game.uiOverlayCreator.scroll_offset = 0

                total_vertices = len(verticesHolder.vertices) // 6
                if total_vertices > 0:
                    if total_vertices % 3 == 0:
                        self.game.current_color = self.game.random_color()
                    else:
                        last_vertex = verticesHolder.vertices[-6:]
                        self.game.current_color = last_vertex[3:6].tolist()
                else:
                    self.game.current_color = self.game.random_color()

                self.game.renderer.renderer3D.update_vertex_buffer()
                print(f"Loaded vertices from {self.game.filename_text}: count={(len(verticesHolder.vertices)//6)}")
                set_last_file(self.game.filename_text)
            except Exception as e:
                print(f"Error opening {self.game.filename_text}: {e}")
            finally:
                self.game.filename_edit_purpose = 'save'
                # Reset last selected vertex reference on open
                self.game.last_selected_vertex_index = None
        else:
            print(f"Save filename set to: {self.game.filename_text}")
            try:
                self.save_vertices()
                set_last_file(self.game.filename_text)
            except Exception as e:
                print(f"Error saving to {self.game.filename_text}: {e}")

    def handle_vertex_list_click(self, x, y, ctrl_pressed):
        for actual_index, rect in self.game.uiOverlayCreator.vertex_rects:
            if rect.collidepoint(x, y):
                if ctrl_pressed:
                    if actual_index in self.game.selected_vertices:
                        self.game.selected_vertices.remove(actual_index)
                    else:
                        self.game.selected_vertices.add(actual_index)
                else:
                    self.game.selected_vertices = {actual_index}
                # Track last interacted vertex from the list click
                self.game.last_selected_vertex_index = actual_index
                return True
        return False

    def handle_scroll(self, y):
        total_vertices = len(verticesHolder.vertices) // 6
        if y > 0:  # Scroll up
            self.game.uiOverlayCreator.scroll_offset = max(0, self.game.uiOverlayCreator.scroll_offset - self.game.scroll_speed)
        else:  # Scroll down
            max_offset = max(0, total_vertices - self.game.uiOverlayCreator.max_visible_vertices)
            self.game.uiOverlayCreator.scroll_offset = min(max_offset, self.game.uiOverlayCreator.scroll_offset + self.game.scroll_speed) 

    def remove_backfacing_triangles(self):
        vertices = verticesHolder.vertices
        if vertices.size == 0:
            return
        rows = vertices.reshape(-1, 6)
        num_tri = len(rows) // 3
        if num_tri == 0:
            return

        # Object-centric orientation: outward is away from object bounding-box center
        all_positions = rows[:, :3]
        if len(all_positions) > 0:
            mins = np.min(all_positions, axis=0)
            maxs = np.max(all_positions, axis=0)
            object_center = (mins + maxs) * 0.5
        else:
            object_center = np.array([0.0, 0.0, 0.0])

        def tri_outward(t_index:int) -> bool:
            i0 = t_index * 3
            p0 = rows[i0, :3]
            p1 = rows[i0 + 1, :3]
            p2 = rows[i0 + 2, :3]
            p0 = np.array(p0, dtype=float)
            p1 = np.array(p1, dtype=float)
            p2 = np.array(p2, dtype=float)
            normal = np.cross(p1 - p0, p2 - p0)
            norm_len = np.linalg.norm(normal)
            if norm_len == 0:
                return False
            tri_center = (p0 + p1 + p2) / 3.0
            from_object_center = tri_center - object_center
            dot = float(np.dot(normal, from_object_center))
            eps = 1e-8 * (np.linalg.norm(from_object_center) * norm_len + 1.0)
            return dot >= -eps

        flipped = 0
        for t in range(num_tri):
            if not tri_outward(t):
                i0 = t * 3
                # Swap rows i0+1 and i0+2 to flip winding
                tmp = rows[i0 + 1].copy()
                rows[i0 + 1] = rows[i0 + 2]
                rows[i0 + 2] = tmp
                flipped += 1

        # Remove duplicate triangles (same three positions, ignoring order and colors)
        num_tri_after = len(rows) // 3
        seen = set()
        keep_row_indices = []
        duplicates_removed = 0

        def canonical_key(p0, p1, p2):
            def round_triplet(p):
                return (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))
            pts = sorted([round_triplet(p0), round_triplet(p1), round_triplet(p2)])
            return tuple(pts)

        for t in range(num_tri_after):
            i0 = t * 3
            p0 = rows[i0, :3]
            p1 = rows[i0 + 1, :3]
            p2 = rows[i0 + 2, :3]
            key = canonical_key(p0, p1, p2)
            if key in seen:
                duplicates_removed += 1
                continue
            seen.add(key)
            keep_row_indices.extend([i0, i0 + 1, i0 + 2])

        if duplicates_removed > 0:
            rows = rows[keep_row_indices]

        if flipped == 0 and duplicates_removed == 0:
            print("No inward-facing triangles to fix or duplicate triangles to remove.")
            return

        if duplicates_removed > 0:
            print(f"Removed {duplicates_removed} duplicate triangle(s).")

        verticesHolder.vertices = rows.astype('f4').flatten()

        # Clear selection and editing state
        self.game.selected_vertices.clear()
        self.game.edit_mode = False
        self.game.edit_text = ""
        self.game.yellow_highlights.clear()

        # Maintain current color for subsequent additions
        total_vertices = len(verticesHolder.vertices) // 6
        if total_vertices > 0:
            if total_vertices % 3 == 0:
                self.game.current_color = self.game.random_color()
            else:
                last_vertex_color = verticesHolder.vertices[-3:]
                self.game.current_color = last_vertex_color.tolist()
        else:
            self.game.current_color = self.game.random_color()

        self.game.renderer.renderer3D.update_vertex_buffer()
        print(f"Fixed winding for {flipped} inward-facing triangle(s).")
        # Clear last selected after geometry reorientation
        self.game.last_selected_vertex_index = None

    def check_selected_edge_exists(self):
        rows = verticesHolder.vertices.reshape(-1, 6)
        if len(self.game.selected_vertices) != 2:
            self.game.set_status("Select exactly two vertices to check edge", 180)
            return
        i_a, i_b = sorted(list(self.game.selected_vertices))
        if i_a < 0 or i_b >= len(rows):
            self.game.set_status("Selected vertex indices out of range", 180)
            return
        pos_a = rows[i_a, :3]
        pos_b = rows[i_b, :3]

        def same_point(p, q, tol=1e-6):
            return (abs(float(p[0]) - float(q[0])) <= tol and
                    abs(float(p[1]) - float(q[1])) <= tol and
                    abs(float(p[2]) - float(q[2])) <= tol)

        highlight_indices = set()
        num_tri = len(rows) // 3
        found_count = 0
        for t in range(num_tri):
            i0 = t * 3
            tri_positions = [rows[i0 + 0, :3], rows[i0 + 1, :3], rows[i0 + 2, :3]]
            edges = [(0, 1), (1, 2), (2, 0)]
            for e0, e1 in edges:
                p = tri_positions[e0]
                q = tri_positions[e1]
                if (same_point(p, pos_a) and same_point(q, pos_b)) or (same_point(p, pos_b) and same_point(q, pos_a)):
                    found_count += 1
                    highlight_indices.update({i0 + e0, i0 + e1})

        if found_count > 0:
            self.game.yellow_highlights = highlight_indices
            self.game.uiOverlayCreator.scroll_offset = min(highlight_indices)
            self.game.set_status(f"Edge exists; found in {found_count} triangle edge(s)", 240)
        else:
            self.game.set_status("No edge exists between selected vertices", 240)

    def remove_internal_edges_via_raycasts(self):
        rows = verticesHolder.vertices.reshape(-1, 6)
        num_rows = len(rows)
        if num_rows < 3:
            self.game.set_status("No triangles to process", 180)
            return
        num_tri = num_rows // 3

        # Precompute triangle positions (float64 for robustness)
        # Only operate on complete triangles to avoid reshape errors when rows % 3 != 0
        tri_rows = rows[:num_tri * 3]
        if num_tri == 0:
            self.game.set_status("No triangles to process", 180)
            return
        tri_pos = tri_rows.reshape(num_tri, 3, 6)[:, :, :3].astype(np.float64)

        # Map edges (by rounded position pairs) to triangles that contain them
        def round_triplet(p):
            return (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))

        edge_to_tris = {}
        for t in range(num_tri):
            p0, p1, p2 = tri_pos[t]
            edges = [(p0, p1), (p1, p2), (p2, p0)]
            for a, b in edges:
                ra, rb = round_triplet(a), round_triplet(b)
                key = tuple(sorted([ra, rb]))
                edge_to_tris.setdefault(key, set()).add(t)

        # Directions: 26-ish directions (axes, face diagonals, space diagonals)
        dirs = []
        base = [
            (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1),
            (1, 1, 0), (1, -1, 0), (-1, 1, 0), (-1, -1, 0),
            (1, 0, 1), (1, 0, -1), (-1, 0, 1), (-1, 0, -1),
            (0, 1, 1), (0, 1, -1), (0, -1, 1), (0, -1, -1),
            (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
            (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1),
        ]
        for dx, dy, dz in base:
            v = np.array([dx, dy, dz], dtype=np.float64)
            n = np.linalg.norm(v)
            if n > 0:
                dirs.append(v / n)
        dirs = np.array(dirs)

        def ray_intersects_triangle(origin, direction, v0, v1, v2, eps=1e-8):
            # Moller-Trumbore
            edge1 = v1 - v0
            edge2 = v2 - v0
            pvec = np.cross(direction, edge2)
            det = np.dot(edge1, pvec)
            if -eps < det < eps:
                return False, None
            inv_det = 1.0 / det
            tvec = origin - v0
            u = np.dot(tvec, pvec) * inv_det
            if u < 0.0 - eps or u > 1.0 + eps:
                return False, None
            qvec = np.cross(tvec, edge1)
            v = np.dot(direction, qvec) * inv_det
            if v < 0.0 - eps or u + v > 1.0 + eps:
                return False, None
            t = np.dot(edge2, qvec) * inv_det
            if t <= eps:
                return False, None
            return True, t

        def edge_is_internal(pa, pb, exclude_tris:set):
            def fmt3(p):
                return f"({float(p[0]):.3f}, {float(p[1]):.3f}, {float(p[2]):.3f})"
            # Sample points along the edge (avoid endpoints)
            samples = [0.25, 0.5, 0.75]
            for alpha in samples:
                origin = (1.0 - alpha) * pa + alpha * pb
                # Require a hit in every sampled direction to consider interior
                for d in dirs:
                    hit_any = False
                    for t_idx in range(num_tri):
                        if t_idx in exclude_tris:
                            continue
                        v0, v1, v2 = tri_pos[t_idx]
                        hit, _ = ray_intersects_triangle(origin, d, v0, v1, v2)
                        if hit:
                            hit_any = True
                            break
                    if not hit_any:
                        print(f"[internal-edge] ray miss for edge {fmt3(pa)} -> {fmt3(pb)} at alpha={alpha:.2f}, dir=({float(d[0]):.3f}, {float(d[1]):.3f}, {float(d[2]):.3f})")
                        return False
            return True

        triangles_to_remove = set()
        internal_edge_count = 0
        # Evaluate each unique edge once
        for key, tri_set in edge_to_tris.items():
            ra, rb = key
            pa = np.array(ra, dtype=np.float64)
            pb = np.array(rb, dtype=np.float64)
            # Skip degenerate (zero-length) edges
            length = np.linalg.norm(pb - pa)
            if length < 1e-9:
                continue
            print(f"[internal-edge] checking edge {pa[0]:.3f},{pa[1]:.3f},{pa[2]:.3f} -> {pb[0]:.3f},{pb[1]:.3f},{pb[2]:.3f}; length={length:.3f}; shared_tris={len(tri_set)}")
            if edge_is_internal(pa, pb, tri_set):
                internal_edge_count += 1
                for t_idx in tri_set:
                    triangles_to_remove.add(t_idx)

        if not triangles_to_remove:
            self.game.set_status("No internal edges found", 240)
            return

        # Remove triangles (3 rows per triangle)
        mask = np.ones(num_rows, dtype=bool)
        for t_idx in triangles_to_remove:
            i0 = t_idx * 3
            mask[i0:i0+3] = False
        new_rows = rows[mask]
        verticesHolder.vertices = new_rows.astype('f4').flatten()

        # Reset selection/UI and keep color continuity
        self.game.selected_vertices.clear()
        self.game.edit_mode = False
        self.game.edit_text = ""
        self.game.yellow_highlights.clear()

        total_vertices = len(verticesHolder.vertices) // 6
        if total_vertices > 0:
            if total_vertices % 3 == 0:
                self.game.current_color = self.game.random_color()
            else:
                last_vertex_color = verticesHolder.vertices[-3:]
                self.game.current_color = last_vertex_color.tolist()
        else:
            self.game.current_color = self.game.random_color()

        self.game.renderer.renderer3D.update_vertex_buffer()
        removed_tris = len(triangles_to_remove)
        self.game.set_status(f"Removed {removed_tris} triangles from {internal_edge_count} internal edge(s)", 300)
        # Clear last selected after geometry changes
        self.game.last_selected_vertex_index = None

    def delete_selected_vertices(self):
        if not self.game.selected_vertices:
            return
        try:
            vertices = verticesHolder.vertices
            if vertices.size == 0:
                return
            vertex_rows = vertices.reshape(-1, 6)
            max_index = len(vertex_rows) - 1
            indices_to_delete = sorted([i for i in self.game.selected_vertices if 0 <= i <= max_index])
            if not indices_to_delete:
                return
            keep_mask = np.ones(len(vertex_rows), dtype=bool)
            keep_mask[indices_to_delete] = False
            new_rows = vertex_rows[keep_mask]
            verticesHolder.vertices = new_rows.astype('f4').flatten()

            # Clear selection and editing state
            self.game.selected_vertices.clear()
            self.game.edit_mode = False
            self.game.edit_text = ""
            self.game.yellow_highlights.clear()

            # Clamp scroll
            total_vertices = len(verticesHolder.vertices) // 6
            max_offset = max(0, total_vertices - self.game.uiOverlayCreator.max_visible_vertices)
            self.game.uiOverlayCreator.scroll_offset = min(self.game.uiOverlayCreator.scroll_offset, max_offset)

            # Maintain current color for subsequent additions
            if total_vertices > 0:
                if total_vertices % 3 == 0:
                    self.game.current_color = self.game.random_color()
                else:
                    last_vertex_color = verticesHolder.vertices[-3:]
                    self.game.current_color = last_vertex_color.tolist()
            else:
                self.game.current_color = self.game.random_color()

            # Update GPU buffer
            self.game.renderer.renderer3D.update_vertex_buffer()
        except Exception as e:
            print(f"Error deleting vertices: {e}")
        finally:
            # Reset last selected after deletions
            self.game.last_selected_vertex_index = None

    def clear_all_vertices(self):
        try:
            verticesHolder.vertices = np.array([], dtype='f4')
            self.game.selected_vertices.clear()
            self.game.yellow_highlights.clear()
            self.game.uiOverlayCreator.scroll_offset = 0
            self.game.current_color = self.game.random_color()
            self.game.edit_mode = False
            self.game.edit_text = ""
            self.game.renderer.renderer3D.update_vertex_buffer()
            print("All vertices cleared")
        except Exception as e:
            print(f"Error clearing all vertices: {e}")
        finally:
            # Reset last selected on clear
            self.game.last_selected_vertex_index = None