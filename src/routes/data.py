from fastapi import APIRouter, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_db

from helpers import embedding, generation, pdf_processor
from helpers.doc_processor import DocProcessor
from helpers.subject_processor import SubjectProcessor
from helpers.vector_store import store_chunks, search_chunks, has_document_chunks
from helpers.question_processor import QuestionProcessor

from models.document import Document

import os




data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

class ProcessorDocumentRequest(BaseModel):
    subject_name: str
    document_name: str

class GenerateAnswerRequest(BaseModel):
    subject_name: str
    document_name: str
    query: str
    top_k: int = 3


class GenerateQuestionsRequest(BaseModel):
    subject_name: str
    document_name: str
    top_k: int = 3
    num_questions: int = 5
    
class DeleteDocumentRequest(BaseModel):
    subject_name: str
    document_name: str
    
class GetQuestionsByDocumentRequest(BaseModel):
    subject_name: str
    document_name: str

class GetQuestionsBySubjectRequest(BaseModel):
    subject_name: str

class GetQuestionsByTypeRequest(BaseModel):
    subject_name: str
    document_name: str
    question_type: str
    


def _get_document_context(
    db: Session,
    subject_name: str,
    document_name: str,
):
    subject = SubjectProcessor().get_subject_by_name(
        db, subject_name
    )

    if subject is None:
        return None, JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Subject does not exist."},
        )

    document = DocProcessor().get_document_by_name(
        db, subject["id"], document_name
    )

    if document is None:
        return None, JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Document does not exist."},
        )

    if not has_document_chunks(
        subject["id"],
        document["id"],
    ):
        return None, JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": (
                    f"Document '{document['name']}' under "
                    f"'{subject['name']}' has not been processed."
                )
            },
        )

    return (subject, document), None


def _retrieve_chunks(query: str, document: dict, top_k: int):
    query_embedding = embedding.get_embedding([query])[0]

    results = search_chunks(
        query_embedding=query_embedding,
        subject_id=document["subject_id"],
        document_id=document["id"],
        top_k=top_k,
    )

    texts = results["documents"][0] if results["documents"] else []

    return [{"text": text} for text in texts]


@data_router.post("/upload")
async def upload_file(
    file: UploadFile,
    subject_name: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    doc_processor = DocProcessor()

    file_type_valid, file_type_status = doc_processor.validate_file_type(file)
    file_size_valid, file_size_status = doc_processor.validate_file_size(file)

    validation_response = {
        "file_type_validation": file_type_status,
        "file_size_validation": file_size_status,
    }

    if not (file_type_valid and file_size_valid):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": "File validation failed",
                "validation_response": validation_response,
            },
        )

    try:
        subject = SubjectProcessor().get_subject_by_name(db, subject_name)
        if subject is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Subject does not exist."},
            )

        document, _ = doc_processor.save_document(
            db, file, subject["id"], name
        )

    except ValueError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(error)},
        )
    except FileExistsError:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"message": f"A document named '{name.strip()}' already exists under subject '{subject_name}'."},
        )
    except FileNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": f"Subject '{subject_name}' does not exist."},
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "File uploaded successfully. Processing has not started.",
            "validation_response": validation_response,
            "document": document,
        },
    )
    
@data_router.post(
    "/subjects/{subject_name}/documents/{document_name}/process"
)
def process_document(
    db: Session = Depends(get_db), request: ProcessorDocumentRequest = None
):
    subject_processor = SubjectProcessor()

    subject = subject_processor.get_subject_by_name(db, request.subject_name)

    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")

    subject_id = subject["id"]  # If get_subject_by_name returns a dictionary

    document = DocProcessor().get_document_by_name(
        db, subject_id, request.document_name
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")


    try:
        subject_path = subject_processor.get_subject_path(
            db, subject_id
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Subject directory not found.",
        )

    file_path = os.path.join(
        subject_path,
        document["filename"],
    )

    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=404,
            detail="The document file could not be found.",
        )

    try:
        text, page_count = pdf_processor.get_pdf_text(file_path)
        chunks = pdf_processor.chunk_text(text)

        if not chunks:
            raise HTTPException(
                status_code=422,
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
        # Log the exception here while debugging.
        raise HTTPException(
            status_code=500,
            detail="Document processing failed.",
        )

    return {
        "message": "Document processed successfully.",
        "document_id": document["id"],
        "page_count": page_count,
        "chunk_count": len(chunks),
    }

@data_router.post("/generate_answer")
async def generate_answer(db: Session = Depends(get_db), request: GenerateAnswerRequest = None):
    try:
        context, error = _get_document_context(
            db, request.subject_name, request.document_name
        )
    except ValueError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(error)},
        )
    if error is not None:
        return error
    subject, document = context

    retrieved_chunks = _retrieve_chunks(
        request.query,
        document,
        request.top_k,
    )

    if not retrieved_chunks:
        raise HTTPException(
            status_code=404,
            detail="No processed chunks found for this document.",
        )

    answer = generation.generate_answer(
        request.query,
        retrieved_chunks,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": (
                f"Generated answer for query '{request.query}' in document "
                f"'{document['name']}' under subject '{subject['name']}'."
            ),
            "answer": answer,
        },
    )


