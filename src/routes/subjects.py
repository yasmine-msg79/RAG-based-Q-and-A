from pydantic import BaseModel
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_db

from helpers.subject_processor import SubjectProcessor
from helpers.doc_processor import DocProcessor


subjects_router = APIRouter(
    prefix="/api/v1/subjects",
    tags=["api_v1", "subjects"],
)


class SubjectCreateRequest(BaseModel):
    name: str


@subjects_router.post("", status_code=status.HTTP_201_CREATED)
async def create_subject(db: Session = Depends(get_db), request: SubjectCreateRequest = None):
    try:
        subject = SubjectProcessor().create_subject(db, request.name)
    except ValueError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(error)},
        )
    if subject is None:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"message": f"Subject '{request.name.strip()}' already exists."},
        )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Subject created successfully.",
            "subject": {"name": subject["name"]},
        },
    )


@subjects_router.get("")
async def list_subjects(db:Session = Depends(get_db)):
    subjects = SubjectProcessor().list_subjects(db)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"subjects": [{"name": subject["name"]} for subject in subjects]},
    )
    
@subjects_router.get("/documents")
async def list_subject_documents(db: Session = Depends(get_db), subject_name: str = None):
    try:
        subject = SubjectProcessor().get_subject_by_name(db, subject_name)
    except ValueError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(error)},
        )
    if subject is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Subject does not exist."},
        )
    doc_processor = DocProcessor()
    documents = doc_processor.list_documents(db, subject["id"])
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"Documents for subject '{subject['name']}'.",
            "documents": [{"name": document["name"]} for document in documents],
        },
    )
