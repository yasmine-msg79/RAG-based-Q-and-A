import os

from fastapi import FastAPI, APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from controllers import DataController, BaseController
from helpers.config import get_settings, Settings


class ProjectController(BaseController):
    def __init__(self):
        super().__init__()

    def get_project_path(self, project_id: str):
        return f"{self.files_path}/{project_id}"

    def make_project_directory(self, project_id: str):
        project_path = self.get_project_path(project_id)
        if not os.path.exists(project_path):
            os.makedirs(project_path)
            return True
        return False
