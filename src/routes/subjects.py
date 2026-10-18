
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from helpers.subject_processor import SubjectProcessor
from helpers.doc_processor import DocProcessor


subjects_router = APIRouter(
    prefix="/api/v1/subjects",
    tags=["api_v1", "subjects"],
)


class SubjectCreateRequest(BaseModel):
    name: str = Field(min_length=1)


@subjects_router.post("", status_code=status.HTTP_201_CREATED)
def create_subject(
    request: SubjectCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        subject = SubjectProcessor().create_subject(db, request.name)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subject '{request.name.strip()}' already exists.",
        )

    return {
        "message": "Subject created successfully.",
        "subject": {
            "id": subject["id"],
            "name": subject["name"],
        },
    }


@subjects_router.get("")
def list_subjects(db: Session = Depends(get_db)):
    subjects = SubjectProcessor().list_subjects(db)

    return {
        "subjects": [
            {
                "id": subject["id"],
                "name": subject["name"],
            }
            for subject in subjects
        ]
    }


@subjects_router.get("/documents")
def list_subject_documents(
    subject_id: int,
    db: Session = Depends(get_db),
):
    subject = SubjectProcessor().get_subject(db, subject_id)

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found.",
        )

    documents = DocProcessor().list_documents(db, subject_id)

    return {
        "message": f"Documents for subject '{subject['name']}'.",
        "documents": [
            {
                "id": document["id"],
                "name": document["name"],
                "filename": document["filename"],
            }
            for document in documents
        ],
    }
