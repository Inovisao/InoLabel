from app.annotation.ui.mode_toggles import ModeTogglesMixin


class OBBModeTogglesMixin(ModeTogglesMixin):
    def toggle_edit_id_mode(self):
        print("[INFO] O modo OBB MVP nao usa edicao de ID.")
