
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from helpers import embedding, generation, pdf_processor
from helpers.doc_processor import DocProcessor
from helpers.subject_processor import SubjectProcessor
from helpers.vector_store import (
    has_document_chunks,
    search_chunks,
    store_chunks,
)
from helpers.question_processor import QuestionProcessor


data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)


# ---------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------

class GenerateAnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1)


class GenerateQuestionsRequest(BaseModel):
    top_k: int = Field(default=3, ge=1)
    num_questions: int = Field(default=5, ge=1)


# ---------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------

def _get_document(db: Session, document_id: int) -> dict:
    """Retrieve a document by ID or raise 404."""
    document = DocProcessor().get_document(db, document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return document


def _get_processed_document(
    db: Session,
    document_id: int,
) -> dict:
    """Retrieve a document and ensure its chunks exist."""
    document = _get_document(db, document_id)

    if not has_document_chunks(
        document["subject_id"],
        document["id"],
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document has not been processed yet.",
        )

    return document


def _retrieve_chunks(
    query: str,
    document: dict,
    top_k: int,
) -> list[dict[str, str]]:
    """Retrieve relevant text chunks for a document."""
    query_embedding = embedding.get_embedding([query])[0]

    results = search_chunks(
        query_embedding=query_embedding,
        subject_id=document["subject_id"],
        document_id=document["id"],
        top_k=top_k,
    )

    documents = results.get("documents") or []
    texts = documents[0] if documents else []

    return [{"text": text} for text in texts]


def _document_file_path(
    db: Session,
    document: dict,
) -> str:
    """Resolve the file path using the document's stored subject ID."""
    subject_processor = SubjectProcessor()

    try:
        subject_path = subject_processor.get_subject_path(
            db,
            document["subject_id"],
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject directory not found.",
        )

    file_path = os.path.join(
        subject_path,
        document["filename"],
    )

    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The document file could not be found.",
        )

    return file_path


# ---------------------------------------------------------------------
# Upload document
# POST /api/v1/data/upload
# ---------------------------------------------------------------------

@data_router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    subject_id: int = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    doc_processor = DocProcessor()

    file_type_valid, file_type_status = (
        doc_processor.validate_file_type(file)
    )
    file_size_valid, file_size_status = (
        doc_processor.validate_file_size(file)
    )

    validation_response = {
        "file_type_validation": file_type_status,
        "file_size_validation": file_size_status,
    }

    if not (file_type_valid and file_size_valid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "File validation failed.",
                "validation_response": validation_response,
            },
        )

    subject_processor = SubjectProcessor()
    subject = subject_processor.get_subject(db, subject_id)

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found.",
        )

    try:
        document, _ = doc_processor.save_document(
            db,
            file,
            subject_id,
            name,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )
    except FileExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A document named '{name.strip()}' already exists.",
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject directory not found.",
        )

    return {
        "message": "File uploaded successfully. Processing has not started.",
        "validation_response": validation_response,
        "document": document,
    }


# ---------------------------------------------------------------------
# Process document
# POST /api/v1/data/documents/{document_id}/process
# ---------------------------------------------------------------------

@data_router.post("/documents/{document_id}/process")
def process_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = _get_document(db, document_id)
    file_path = _document_file_path(db, document)

    try:
        text, page_count = pdf_processor.get_pdf_text(file_path)
        chunks = pdf_processor.chunk_text(text)

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No extractable text was found in the document.",
            )

        embeddings = embedding.get_embedding(chunks)

        store_chunks(
            chunks=chunks,
            embeddings=embeddings,
            subject_id=document["subject_id"],
            document_id=document["id"],
        )

    except HTTPException:
        raise
    except Exception:
        # Replace with logger.exception(...) when logging is configured.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document processing failed.",
        )

    return {
        "message": "Document processed successfully.",
        "document_id": document["id"],
        "page_count": page_count,
        "chunk_count": len(chunks),
    }


# ---------------------------------------------------------------------
# Generate answer
# POST /api/v1/data/documents/{document_id}/generate_answer
# ---------------------------------------------------------------------

@data_router.post("/documents/{document_id}/generate_answer")
def generate_answer(
    document_id: int,
    request: GenerateAnswerRequest,
    db: Session = Depends(get_db),
):
    document = _get_processed_document(db, document_id)

    retrieved_chunks = _retrieve_chunks(
        request.query,
        document,
        request.top_k,
    )

    if not retrieved_chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant chunks found for this document.",
        )

    answer = generation.generate_answer(
        request.query,
        retrieved_chunks,
    )

    return {
        "message": f"Generated answer for document '{document['name']}'.",
        "answer": answer,
    }


