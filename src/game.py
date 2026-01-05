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
        # Triangle selection tool state (separate from vertex selection)
        self.triangle_select_mode = False
        self.selected_triangles = set()  # set[int] of triangle indices (0-based)
        self.last_selected_triangle_index = None
        self.triangle_highlights = set()  # set[int] vertex indices to highlight in the vertex list/screen
        self.triangle_item_rects = []  # list of (triangle_index:int, rect:pygame.Rect) for click detection
        self.edit_mode = False
        self.edit_text = ""
        self.edit_rect = pygame.Rect(10, self.height - 35, 290, 30)
        # Two-field edit support: position and color
        self.edit_pos_text = ""
        self.edit_color_text = ""
        self.edit_pos_rect = self.edit_rect
        self.edit_color_rect = pygame.Rect(10, self.height - 70, 290, 30)
        self.edit_focus = 'pos'  # 'pos' | 'color'
        self.edit_error = ""
        # Add-vertex editing variables
        self.add_vertex_mode = False
        self.add_vertex_text = ""
        self.add_vertex_rect = pygame.Rect(10, self.height - 105, 350, 30)
        # Two-field add support: position and color
        self.add_vertex_pos_text = ""
        self.add_vertex_color_text = ""
        self.add_vertex_pos_rect = self.add_vertex_rect
        self.add_vertex_color_rect = pygame.Rect(10, self.height - 70, 350, 30)
        self.add_vertex_focus = 'pos'  # 'pos' | 'color'
        self.add_vertex_placeholder_active = False
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
        # Transient status message shown on-screen (text, frames_remaining)
        self.status_message = ("", 0)
        # Remember the last vertex index the user interacted with
        self.last_selected_vertex_index = None
        # Extrusion mode input state
        self.extrude_mode = False
        self.extrude_text = ""
        self.extrude_rect = pygame.Rect(370, self.height - 105, 350, 30)
        self.extrude_error = ""

        # Shapes mode and input state
        self.shapes_mode = False
        # None | 'rectangle' | 'ngon'
        self.shape_input_mode = None
        # Steps within a given shape flow, e.g. 'point', 'width', 'length', 'sides'
        self.shape_step = None
        self.shape_primary_text = ""
        self.shape_secondary_text = ""
        self.shape_error = ""
        # UI rects for shape input fields (placed to the right of extrude)
        self.shape_primary_rect = pygame.Rect(730, self.height - 105, 300, 30)
        self.shape_secondary_rect = pygame.Rect(1040, self.height - 105, 220, 30)

        from src.event_handler import EventHandler
        self.event_handler = EventHandler(self)

        # Undo state
        self._undo_stack = []
        self._undo_stack_limit = 50

        # File picker state
        self.file_picker_mode = False
        
        # Color picker state
        self.color_picker_mode = False
        self.color_picker_rects = []  # List of (rect, color_name) tuples for color selection
        self.file_picker_dir = ""
        self.file_picker_items = []  # full paths
        self.file_picker_index = 0
        self.file_picker_scroll = 0
        self.file_picker_max_visible = 12
        self.file_picker_item_rects = []

        # Disambiguation (ambiguous vertex pick) modal state
        self.disambiguation_mode = False
        # Kind: 'vertex' (existing) or 'triangle' (triangle select tool)
        self.disambiguation_kind = 'vertex'
        self.disambiguation_candidates = []  # list[int] indices (vertex or triangle depending on kind)
        self.disambiguation_selected = 0
        self.disambiguation_item_rects = []
        self.disambiguation_ctrl_pressed = False
        self.disambiguation_triangles = []  # list of {candidate:int, triangle_index:int, screen_pts:[(x,y)*3], color:(r,g,b,a)}
        self.disambiguation_prev_selection = set()
        self.disambiguation_action = None  # 'toggle' or 'replace'

        # Cleanup mode state
        self.cleanup_mode = False
        # Overlays for cleanup inspection (triangles sharing selected positions)
        self.cleanup_position_overlays = []
        # Wireframe overlays for non-matching triangles during cleanup inspection
        self.cleanup_position_wireframes = []
        # Debug overlays for internal-triangle inspection (centroid ray checks)
        # Each entry: {'origin':[x,y,z], 'end':[x,y,z], 'hits':int, 'reason':str, 'color':(r,g,b,a)}
        self.internal_triangle_debug_rays = []
        self.internal_triangle_debug_triangle = None  # triangle index inspected
        self.internal_triangle_debug_lines = []  # list[str] summary lines to show on-screen
        
        # Predefined colors (RGB values 0.0-1.0)
        self.predefined_colors = {
            'red': [1.0, 0.0, 0.0],
            'green': [0.0, 1.0, 0.0], 
            'blue': [0.0, 0.0, 1.0],
            'yellow': [1.0, 1.0, 0.0],
            'cyan': [0.0, 1.0, 1.0],
            'magenta': [1.0, 0.0, 1.0],
            'white': [1.0, 1.0, 1.0],
            'black': [0.0, 0.0, 0.0],
            'orange': [1.0, 0.5, 0.0],
            'purple': [0.5, 0.0, 1.0],
            'pink': [1.0, 0.75, 0.8],
            'brown': [0.6, 0.3, 0.0],
            'gray': [0.5, 0.5, 0.5],
            'dark_red': [0.5, 0.0, 0.0],
            'dark_green': [0.0, 0.5, 0.0],
            'dark_blue': [0.0, 0.0, 0.5]
        }

    def random_color(self):
        return [random.random() for _ in range(3)]
    
    def get_predefined_color(self, color_name):
        """Get predefined color by name, or return random color if not found."""
        return self.predefined_colors.get(color_name, self.random_color())

    def run(self):
        running = True
        while running:
            running = self.event_handler.handle_events()
            self.tick_status()
            self.renderer.render()
        pygame.quit()

    def set_status(self, text:str, frames:int=180):
        # ~3 seconds at 60 FPS by default
        self.status_message = (str(text), int(max(1, frames)))

    def tick_status(self):
        text, frames = self.status_message
        if frames > 0:
            self.status_message = (text, frames - 1)

    # ===================== Undo support =====================
    def push_undo_snapshot(self, reason:str=""):
        try:
            # Snapshot essential mutable state
            snapshot = {
                'vertices': np.copy(verticesHolder.vertices),
                'selected_vertices': set(self.selected_vertices),
                'selected_triangles': set(self.selected_triangles),
                'current_color': list(self.current_color) if isinstance(self.current_color, (list, tuple)) else self.current_color,
                'scroll_offset': int(self.uiOverlayCreator.scroll_offset),
                'yellow_highlights': set(self.yellow_highlights),
                'triangle_highlights': set(self.triangle_highlights),
                'last_selected_vertex_index': self.last_selected_vertex_index,
                'last_selected_triangle_index': self.last_selected_triangle_index,
                'reason': str(reason) if reason else "",
            }
            self._undo_stack.append(snapshot)
            if len(self._undo_stack) > self._undo_stack_limit:
                # Drop oldest
                self._undo_stack.pop(0)
        except Exception as _:
            # Best-effort; do not crash if snapshot fails
            pass

    def undo_last_action(self):
        if not self._undo_stack:
            self.set_status("Nothing to undo", 120)
            return
        snapshot = self._undo_stack.pop()
        try:
            # Restore vertices and UI-related state
            verticesHolder.vertices = snapshot.get('vertices', np.array([], dtype='f4')).astype('f4')
            self.selected_vertices = snapshot.get('selected_vertices', set())
            self.selected_triangles = snapshot.get('selected_triangles', set())
            self.current_color = snapshot.get('current_color', self.random_color())
            self.uiOverlayCreator.scroll_offset = int(snapshot.get('scroll_offset', 0))
            self.yellow_highlights = snapshot.get('yellow_highlights', set())
            self.last_selected_vertex_index = snapshot.get('last_selected_vertex_index', None)
            self.triangle_highlights = snapshot.get('triangle_highlights', set())
            self.last_selected_triangle_index = snapshot.get('last_selected_triangle_index', None)

            # Clear transient editing modes
            self.add_vertex_mode = False
            self.add_vertex_text = ""
            self.add_vertex_error = ""
            self.edit_mode = False
            self.edit_text = ""
            self.extrude_mode = False
            self.extrude_text = ""
            self.extrude_error = ""
            # Clear transient modal/tool UI state
            self.disambiguation_mode = False
            self.disambiguation_triangles = []
            self.disambiguation_candidates = []
            self.disambiguation_item_rects = []
            self.triangle_item_rects = []

            # Update GPU buffer after restoration
            self.renderer.renderer3D.update_vertex_buffer()

            reason = snapshot.get('reason', '')
            self.set_status(f"Undid: {reason}" if reason else "Undid last action", 150)
        except Exception as _:
            # If restore fails, keep going but at least avoid crash
            self.set_status("Undo failed", 150)