import os
import numpy as np

from src.geometry.VerticesHolder import verticesHolder
from src.geometry.loader import load_vertices_from_file
from src.configuration.session_store import set_last_file


class FileController:
    """File open/save and file picker helpers extracted from EventHandler."""

    def __init__(self, game):
        self.game = game

    def normalize_file_input(self, text: str) -> str:
        s = (text or '').strip()
        if not s:
            return s
        return os.path.normpath(s)

    def open_vertices_file(self, path: str):
        print(f"Opening file: {path}")
        try:
            loaded = load_vertices_from_file(path)
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
            print(f"Loaded vertices from {path}: count={(len(verticesHolder.vertices)//6)}")
            set_last_file(path)
        except Exception as e:
            print(f"Error opening {path}: {e}")

    def save_vertices(self):
        try:
            normalized = self.normalize_file_input(self.game.filename_text)
            if normalized:
                self.game.filename_text = normalized
            filename = normalized or self.game.filename_text
            if filename:
                if os.path.isdir(filename):
                    filename = os.path.join(filename, 'untitled.vertices')
                root, ext = os.path.splitext(filename)
                if not ext:
                    filename = filename + '.vertices'
                self.game.filename_text = filename
        except Exception:
            filename = self.game.filename_text
        vertices = verticesHolder.vertices.reshape(-1, 6)
        with open(filename, 'w') as file:
            for vertex in vertices:
                file.write(f"{' '.join(map(str, vertex))}\n")
        print(f"Vertices saved to {filename}")

    def apply_filename_edit(self):
        self.game.filename_edit_mode = False
        try:
            normalized = self.normalize_file_input(self.game.filename_text)
            if normalized:
                self.game.filename_text = normalized
        except Exception:
            pass
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
                self.game.last_selected_vertex_index = None
        elif purpose == 'open':
            self.open_vertices_file(self.game.filename_text)
            self.game.filename_edit_purpose = 'save'
            self.game.last_selected_vertex_index = None
        else:
            print(f"Save filename set to: {self.game.filename_text}")
            try:
                self.save_vertices()
                set_last_file(self.game.filename_text)
            except Exception as e:
                print(f"Error saving to {self.game.filename_text}: {e}")

    def start_file_picker(self):
        try:
            current = self.game.filename_text or ""
            normalized = self.normalize_file_input(current)
            current = normalized if normalized else current
        except Exception:
            current = ""
        directory = None
        if current:
            if os.path.isdir(current):
                directory = current
            else:
                directory = os.path.dirname(current)
        if not directory:
            try:
                this_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(this_dir))
                fallback = os.path.join(project_root, 'assets')
                directory = fallback if os.path.isdir(fallback) else os.getcwd()
            except Exception:
                directory = os.getcwd()
        try:
            entries = os.listdir(directory)
        except Exception:
            entries = []
        full_paths = []
        for name in sorted(entries, key=lambda n: n.lower()):
            fp = os.path.join(directory, name)
            if os.path.isfile(fp):
                full_paths.append(fp)
        vertices_files = [p for p in full_paths if p.lower().endswith('.vertices')]
        items = vertices_files if vertices_files else full_paths
        self.game.file_picker_dir = directory
        self.game.file_picker_items = items
        try:
            idx = items.index(current) if current in items else 0
        except Exception:
            idx = 0
        if items:
            self.game.file_picker_index = max(0, min(len(items) - 1, idx))
            self.game.file_picker_scroll = max(0, self.game.file_picker_index - (self.game.file_picker_max_visible // 2))
        else:
            self.game.file_picker_index = 0
            self.game.file_picker_scroll = 0
        self.game.file_picker_item_rects = []
        self.game.file_picker_mode = True


