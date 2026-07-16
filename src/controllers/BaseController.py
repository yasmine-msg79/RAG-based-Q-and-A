from helpers.config import get_settings, Settings
import os

class BaseController:
    def __init__(self):
        self.app_settings = get_settings()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.files_path = os.path.join(self.base_dir, "assets", "files")
        