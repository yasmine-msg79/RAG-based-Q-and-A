import os

from .BaseController import BaseController
from fastapi import UploadFile 
from models import ResponseEnums

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_scale = 1024 * 1024  
        
    def validate_file_type(self, file : UploadFile):
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseEnums.ResponseStatus.FILE_TYPE_NOT_ALLOWED
        return True, ResponseEnums.ResponseStatus.FILE_TYPE_ALLOWED
    def validate_file_size(self, file : UploadFile):
        if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            return False, ResponseEnums.ResponseStatus.FILE_SIZE_EXCEEDED
        return True, ResponseEnums.ResponseStatus.FILE_SIZE_ALLOWED  
    def get_project_path(self, project_id : str):
        return f"{self.files_path}/{project_id}"  
    
    def save_file(self, file : UploadFile, project_id : str):
        project_path = self.get_project_path(project_id)
        if not os.path.exists(project_path):
            os.makedirs(project_path)
        file_path = os.path.join(project_path, file.filename)
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        return file_path