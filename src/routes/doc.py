
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from helpers.doc_processor import DocProcessor


doc_router = APIRouter(
    prefix="/api/v1/documents",
    tags=["api_v1", "documents"],
)


@doc_router.get("/list")
def list_documents(
    subject_id: int,
    db: Session = Depends(get_db),
):
    documents = DocProcessor().list_documents(db, subject_id)

    return {
        "documents": [
            {
                "id": document["id"],
                "name": document["name"],
                "filename": document["filename"],
            }
            for document in documents
        ]
    }


@doc_router.get("/{document_id}")
def get_document_by_id(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = DocProcessor().get_document_by_id(db, document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return {
        "document": {
            "id": document["id"],
            "subject_id": document["subject_id"],
            "name": document["name"],
            "filename": document["filename"],
        }
    }
