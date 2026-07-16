from fastapi import FastAPI, APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from controllers import DataController
from helpers.config import get_settings, Settings
from models import ResponseEnums

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

@data_router.post("/upload/{project_id}")
async def upload_file(file: UploadFile, project_id: str, app_settings : Settings = Depends(get_settings)):
    is_valid_file = DataController().validate_file_type(file)[0] & DataController().validate_file_size(file)[0]
    validation_response = {
        "file_type_validation": DataController().validate_file_type(file)[1],
        "file_size_validation": DataController().validate_file_size(file)[1]
    }
    
    if not is_valid_file:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": "File validation failed",
                "validation_response": validation_response
            }
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "File validation successful",
            "validation_response": validation_response
        }
    )