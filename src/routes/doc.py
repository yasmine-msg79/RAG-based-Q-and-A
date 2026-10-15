from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_db

from helpers.doc_processor import DocProcessor
from helpers.subject_processor import SubjectProcessor


doc_router = APIRouter(
    prefix="/api/v1/documents",
    tags=["api_v1", "documents"],
)

@doc_router.get("/list")
async def list_documents(db: Session = Depends(get_db), subject_name: str = None):
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
            content={"message": f"Subject '{subject_name.strip()}' does not exist."},
        )

    documents = DocProcessor().list_documents(db, subject["id"])
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "documents": [
                {"name": document["name"]} for document in documents
            ]
        },
    )
    
@doc_router.get("")
async def get_document_by_name(db: Session = Depends(get_db), subject_name: str = None, document_name: str = None):
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
            content={"message": f"Subject '{subject_name.strip()}' does not exist."},
        )

    try:
        document = DocProcessor().get_document_by_name(db, subject["id"], document_name)
    except ValueError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(error)},
        )
    if document is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": (
                    f"Document '{document_name.strip()}' under "
                    f"'{subject_name.strip()}' does not exist."
                )
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "document": {
                "name": document["name"],
                "filename": document["filename"],
            }
        },
    )





