from fastapi import FastAPI, APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from controllers import DataController, BaseController
from helpers.config import get_settings, Settings


class ProjectController(BaseController):
    def __init__(self):
        super().__init__()

