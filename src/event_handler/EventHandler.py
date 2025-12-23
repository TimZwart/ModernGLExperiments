import pygame
from src.event_handler.TriangleFiller import TriangleFiller
from src.geometry.VerticesHolder import verticesHolder
from src.geometry.loader import load_vertices_from_file
from src.configuration.session_store import set_last_file

import numpy as np
import itertools
from src.configuration.loadconfig import keybindings, mouse_rotation_button
from src.event_handler.CoveredTriangleRemover import CoveredTriangleRemover
from src.event_handler.InternalEdgeRemover import InternalEdgeRemover
from src.event_handler.BackfaceTriangleFixer import BackfaceTriangleFixer
from src.event_handler.EdgeExistenceChecker import EdgeExistenceChecker
from src.event_handler.PositionMatchInspector import PositionMatchInspector
from src.event_handler.SelectionController import SelectionController
from src.event_handler.VertexEditController import VertexEditController
from src.event_handler.ShapesController import ShapesController
from src.event_handler.FileController import FileController
from src.event_handler.ExtrudeController import ExtrudeController
from src.event_handler.CleanupModeController import CleanupModeController
from src.event_handler.VerticesAnalyzeExporter import VerticesAnalyzeExporter
import ast
import os

class EventHandler:
    def __init__(self, game):
        self.game = game
        self.rotation_button = mouse_rotation_button
        self.mouse_button_rotation_held = False
        self.rotate_key_held = False
        self.triangle_filler = TriangleFiller(game)
        self.covered_triangle_remover = CoveredTriangleRemover()
        self.internal_edge_remover = InternalEdgeRemover()
        self.backface_triangle_fixer = BackfaceTriangleFixer()
        self.edge_existence_checker = EdgeExistenceChecker()
        self.position_match_inspector = PositionMatchInspector()
        self.vertex_editor = VertexEditController(game)
        self.selection_controller = SelectionController(game, vertex_editor=self.vertex_editor)
        self.shapes_controller = ShapesController(game, clear_rotation_state=self._clear_rotation_state)
        self.file_controller = FileController(game)
        self.extrude_controller = ExtrudeController(game, triangle_filler=self.triangle_filler, remove_internal_edges_callable=self.remove_internal_edges_via_raycasts)
        self.cleanup_mode_controller = CleanupModeController(game, clear_rotation_state=self._clear_rotation_state, cancel_shape_flow=self.cancel_shape_flow)
        self.vertices_analyze_exporter = VerticesAnalyzeExporter()
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
            'remove_covered': pygame.K_F4,
            'show_position_matches': pygame.K_F2,
            'color_picker': pygame.K_c,  # Color picker toggle
        }
        self.rotation_speed = 0.1

    def _clear_rotation_state(self):
        self.mouse_button_rotation_held = False
        self.rotate_key_held = False

    def handle_events(self):
        continue_running = True
        for event in pygame.event.get():
            # If disambiguation modal is active, only handle its inputs
            if getattr(self.game, 'disambiguation_mode', False):
                if event.type == pygame.QUIT:
                    continue_running = False
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Cancel disambiguation
                        self._end_disambiguation(None)
                        continue
                    if event.key in (pygame.K_UP, pygame.K_w):
                        if self.game.disambiguation_candidates:
                            self.game.disambiguation_selected = (self.game.disambiguation_selected - 1) % len(self.game.disambiguation_candidates)
                        continue
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        if self.game.disambiguation_candidates:
                            self.game.disambiguation_selected = (self.game.disambiguation_selected + 1) % len(self.game.disambiguation_candidates)
                        continue
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        idx = None
                        if self.game.disambiguation_candidates:
                            idx = self.game.disambiguation_candidates[self.game.disambiguation_selected]
                        self._end_disambiguation(idx)
                        continue
                    # Number keys 1..9 choose directly
                    if pygame.K_1 <= event.key <= pygame.K_9:
                        choice = event.key - pygame.K_1
                        if 0 <= choice < len(self.game.disambiguation_candidates):
                            idx = self.game.disambiguation_candidates[choice]
                            self._end_disambiguation(idx)
                        continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Click inside one of the highlighted triangles; pick the closest at the click point
                    x, y = event.pos
                    try:
                        tris = getattr(self.game, 'disambiguation_triangles', [])
                        best = None
                        best_depth = None
                        for ov in tris:
                            pts = ov.get('screen_pts', [])
                            zvals = ov.get('ndc_z', [])
                            if len(pts) == 3 and len(zvals) == 3 and self._point_in_triangle((x, y), pts[0], pts[1], pts[2]):
                                w0, w1, w2 = self._barycentric_weights((x, y), pts[0], pts[1], pts[2])
                                # Interpolate ndc z; smaller (more negative) is closer to camera in OpenGL
                                depth = w0 * zvals[0] + w1 * zvals[1] + w2 * zvals[2]
                                if (best_depth is None) or (depth < best_depth):
                                    best_depth = depth
                                    best = ov
                        if best is not None:
                            chosen_idx = int(best.get('candidate'))
                            self._end_disambiguation(chosen_idx)
                    except Exception:
                        pass
                    continue
                # Swallow other events
                continue
            # Modal: File picker has precedence over everything except QUIT
            if getattr(self.game, 'file_picker_mode', False):
                if event.type == pygame.QUIT:
                    continue_running = False
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.game.file_picker_mode = False
                        continue
                    items = self.game.file_picker_items
                    if not items:
                        self.game.file_picker_mode = False
                        continue
                    idx = int(self.game.file_picker_index)
                    page = int(self.game.file_picker_max_visible)
                    if event.key == pygame.K_UP:
                        idx = max(0, idx - 1)
                    elif event.key == pygame.K_DOWN:
                        idx = min(len(items) - 1, idx + 1)
                    elif event.key == pygame.K_PAGEUP:
                        idx = max(0, idx - page)
                    elif event.key == pygame.K_PAGEDOWN:
                        idx = min(len(items) - 1, idx + page)
                    elif event.key == pygame.K_HOME:
                        idx = 0
                    elif event.key == pygame.K_END:
                        idx = len(items) - 1
                    elif event.key == pygame.K_RETURN:
                        try:
                            chosen = items[idx]
                            self._open_vertices_file(chosen)
                            self.game.filename_text = chosen
                        except Exception:
                            pass
                        finally:
                            self.game.file_picker_mode = False
                            self.game.filename_edit_purpose = 'save'
                        continue
                    self.game.file_picker_index = idx
                    if idx < self.game.file_picker_scroll:
                        self.game.file_picker_scroll = idx
                    elif idx >= self.game.file_picker_scroll + page:
                        self.game.file_picker_scroll = max(0, idx - page + 1)
                    continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    x, y = event.pos
                    try:
                        for item_idx, rect in self.game.file_picker_item_rects:
                            if rect.collidepoint(x, y):
                                self.game.file_picker_index = int(item_idx)
                                chosen = self.game.file_picker_items[item_idx]
                                try:
                                    self._open_vertices_file(chosen)
                                    self.game.filename_text = chosen
                                except Exception:
                                    pass
                                finally:
                                    self.game.file_picker_mode = False
                                    self.game.filename_edit_purpose = 'save'
                                break
                    except Exception:
                        pass
                    continue
                # Swallow all other events while picker is open
                continue
            # Modal: Color picker has precedence over other inputs except QUIT and file picker
            if getattr(self.game, 'color_picker_mode', False):
                if event.type == pygame.QUIT:
                    continue_running = False
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.game.color_picker_mode = False
                        continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    x, y = event.pos
                    try:
                        # Check if user clicked on a color in the picker
                        for color_rect, color_name in self.game.color_picker_rects:
                            if color_rect.collidepoint(x, y):
                                # Apply the selected color
                                self.game.current_color = self.game.predefined_colors[color_name].copy()
                                # Update current color input field if we're in edit/add mode
                                formatted_color = self._fmt_triplet(self.game.current_color)
                                if hasattr(self.game, 'add_vertex_mode') and self.game.add_vertex_mode:
                                    self.game.add_vertex_color_text = formatted_color
                                    print(f"Updated add vertex color to: {formatted_color}")
                                if hasattr(self.game, 'edit_mode') and self.game.edit_mode:
                                    self.game.edit_color_text = formatted_color
                                    print(f"Updated edit color to: {formatted_color}")
                                # Ensure we remain in edit mode if exactly one vertex is selected
                                try:
                                    if len(getattr(self.game, 'selected_vertices', set())) == 1:
                                        self.game.edit_mode = True
                                except Exception:
                                    pass
                                print(f"Selected color '{color_name}': {self.game.current_color}")
                                # Close the color picker
                                self.game.color_picker_mode = False
                                break
                        continue
                    except Exception:
                        pass
                # Swallow all other events while color picker is open
                continue
            # Modal: Shapes input flows have precedence over other inputs except QUIT
            if getattr(self.game, 'shapes_mode', False) and getattr(self.game, 'shape_input_mode', None) is not None:
                if event.type == pygame.QUIT:
                    continue_running = False
                    continue
                if event.type == pygame.KEYDOWN:
                    # Global Undo during shape entry (allow Ctrl+Z)
                    mods = pygame.key.get_mods()
                    if (mods & pygame.KMOD_CTRL) and (event.key == pygame.K_z):
                        self.game.undo_last_action()
                        continue
                    # Allow help key during shape input flow to toggle shapes help screen
                    if (event.key == pygame.key.key_code(keybindings['help'])) or (event.key == self.alternate_keys['help']):
                        self.game.help_mode = not self.game.help_mode
                        continue
                    # Allow color picker during shape input flow
                    if (event.key == pygame.key.key_code(keybindings.get('color_picker', 'c'))) or (event.key == self.alternate_keys.get('color_picker', pygame.K_c)):
                        self.game.color_picker_mode = not self.game.color_picker_mode
                        continue
                    if event.key == pygame.K_ESCAPE:
                        # Abort current shape input flow, remain in shapes mode
                        self.cancel_shape_flow(clear_error=True)
                        continue
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
            # Modal: Cleanup Mode swallows all but its own keys and QUIT
            if getattr(self.game, 'cleanup_mode', False):
                if event.type == pygame.QUIT:
                    continue_running = False
                    continue
                if event.type == pygame.KEYDOWN:
                    mods = pygame.key.get_mods()
                    # Allow global Undo during cleanup
                    if (mods & pygame.KMOD_CTRL) and (event.key == pygame.K_z):
                        self.game.undo_last_action()
                        continue
                    if event.key == pygame.key.key_code(keybindings.get('undo', 'z')):
                        self.game.undo_last_action()
                        continue
                    # Export analysis file (reuse Save keybinding in Cleanup Mode)
                    if (('save_vertices' in keybindings) and event.key == pygame.key.key_code(keybindings['save_vertices'])) or event.key == self.alternate_keys['save_vertices']:
                        try:
                            self.vertices_analyze_exporter.export(self.game)
                        except Exception as _:
                            pass
                        continue
                    # Toggle cleanup mode
                    if event.key == pygame.key.key_code(keybindings.get('cleanup_mode', 'u')):
                        self.toggle_cleanup_mode()
                        continue
                    # Toggle help
                    if (event.key == pygame.key.key_code(keybindings['help'])) or (event.key == self.alternate_keys['help']):
                        self.game.help_mode = not self.game.help_mode
                        continue
                    # Toggle color picker
                    if (event.key == pygame.key.key_code(keybindings.get('color_picker', 'c'))) or (event.key == self.alternate_keys.get('color_picker', pygame.K_c)):
                        self.game.color_picker_mode = not self.game.color_picker_mode
                        continue
                    # Cleanup actions only
                    if (('remove_backfaces' in keybindings) and event.key == pygame.key.key_code(keybindings['remove_backfaces'])) or event.key == self.alternate_keys['remove_backfaces']:
                        self.remove_backfacing_triangles()
                        continue
                    if (('check_edge' in keybindings) and event.key == pygame.key.key_code(keybindings['check_edge'])) or event.key == self.alternate_keys['check_edge']:
                        self.check_selected_edge_exists()
                        continue
                    if (('remove_internal_edges' in keybindings) and event.key == pygame.key.key_code(keybindings['remove_internal_edges'])) or event.key == self.alternate_keys['remove_internal_edges']:
                        self.remove_internal_edges_via_raycasts()
                        continue
                    if (('remove_covered' in keybindings) and event.key == pygame.key.key_code(keybindings['remove_covered'])) or event.key == self.alternate_keys['remove_covered']:
                        self.covered_triangle_remover.remove_fully_covered_triangles(self.game)
                        continue
                    if (('show_position_matches' in keybindings) and event.key == pygame.key.key_code(keybindings['show_position_matches'])) or event.key == self.alternate_keys['show_position_matches']:
                        self.show_triangles_matching_selected_positions()
                        continue
                # Swallow all other events while in cleanup mode
                continue
            # While entering a new vertex's coordinates/colors, handle only text/mouse for those fields and QUIT
            if self.game.add_vertex_mode:
                if event.type == pygame.QUIT:
                    continue_running = False
                    continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    x, y = event.pos
                    try:
                        # Allow overriding to multi-select color edit if applicable
                        if len(getattr(self.game, 'selected_vertices', set())) > 1 and \
                           (self.game.edit_color_rect and self.game.edit_color_rect.collidepoint(x, y)):
                            # Exit add mode and enter color-only edit
                            self.game.add_vertex_mode = False
                            self.game.filename_edit_mode = False
                            self.game.edit_mode = True
                            self.game.edit_pos_text = ""
                            try:
                                self.game.edit_color_text = self._fmt_triplet(self.game.current_color)
                            except Exception:
                                self.game.edit_color_text = "[1.000, 1.000, 1.000]"
                            self.game.edit_focus = 'color'
                            continue
                        if self.game.add_vertex_pos_rect and self.game.add_vertex_pos_rect.collidepoint(x, y):
                            self.game.add_vertex_focus = 'pos'
                        elif self.game.add_vertex_color_rect and self.game.add_vertex_color_rect.collidepoint(x, y):
                            self.game.add_vertex_focus = 'color'
                    except Exception:
                        pass
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Cancel add-vertex mode
                        self.game.add_vertex_mode = False
                        self.game.add_vertex_text = ""
                        self.game.add_vertex_pos_text = ""
                        self.game.add_vertex_color_text = ""
                        self.game.add_vertex_error = ""
                        self.game.add_vertex_focus = 'pos'
                        continue
                    if event.key == pygame.K_RETURN:
                        self.apply_add_vertex()
                    elif event.key == pygame.K_TAB:
                        self.game.add_vertex_focus = 'color' if self.game.add_vertex_focus == 'pos' else 'pos'
                    elif event.key == pygame.K_BACKSPACE:
                        if self.game.add_vertex_focus == 'pos':
                            self.game.add_vertex_pos_text = self.game.add_vertex_pos_text[:-1]
                        else:
                            self.game.add_vertex_color_text = self.game.add_vertex_color_text[:-1]
                        self.game.add_vertex_error = ""
                    else:
                        if self.game.add_vertex_focus == 'pos':
                            self.game.add_vertex_pos_text += event.unicode
                        else:
                            self.game.add_vertex_color_text += event.unicode
                        self.game.add_vertex_error = ""
                # Swallow all other events during add-vertex edit mode
                continue
            # While entering extrude offset, disable all other controls except text entry and QUIT
            if self.game.extrude_mode:
                if event.type == pygame.QUIT:
                    continue_running = False
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Cancel extrude mode
                        self.game.extrude_mode = False
                        self.game.extrude_text = ""
                        self.game.extrude_error = ""
                        # Clear extrude base indicators
                        if hasattr(self.game, 'extrude_base_index'):
                            try:
                                delattr(self.game, 'extrude_base_index')
                            except Exception:
                                pass
                        if hasattr(self.game, 'extrude_base_point'):
                            try:
                                delattr(self.game, 'extrude_base_point')
                            except Exception:
                                pass
                        try:
                            self.game.yellow_highlights.clear()
                        except Exception:
                            pass
                        continue
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
                # Allow clicking multi-select color field to exit filename mode and start color edit
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    x, y = event.pos
                    try:
                        if len(getattr(self.game, 'selected_vertices', set())) > 1 and \
                           (self.game.edit_color_rect and self.game.edit_color_rect.collidepoint(x, y)):
                            self.game.filename_edit_mode = False
                            self.game.edit_mode = True
                            self.game.add_vertex_mode = False
                            self.game.edit_pos_text = ""
                            try:
                                self.game.edit_color_text = self._fmt_triplet(self.game.current_color)
                            except Exception:
                                self.game.edit_color_text = "[1.000, 1.000, 1.000]"
                            self.game.edit_focus = 'color'
                            continue
                    except Exception:
                        pass
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Cancel filename edit
                        self.game.filename_edit_mode = False
                        continue
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
                        # Do not open add-vertex fields while multi-select is active
                        if len(self.game.selected_vertices) > 1:
                            pass
                        else:
                            self.game.add_vertex_mode = True
                            # Prefill with last selected vertex coords and current color
                            pos_str, col_str = self._get_add_vertex_default_texts()
                            self.game.add_vertex_pos_text = pos_str
                            self.game.add_vertex_color_text = col_str
                            self.game.add_vertex_error = ""
                            self.game.add_vertex_focus = 'pos'
                            self.mouse_button_rotation_held = False
                            self.rotate_key_held = False
                    # Prioritize multi-select color input click before filename area
                    elif (not self.game.edit_mode) and (len(self.game.selected_vertices) > 1) and \
                         (self.game.edit_color_rect and self.game.edit_color_rect.collidepoint(x, y)):
                        # Enter color-only edit for multi-select; ensure other input modes are off
                        self.game.edit_mode = True
                        self.game.add_vertex_mode = False
                        self.game.filename_edit_mode = False
                        try:
                            self.game.edit_pos_text = ""
                            self.game.edit_color_text = self._fmt_triplet(self.game.current_color)
                        except Exception:
                            self.game.edit_pos_text = ""
                            self.game.edit_color_text = "[1.000, 1.000, 1.000]"
                        self.game.edit_focus = 'color'
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
                            # Establish and show base point used for offset calculation
                            base_idx, base_point = self._get_extrude_base_index_and_point()
                            if base_idx is not None and base_point is not None:
                                self.game.extrude_base_index = base_idx
                                self.game.extrude_base_point = [float(base_point[0]), float(base_point[1]), float(base_point[2])]
                                self.game.yellow_highlights = {base_idx}
                    # When multiple vertices are selected, allow clicking the visible color field
                    # to enter color-only editing directly
                    
                    elif self.game.edit_rect and self.game.edit_rect.collidepoint(x, y) and len(self.game.selected_vertices) >= 1:
                        self.game.edit_mode = True
                        if len(self.game.selected_vertices) == 1:
                            selected = list(self.game.selected_vertices)[0]
                            self._prefill_edit_fields(selected)
                        else:
                            # Multi-select: enable color-only edit; clear position field
                            try:
                                self.game.edit_pos_text = ""
                                self.game.edit_color_text = self._fmt_triplet(self.game.current_color)
                            except Exception:
                                self.game.edit_pos_text = ""
                                self.game.edit_color_text = "[1.000, 1.000, 1.000]"
                            self.game.edit_focus = 'color'
                    elif self.game.edit_mode and self.game.edit_pos_rect and self.game.edit_pos_rect.collidepoint(x, y):
                        self.game.edit_focus = 'pos'
                    elif self.game.edit_mode and self.game.edit_color_rect and self.game.edit_color_rect.collidepoint(x, y):
                        self.game.edit_focus = 'color'
                    elif self.handle_vertex_list_click(x, y, ctrl_pressed):
                        pass # Vertex in the list was clicked, no need to do anything else
                    else:
                        nearest_vertex, ambiguous = self.find_nearest_vertex_with_ambiguity(x, y)
                        if ambiguous and len(ambiguous) > 1:
                            # Start disambiguation modal
                            ctrl_pressed_bool = bool(ctrl_pressed)
                            self.start_disambiguation(ambiguous, ctrl_pressed_bool)
                            # Do not change current selection yet
                            continue
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
                            self._prefill_edit_fields(selected)
                        else:
                            self.game.edit_mode = False
                            self.game.edit_text = ""
                            self.game.edit_pos_text = ""
                            self.game.edit_color_text = ""
                elif event.button == self.rotation_button:
                    self.mouse_button_rotation_held = True

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == self.rotation_button:
                    self.mouse_button_rotation_held = False

            elif event.type == pygame.MOUSEMOTION:
                if (self.mouse_button_rotation_held or self.rotate_key_held) and (not getattr(self.game, 'cleanup_mode', False)):
                    dx, dy = event.rel
                    sensitivity = 0.005  # Adjust sensitivity as needed
                    self.game.camera.yaw(-dx * sensitivity)
                    self.game.camera.pitch(-dy * sensitivity)
            elif event.type == pygame.KEYUP:
                # Release rotation when the configured rotate key is released
                if 'rotate' in keybindings and event.key == pygame.key.key_code(keybindings['rotate']):
                    self.rotate_key_held = False
            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                # Undo: Ctrl+Z or configured key
                if (mods & pygame.KMOD_CTRL) and (event.key == pygame.K_z):
                    self.game.undo_last_action()
                    continue
                if event.key == pygame.key.key_code(keybindings.get('undo', 'z')):
                    self.game.undo_last_action()
                    continue
                # Toggle shapes mode irrespective of other modes except text editing ones handled above
                if event.key == pygame.key.key_code(keybindings.get('shapes_mode', 'm')):
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status("Cleanup Mode is ON. Toggle it off to use Shapes Mode.", 180)
                    else:
                        self.toggle_shapes_mode()
                    continue
                # Toggle Cleanup Mode (only when not in text edit modals handled above)
                if event.key == pygame.key.key_code(keybindings.get('cleanup_mode', 'u')):
                    self.toggle_cleanup_mode()
                    continue
                if self.game.filename_edit_mode:
                    if event.key == pygame.K_RETURN:
                        self.apply_filename_edit()
                    elif event.key == pygame.K_BACKSPACE:
                        self.game.filename_text = self.game.filename_text[:-1]
                    else:
                        self.game.filename_text += event.unicode
                elif self.game.edit_mode:
                    # While editing, only allow: Enter (apply), Escape (cancel), Tab (switch field),
                    # Backspace (edit), Color Picker toggle, Add-Vertex, and text input for the active field.
                    # Swallow all other keys to avoid triggering unrelated actions (e.g., change filename).
                    # Enter -> apply
                    if event.key == pygame.K_RETURN:
                        self.apply_edit()
                        continue
                    # Backspace -> edit
                    if event.key == pygame.K_BACKSPACE:
                        if self.game.edit_focus == 'pos':
                            self.game.edit_pos_text = self.game.edit_pos_text[:-1]
                        else:
                            self.game.edit_color_text = self.game.edit_color_text[:-1]
                        continue
                    # Delete -> delete currently selected vertices even while editing
                    if event.key == pygame.K_DELETE:
                        self.delete_selected_vertices()
                        continue
                    # Tab -> switch field
                    if event.key == pygame.K_TAB:
                        self.game.edit_focus = 'color' if self.game.edit_focus == 'pos' else 'pos'
                        continue
                    # Escape -> cancel edit
                    if event.key == pygame.K_ESCAPE:
                        self.game.edit_mode = False
                        self.game.edit_text = ""
                        self.game.edit_pos_text = ""
                        self.game.edit_color_text = ""
                        continue
                    # Color Picker toggle while editing
                    try:
                        if (('color_picker' in keybindings) and event.key == pygame.key.key_code(keybindings['color_picker'])) or \
                           (event.key == self.alternate_keys.get('color_picker', -1)):
                            # Ensure filename editor is closed to prevent conflicts
                            self.game.filename_edit_mode = False
                            self.game.color_picker_mode = not self.game.color_picker_mode
                            # Keep edit mode active
                            self.game.edit_mode = True
                            continue
                    except Exception:
                        pass
                    # Add-vertex key while editing (allowed)
                    try:
                        if (event.key == pygame.key.key_code(keybindings.get('add_vertex', 'insert'))) or \
                           (event.key == self.alternate_keys.get('add_vertex', -1)):
                            self.game.add_vertex_mode = True
                            pos_str, col_str = self._get_add_vertex_default_texts()
                            self.game.add_vertex_pos_text = pos_str
                            # Prefill color with current field text if non-empty, else use default
                            self.game.add_vertex_color_text = (self.game.edit_color_text or col_str)
                            self.game.add_vertex_error = ""
                            self.game.add_vertex_focus = 'pos'
                            self.mouse_button_rotation_held = False
                            self.rotate_key_held = False
                            continue
                    except Exception:
                        pass
                    # Default: treat as text input for the active field and swallow the key
                    if event.unicode:
                        if self.game.edit_focus == 'pos':
                            self.game.edit_pos_text += event.unicode
                        else:
                            self.game.edit_color_text += event.unicode
                    continue
                # Fallback: if Enter is pressed with one selected vertex and pending edit fields,
                # apply the edit even if edit_mode was toggled off unexpectedly.
                elif event.key == pygame.K_RETURN:
                    try:
                        if (len(getattr(self.game, 'selected_vertices', set())) == 1) and \
                           ((self.game.edit_pos_text or '').strip() or (self.game.edit_color_text or '').strip()):
                            self.apply_edit()
                            continue
                    except Exception:
                        pass
                # Only allow deletion when not in any text-editing mode
                if not (self.game.filename_edit_mode or self.game.add_vertex_mode or self.game.edit_mode):
                    if event.key == pygame.K_DELETE:
                        self.delete_selected_vertices()
                    # Clear all vertices via configured key (e.g., X)
                    if 'clear_vertices' in keybindings and event.key == pygame.key.key_code(keybindings['clear_vertices']):
                        self.clear_all_vertices()
                # Press-and-hold keyboard rotate key acts like holding the mouse rotation button
                # Do not engage rotate when in shapes mode to allow key reuse (e.g., 'r' for Rectangle)
                if 'rotate' in keybindings and event.key == pygame.key.key_code(keybindings['rotate']):
                    if not getattr(self.game, 'shapes_mode', False) and not getattr(self.game, 'cleanup_mode', False):
                        self.rotate_key_held = True
                # Shape entry hotkeys only active when shapes mode is enabled
                if getattr(self.game, 'shapes_mode', False):
                    if event.key == pygame.key.key_code(keybindings.get('shape_rectangle', 'r')):
                        self.start_rectangle_flow()
                        continue
                    if event.key == pygame.key.key_code(keybindings.get('shape_ngon', 'g')):
                        self.start_ngon_flow()
                        continue

                if (event.key == pygame.key.key_code(keybindings['add_vertex']) or event.key == self.alternate_keys['add_vertex']):
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status(f"Cleanup Mode is ON. Toggle it off with {keybindings.get('cleanup_mode','u').upper()} to add vertices.", 240)
                        continue
                    # Enter add-vertex input mode; prefill from last selected when possible
                    self.game.add_vertex_mode = True
                    pos_str, col_str = self._get_add_vertex_default_texts()
                    self.game.add_vertex_pos_text = pos_str
                    self.game.add_vertex_color_text = col_str
                    self.game.add_vertex_error = ""
                    self.game.add_vertex_focus = 'pos'
                    self.mouse_button_rotation_held = False
                    self.rotate_key_held = False
                if event.key == pygame.key.key_code(keybindings['save_vertices']) or event.key == self.alternate_keys['save_vertices']:
                    self.save_vertices()
                if (('extrude' in keybindings) and event.key == pygame.key.key_code(keybindings['extrude'])):
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status(f"Cleanup Mode is ON. Toggle it off with {keybindings.get('cleanup_mode','u').upper()} to extrude.", 240)
                        continue
                    if len(self.game.selected_vertices) == 0:
                        self.game.set_status("Select vertices to extrude", 180)
                    else:
                        self.game.extrude_mode = True
                        self.game.extrude_text = self._get_add_vertex_default_text()
                        self.game.extrude_error = ""
                        self.mouse_button_rotation_held = False
                        self.rotate_key_held = False
                        # Establish and show base point used for offset calculation
                        base_idx, base_point = self._get_extrude_base_index_and_point()
                        if base_idx is not None and base_point is not None:
                            self.game.extrude_base_index = base_idx
                            self.game.extrude_base_point = [float(base_point[0]), float(base_point[1]), float(base_point[2])]
                            self.game.yellow_highlights = {base_idx}
                if event.key == pygame.key.key_code(keybindings['change_filename']) or event.key == self.alternate_keys['change_filename']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status(f"Cleanup Mode is ON. Toggle it off with {keybindings.get('cleanup_mode','u').upper()} to edit filename.", 240)
                        continue
                    self.game.filename_edit_mode = True
                    self.game.filename_edit_purpose = 'save'
                    self.mouse_button_rotation_held = False
                    self.rotate_key_held = False
                if (('new_file' in keybindings) and event.key == pygame.key.key_code(keybindings['new_file'])) or event.key == self.alternate_keys['new_file']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status(f"Cleanup Mode is ON. Toggle it off with {keybindings.get('cleanup_mode','u').upper()} to create a new file.", 240)
                        continue
                    self.game.filename_edit_mode = True
                    self.game.filename_edit_purpose = 'new'
                    self.mouse_button_rotation_held = False
                    self.rotate_key_held = False
                if (('open_file' in keybindings) and event.key == pygame.key.key_code(keybindings['open_file'])) or event.key == self.alternate_keys['open_file']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status(f"Cleanup Mode is ON. Toggle it off with {keybindings.get('cleanup_mode','u').upper()} to open files.", 240)
                        continue
                    self.start_file_picker()
                    self.mouse_button_rotation_held = False
                    self.rotate_key_held = False
                if event.key == pygame.key.key_code(keybindings['form_triangles']) or event.key == self.alternate_keys['form_triangles']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status(f"Cleanup Mode is ON. Toggle it off with {keybindings.get('cleanup_mode','u').upper()} to form triangles.", 240)
                        continue
                    self.triangle_filler.form_triangles_from_selected()
                if (('remove_backfaces' in keybindings) and event.key == pygame.key.key_code(keybindings['remove_backfaces'])) or event.key == self.alternate_keys['remove_backfaces']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.remove_backfacing_triangles()
                    else:
                        self.game.set_status(f"Cleanup tools are in Cleanup Mode. Press {keybindings.get('cleanup_mode','u').upper()} to toggle.", 240)
                if event.key == pygame.key.key_code(keybindings['forward']) or event.key == self.alternate_keys['forward']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status("Movement disabled in Cleanup Mode.", 120)
                        continue
                    if self.game.relative_movement:
                        self.game.camera.relative_forward()
                    else:
                        self.game.camera.forward()
                if event.key == pygame.key.key_code(keybindings['backward']) or event.key == self.alternate_keys['backward']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status("Movement disabled in Cleanup Mode.", 120)
                        continue
                    if self.game.relative_movement:
                        self.game.camera.relative_backward()
                    else:
                        self.game.camera.backward()
                if event.key == pygame.key.key_code(keybindings['left']) or event.key == self.alternate_keys['left']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status("Movement disabled in Cleanup Mode.", 120)
                        continue
                    if self.game.relative_movement:
                        self.game.camera.relative_left()
                    else:
                        self.game.camera.left()
                if event.key == pygame.key.key_code(keybindings['right']) or event.key == self.alternate_keys['right']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status("Movement disabled in Cleanup Mode.", 120)
                        continue
                    if self.game.relative_movement:
                        self.game.camera.relative_right()
                    else:
                        self.game.camera.right()
                if event.key == pygame.key.key_code(keybindings['up']) or event.key == self.alternate_keys['up']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status("Movement disabled in Cleanup Mode.", 120)
                        continue
                    if self.game.relative_movement:
                        self.game.camera.relative_upwards()
                    else:
                        self.game.camera.upwards()
                if event.key == pygame.key.key_code(keybindings['down']) or event.key == self.alternate_keys['down']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.game.set_status("Movement disabled in Cleanup Mode.", 120)
                        continue
                    if self.game.relative_movement:
                        self.game.camera.relative_downwards()
                    else:
                        self.game.camera.downwards()
                if event.key == pygame.key.key_code(keybindings['yaw_left']) or event.key == self.alternate_keys['yaw_left']:
                    if getattr(self.game, 'cleanup_mode', False):
                        continue
                    self.game.camera.yaw(self.rotation_speed)
                if event.key == pygame.key.key_code(keybindings['yaw_right']) or event.key == self.alternate_keys['yaw_right']:
                    if getattr(self.game, 'cleanup_mode', False):
                        continue
                    self.game.camera.yaw(-self.rotation_speed)
                if event.key == pygame.key.key_code(keybindings['pitch_up']) or event.key == self.alternate_keys['pitch_up']:
                    if getattr(self.game, 'cleanup_mode', False):
                        continue
                    self.game.camera.pitch(self.rotation_speed)
                if event.key == pygame.key.key_code(keybindings['pitch_down']) or event.key == self.alternate_keys['pitch_down']:
                    if getattr(self.game, 'cleanup_mode', False):
                        continue
                    self.game.camera.pitch(-self.rotation_speed)
                if event.key == pygame.key.key_code(keybindings['toggle_wireframe']) or event.key == self.alternate_keys['toggle_wireframe']:
                    if getattr(self.game, 'cleanup_mode', False):
                        continue
                    self.game.renderer.renderer3D.toggle_wireframe()
                if event.key == pygame.key.key_code(keybindings['help']) or event.key == self.alternate_keys['help']:
                    self.game.help_mode = not self.game.help_mode
                # Toggle color picker
                if event.key == pygame.key.key_code(keybindings.get('color_picker', 'c')) or event.key == self.alternate_keys.get('color_picker', pygame.K_c):
                    self.game.color_picker_mode = not self.game.color_picker_mode
                if (('check_edge' in keybindings) and event.key == pygame.key.key_code(keybindings['check_edge'])) or event.key == self.alternate_keys['check_edge']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.check_selected_edge_exists()
                    else:
                        self.game.set_status(f"Cleanup tools are in Cleanup Mode. Press {keybindings.get('cleanup_mode','u').upper()} to toggle.", 240)
                if (('remove_internal_edges' in keybindings) and event.key == pygame.key.key_code(keybindings['remove_internal_edges'])) or event.key == self.alternate_keys['remove_internal_edges']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.remove_internal_edges_via_raycasts()
                    else:
                        self.game.set_status(f"Cleanup tools are in Cleanup Mode. Press {keybindings.get('cleanup_mode','u').upper()} to toggle.", 240)
                if (('remove_covered' in keybindings) and event.key == pygame.key.key_code(keybindings['remove_covered'])) or event.key == self.alternate_keys['remove_covered']:
                    if getattr(self.game, 'cleanup_mode', False):
                        self.covered_triangle_remover.remove_fully_covered_triangles(self.game)
                    else:
                        self.game.set_status(f"Cleanup tools are in Cleanup Mode. Press {keybindings.get('cleanup_mode','u').upper()} to toggle.", 240)
            elif event.type == pygame.MOUSEWHEEL:
                self.handle_scroll(event.y)
        
        return continue_running 

    def _get_add_vertex_default_text(self):
        return self.vertex_editor.get_add_vertex_default_text()

    def _fmt_triplet(self, values) -> str:
        return self.vertex_editor.fmt_triplet(values)

    def _get_add_vertex_default_texts(self):
        return self.vertex_editor.get_add_vertex_default_texts()

    def _prefill_edit_fields(self, selected_index:int):
        return self.vertex_editor.prefill_edit_fields(selected_index)

    def _get_default_shape_point_text(self):
        return self.shapes_controller.get_default_shape_point_text()

    # ===================== Shapes Mode / Input Flow =====================
    def toggle_shapes_mode(self):
        return self.shapes_controller.toggle_shapes_mode()

    def cancel_shape_flow(self, clear_error:bool=False):
        return self.shapes_controller.cancel_shape_flow(clear_error=clear_error)

    def start_rectangle_flow(self):
        return self.shapes_controller.start_rectangle_flow()

    def start_ngon_flow(self):
        return self.shapes_controller.start_ngon_flow()

    def backspace_shape_text(self):
        return self.shapes_controller.backspace_shape_text()

    def append_shape_text(self, ch:str):
        return self.shapes_controller.append_shape_text(ch)

    def apply_shape_step(self):
        return self.shapes_controller.apply_shape_step()

    def _commit_rectangle(self):
        # Snapshot before mutating geometry
        self.game.push_undo_snapshot("Add rectangle")
        # Avoid corrupting triangle grouping if there are stray vertices at the end
        self._drop_trailing_incomplete_vertices()
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
        # Ensure rotation states are cleared after shape commit
        self.mouse_button_rotation_held = False
        self.rotate_key_held = False
        self.cancel_shape_flow(clear_error=True)

    def _commit_ngon(self):
        # Snapshot before mutating geometry
        try:
            n = int(self._shape_tmp_sides)
        except Exception:
            n = None
        self.game.push_undo_snapshot(f"Add {n}-gon" if n is not None else "Add n-gon")
        # Avoid corrupting triangle grouping if there are stray vertices at the end
        self._drop_trailing_incomplete_vertices()
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
        # Ensure rotation states are cleared after shape commit
        self.mouse_button_rotation_held = False
        self.rotate_key_held = False
        self.cancel_shape_flow(clear_error=True)

    def _append_vertex_with_color(self, pos_tuple, color_rgb):
        x, y, z = float(pos_tuple[0]), float(pos_tuple[1]), float(pos_tuple[2])
        new_vertex = [x, y, z] + list(color_rgb)
        from src.geometry.VerticesHolder import verticesHolder
        verticesHolder.vertices = np.append(verticesHolder.vertices, new_vertex).astype('f4')

    def _parse_number(self, text_value:str) -> float:
        s = (text_value or '').strip()
        # Accept bare numbers like 10 or 10.5
        try:
            val = ast.literal_eval(s)
            if isinstance(val, (int, float)):
                return float(val)
        except Exception:
            pass
        try:
            return float(s)
        except Exception:
            raise ValueError("Enter a numeric value (e.g., 10 or 10.5)")

    def _drop_trailing_incomplete_vertices(self) -> int:
        """Trim trailing stray vertex rows so total rows is a multiple of 3.
        Returns number of rows dropped.
        """
        try:
            rows_count = len(verticesHolder.vertices) // 6
            remainder = rows_count % 3
            if remainder == 0:
                return 0
            if rows_count - remainder <= 0:
                verticesHolder.vertices = np.array([], dtype='f4')
                return remainder
            rows = verticesHolder.vertices.reshape(-1, 6)
            kept = rows[: rows_count - remainder]
            verticesHolder.vertices = kept.astype('f4').flatten()
            return remainder
        except Exception:
            return 0

    def _commit_rectangle_from_two_vertices(self):
        # Snapshot before mutating geometry
        self.game.push_undo_snapshot("Add rectangle (2 vertices)")
        try:
            p0 = np.array(self._shape_edge_p0, dtype=float)
            p1 = np.array(self._shape_edge_p1, dtype=float)
            dim = float(self._shape_tmp_dim)
            dir_pt = np.array(self._shape_tmp_direction_point, dtype=float)
        except Exception:
            self.game.shape_error = "Invalid temporary state for rectangle"
            return

        # Avoid corrupting triangle grouping if there are stray vertices at the end
        self._drop_trailing_incomplete_vertices()

        e = p1 - p0
        e_len2 = float(np.dot(e, e))
        if e_len2 <= 1e-12:
            self.game.shape_error = "Selected edge too small"
            return

        # Vector from p0 towards direction point, remove component along edge to get perpendicular in plane
        v = dir_pt - p0
        proj_scale = float(np.dot(v, e)) / e_len2
        d_perp = v - proj_scale * e
        if np.linalg.norm(d_perp) <= 1e-9:
            # Direction is colinear with the edge; abort with clear error instead of guessing
            self.game.shape_error = (
                f"Direction point is colinear with the selected edge; pick a non-colinear point. "
                f"Edge: [{float(p0[0]):.3f}, {float(p0[1]):.3f}, {float(p0[2]):.3f}] -> "
                f"[{float(p1[0]):.3f}, {float(p1[1]):.3f}, {float(p1[2]):.3f}], "
                f"Dir: [{float(dir_pt[0]):.3f}, {float(dir_pt[1]):.3f}, {float(dir_pt[2]):.3f}]"
            )
            return

        d_perp_norm = np.linalg.norm(d_perp)
        if d_perp_norm <= 1e-12:
            self.game.shape_error = "Could not determine perpendicular direction"
            return

        # Normalize d_perp and scale by requested dimension
        offset = (dim / d_perp_norm) * d_perp

        q0 = p0
        q1 = p1
        q2 = p1 + offset
        q3 = p0 + offset

        color = self.game.random_color()
        # Two triangles (q0, q1, q2) and (q0, q2, q3)
        self._append_vertex_with_color(q0, color)
        self._append_vertex_with_color(q1, color)
        self._append_vertex_with_color(q2, color)
        self._append_vertex_with_color(q0, color)
        self._append_vertex_with_color(q2, color)
        self._append_vertex_with_color(q3, color)

        # Ensure new vertices are float32 and update buffer
        self.game.renderer.renderer3D.update_vertex_buffer()
        self.game.set_status("Rectangle added (from 2 vertices)", 180)
        # Ensure rotation states are cleared after shape commit
        self.mouse_button_rotation_held = False
        self.rotate_key_held = False
        self.cancel_shape_flow(clear_error=True)

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
        return self.selection_controller.find_nearest_vertex(x, y)

    def find_nearest_vertex_with_ambiguity(self, x, y):
        return self.selection_controller.find_nearest_vertex_with_ambiguity(x, y)

    def _pt_sub(self, a, b):
        return self.selection_controller._pt_sub(a, b)

    def _cross(self, a, b):
        return self.selection_controller._cross(a, b)

    def _same_side(self, p1, p2, a, b):
        return self.selection_controller._same_side(p1, p2, a, b)

    def _point_in_triangle(self, p, a, b, c):
        return self.selection_controller.point_in_triangle(p, a, b, c)

    def _barycentric_weights(self, p, a, b, c):
        return self.selection_controller.barycentric_weights(p, a, b, c)

    def start_disambiguation(self, candidates:list, ctrl_pressed:bool):
        return self.selection_controller.start_disambiguation(candidates, ctrl_pressed)

    def _end_disambiguation(self, chosen_index:int|None):
        return self.selection_controller.end_disambiguation(chosen_index)

    def apply_edit(self):
        return self.vertex_editor.apply_edit()

    def apply_add_vertex(self):
        return self.vertex_editor.apply_add_vertex()

    def _remove_trailing_duplicate_vertices(self) -> int:
        return self.vertex_editor.remove_trailing_duplicate_vertices()

    def add_vertex(self, x:float, y:float, z:float):
        return self.vertex_editor.add_vertex(x, y, z)

    def apply_extrude(self):
        return self.extrude_controller.apply_extrude()

    def _get_extrude_base_index_and_point(self):
        return self.extrude_controller.get_extrude_base_index_and_point()

    def save_vertices(self):
        return self.file_controller.save_vertices()

    def apply_filename_edit(self):
        return self.file_controller.apply_filename_edit()

    def _normalize_file_input(self, text: str) -> str:
        return self.file_controller.normalize_file_input(text)

    def _open_vertices_file(self, path: str):
        return self.file_controller.open_vertices_file(path)

    def start_file_picker(self):
        return self.file_controller.start_file_picker()

    def handle_vertex_list_click(self, x, y, ctrl_pressed):
        return self.selection_controller.handle_vertex_list_click(x, y, ctrl_pressed)

    def handle_scroll(self, y):
        return self.selection_controller.handle_scroll(y)

    def remove_backfacing_triangles(self):
        return self.backface_triangle_fixer.fix_backfaces_and_remove_duplicates(self.game)

    def toggle_cleanup_mode(self):
        return self.cleanup_mode_controller.toggle_cleanup_mode()

    def show_triangles_matching_selected_positions(self):
        return self.position_match_inspector.show_triangles_matching_selected_positions(self.game)

    def check_selected_edge_exists(self):
        return self.edge_existence_checker.check_selected_edge_exists(self.game)

    def remove_internal_edges_via_raycasts(self):
        return self.internal_edge_remover.remove_internal_edges_via_raycasts(self.game)

    

    def delete_selected_vertices(self):
        return self.vertex_editor.delete_selected_vertices()

    def clear_all_vertices(self):
        return self.vertex_editor.clear_all_vertices()