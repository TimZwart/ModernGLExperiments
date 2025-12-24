class DeselectController:
    """
    Handles deselecting all currently selected vertices.
    """

    def __init__(self, game):
        self.game = game

    def deselect_all_vertices(self):
        """
        Clear all selected vertices.
        """
        try:
            self.game.selected_vertices.clear()
            self.game.edit_mode = False
            self.game.edit_text = ""
            self.game.edit_pos_text = ""
            self.game.edit_color_text = ""
            self.game.set_status("All vertices deselected", 120)
        except Exception as e:
            print(f"Error deselecting vertices: {e}")