# ---------------------------------------------------------------------
# Generate MCQs
# POST /api/v1/data/documents/{document_id}/generate_mcqs
# ---------------------------------------------------------------------

@data_router.post("/documents/{document_id}/generate_mcqs")
def generate_mcqs(
    document_id: int,
    request: GenerateQuestionsRequest,
    db: Session = Depends(get_db),
):
    document = _get_processed_document(db, document_id)

    query = "Generate multiple-choice questions based on the content."
    retrieved_chunks = _retrieve_chunks(
        query,
        document,
        request.top_k,
    )

    if not retrieved_chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant chunks found for this document.",
        )

    mcqs = generation.generate_mcqs(
        retrieved_chunks,
        request.num_questions,
    )

    saved_ids = QuestionProcessor().save_generated_questions(
        db=db,
        document_id=document["id"],
        generated_data=mcqs,
        question_type="MCQ",
    )

    return {
        "message": f"Generated multiple-choice questions for '{document['name']}'.",
        "mcqs": mcqs,
        "saved_question_ids": saved_ids,
    }


# ---------------------------------------------------------------------
# Generate true/false questions
# POST /api/v1/data/documents/{document_id}/generate_true_false
# ---------------------------------------------------------------------

@data_router.post("/documents/{document_id}/generate_true_false")
def generate_true_false(
    document_id: int,
    request: GenerateQuestionsRequest,
    db: Session = Depends(get_db),
):
    document = _get_processed_document(db, document_id)

    query = "Generate true/false questions based on the content."
    retrieved_chunks = _retrieve_chunks(
        query,
        document,
        request.top_k,
    )

    if not retrieved_chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant chunks found for this document.",
        )

    true_false_questions = generation.generate_true_false(
        retrieved_chunks,
        request.num_questions,
    )

    saved_ids = QuestionProcessor().save_generated_questions(
        db=db,
        document_id=document["id"],
        generated_data=true_false_questions,
        question_type="TRUE_FALSE",
    )

    return {
        "message": f"Generated true/false questions for '{document['name']}'.",
        "true_false_questions": true_false_questions,
        "saved_question_ids": saved_ids,
    }


# ---------------------------------------------------------------------
# Get questions for a document
# GET /api/v1/data/documents/{document_id}/questions
# ---------------------------------------------------------------------

@data_router.get("/documents/{document_id}/questions")
def get_questions_by_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = _get_document(db, document_id)

    questions = QuestionProcessor().get_questions_by_document(
        db=db,
        document_id=document["id"],
    )

    return {
        "message": f"Retrieved questions for '{document['name']}'.",
        "questions": [question.to_dict() for question in questions],
    }


# ---------------------------------------------------------------------
# Get questions for a subject
# GET /api/v1/data/questions/subject/{subject_id}
# ---------------------------------------------------------------------

@data_router.get("/questions/subject/{subject_id}")
def get_questions_by_subject(
    subject_id: int,
    db: Session = Depends(get_db),
):
    subject = SubjectProcessor().get_subject_by_id(db, subject_id)

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found.",
        )

    questions = QuestionProcessor().get_questions_by_subject(
        db=db,
        subject_id=subject_id,
    )

    return {
        "message": "Retrieved questions for subject.",
        "questions": [question.to_dict() for question in questions],
    }


# ---------------------------------------------------------------------
# Get questions by type
# GET /api/v1/data/documents/{document_id}/questions/type/{question_type}
# ---------------------------------------------------------------------

@data_router.get(
    "/documents/{document_id}/questions/type/{question_type}"
)
def get_questions_by_type(
    document_id: int,
    question_type: str,
    db: Session = Depends(get_db),
):
    document = _get_document(db, document_id)

    try:
        questions = QuestionProcessor().get_question_by_type(
            db=db,
            document_id=document["id"],
            question_type=question_type,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    return {
        "message": f"Retrieved {question_type.upper()} questions.",
        "questions": [question.to_dict() for question in questions],
    }


# ---------------------------------------------------------------------
# Delete document
# DELETE /api/v1/data/documents/{document_id}
# ---------------------------------------------------------------------

@data_router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = _get_document(db, document_id)

    try:
        DocProcessor().delete_document(db, document["id"])
    except Exception:
        # Replace with logger.exception(...) when logging is configured.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document.",
        )

    return {
        "message": "Document deleted successfully.",
        "document_id": document_id,
    }
