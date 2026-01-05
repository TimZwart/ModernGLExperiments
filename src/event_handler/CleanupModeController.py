class CleanupModeController:
    """Toggle and enter/exit behavior for Cleanup Mode, extracted from EventHandler."""

    def __init__(self, game, clear_rotation_state=None, cancel_shape_flow=None):
        self.game = game
        self.clear_rotation_state = clear_rotation_state
        self.cancel_shape_flow = cancel_shape_flow

    def _clear_rotation(self):
        try:
            if callable(self.clear_rotation_state):
                self.clear_rotation_state()
        except Exception:
            pass

    def toggle_cleanup_mode(self, preserve_internal_triangle_debug: bool = False, keep_status: bool = False):
        # Exit conflicting modes when entering cleanup
        self.game.cleanup_mode = not self.game.cleanup_mode
        # Clear any cleanup inspection overlays whenever the mode toggles
        self.game.cleanup_position_overlays = []
        self.game.cleanup_position_wireframes = []
        # Clear internal-triangle inspection debug overlays:
        # - Always clear when ENTERING cleanup (fresh start)
        # - When EXITING cleanup, keep them if requested (so user can move camera around and inspect)
        try:
            entering = bool(self.game.cleanup_mode)
            if entering or (not preserve_internal_triangle_debug):
                self.game.internal_triangle_debug_rays = []
                self.game.internal_triangle_debug_triangle = None
                self.game.internal_triangle_debug_lines = []
        except Exception:
            pass
        if self.game.cleanup_mode:
            # Clear text edit modes and rotation states
            self.game.add_vertex_mode = False
            self.game.filename_edit_mode = False
            self.game.edit_mode = False
            self.game.extrude_mode = False
            # Exit shapes mode and clear any shape flow
            if getattr(self.game, 'shapes_mode', False):
                try:
                    if callable(self.cancel_shape_flow):
                        self.cancel_shape_flow(clear_error=True)
                except Exception:
                    pass
                self.game.shapes_mode = False
            self._clear_rotation()
            if not keep_status:
                self.game.set_status("Cleanup Mode ON", 120)
        else:
            if not keep_status:
                self.game.set_status("Cleanup Mode OFF", 120)


