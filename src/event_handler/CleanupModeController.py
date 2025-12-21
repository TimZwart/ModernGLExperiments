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

    def toggle_cleanup_mode(self):
        # Exit conflicting modes when entering cleanup
        self.game.cleanup_mode = not self.game.cleanup_mode
        # Clear any cleanup inspection overlays whenever the mode toggles
        self.game.cleanup_position_overlays = []
        self.game.cleanup_position_wireframes = []
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
            self.game.set_status("Cleanup Mode ON", 120)
        else:
            self.game.set_status("Cleanup Mode OFF", 120)