@data_router.post("/generate_mcqs")
async def generate_mcqs( db: Session = Depends(get_db), request: GenerateQuestionsRequest = None):
    try:
        context, error = _get_document_context(
            db, request.subject_name, request.document_name
        )
    except ValueError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(error)},
        )
    if error is not None:
        return error
    subject, document = context

    query = "Generate multiple-choice questions based on the content."
    retrieved_chunks = _retrieve_chunks(
        query,
        document,
        request.top_k,
    )

    if not retrieved_chunks:
        raise HTTPException(
            status_code=404,
            detail="No processed chunks found for this document.",
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
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": (
                f"Generated multiple-choice questions for document "
                f"'{document['name']}' under subject '{subject['name']}'."
            ),
            "mcqs": mcqs,
            "saved_question_ids": saved_ids,
        },
    )


@data_router.post("/generate_true_false")
async def generate_true_false(db: Session = Depends(get_db), request: GenerateQuestionsRequest = None):
    try:
        context, error = _get_document_context(
            db, request.subject_name, request.document_name
        )
    except ValueError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(error)},
        )
    if error is not None:
        return error
    subject, document = context

    query = "Generate true/false questions based on the content."
    retrieved_chunks = (
        query,
        document,
        request.top_k,
    )

    if not retrieved_chunks:
        raise HTTPException(
            status_code=404,
            detail="No processed chunks found for this document.",
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
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": (
                f"Generated true/false questions for document "
                f"'{document['name']}' under subject '{subject['name']}'."
            ),
            "true_false_questions": true_false_questions,
            "saved_question_ids": saved_ids,
        },
    )

# @data_router.delete("/questions/{question_id}")
# async def delete_question(
#     question_id: int,
#     db: Session = Depends(get_db),
# ):
#     try:
#         QuestionProcessor().delete_question(db, question_id)
#     except ValueError as error:
#         return JSONResponse(
#             status_code=status.HTTP_404_NOT_FOUND,
#             content={"message": str(error)},
#         )
#     return JSONResponse(
#         status_code=status.HTTP_200_OK,
#         content={"message": f"Question with ID {question_id} deleted successfully."},
#     )
    

@data_router.get(
    "/subjects/{subject_name}/documents/{document_name}/questions"
)
async def get_questions_by_document(
    subject_name: str,
    document_name: str,
    db: Session = Depends(get_db),
):
    context, error = _get_document_context(
        db, subject_name, document_name
    )

    if error is not None:
        return error

    subject, document = context

    questions = QuestionProcessor().get_questions_by_document(
        db=db,
        document_id=document["id"],
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": (
                f"Retrieved questions for document '{document['name']}' "
                f"under subject '{subject['name']}'."
            ),
            "questions": [q.to_dict() for q in questions],
        },
    )


@data_router.get("/questions/subject/{subject_name}")
async def get_questions_by_subject(
    subject_name: str,
    db: Session = Depends(get_db),
):
    subject = SubjectProcessor().get_subject_by_name(db, subject_name)

    if subject is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Subject not found."},
        )

    questions = QuestionProcessor().get_questions_by_subject(
        db=db,
        subject_id=subject["id"],
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": (
                f"Retrieved questions for subject '{subject['name']}'."
            ),
            "questions": [q.to_dict() for q in questions],
        },
    )


@data_router.get(
    "/subjects/{subject_name}/documents/{document_name}/questions/type/{question_type}"
)
async def get_questions_by_type(
    subject_name: str,
    document_name: str,
    question_type: str,
    db: Session = Depends(get_db),
):
    context, error = _get_document_context(
        db, subject_name, document_name
    )

    if error is not None:
        return error

    subject, document = context

    try:
        questions = QuestionProcessor().get_question_by_type(
            db=db,
            document_id=document["id"],
            question_type=question_type,
        )
    except ValueError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(error)},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": (
                f"Retrieved {question_type.upper()} questions for "
                f"document '{document['name']}' under "
                f"subject '{subject['name']}'."
            ),
            "questions": [q.to_dict() for q in questions],
        },
    )

# @data_router.get("/questions/all")
# async def get_all_questions(
#     db: Session = Depends(get_db),
# ):
#     questions = QuestionProcessor().get_all_questions(db)

#     return JSONResponse(
#         status_code=status.HTTP_200_OK,
#         content={
#             "message": "Retrieved all questions.",
#             "questions": [q.to_dict() for q in questions],
#         },
#     )
    
@data_router.delete("/documents/{document_name}")
async def delete_document(
    db: Session = Depends(get_db), request: DeleteDocumentRequest = None
):
    subject_processor = SubjectProcessor()
    doc_processor = DocProcessor()

    subject = subject_processor.get_subject_by_name(db, request.subject_name)

    if not subject:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Subject not found."},
        )

    document = doc_processor.get_document_by_name(
        db, subject["id"], document_name
    )

    if not document:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Document not found."},
        )

    try:
        doc_processor.delete_document(db, document["id"])
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Failed to delete document: {str(e)}"},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": (
                f"Document '{document['name']}' under subject "
                f"'{subject['name']}' deleted successfully."
            )
        },
    )
    
    