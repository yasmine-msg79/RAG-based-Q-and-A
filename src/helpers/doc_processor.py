
import os

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from helpers.config import get_files_path, get_settings
from helpers.subject_processor import SubjectProcessor
from models import Document, ResponseEnums


class DocProcessor:
    def __init__(self):
        self.app_settings = get_settings()
        self.files_path = get_files_path()
        self.subject_processor = SubjectProcessor()
        self.size_scale = 1024 * 1024

    def validate_file_type(self, file: UploadFile):
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseEnums.ResponseStatus.FILE_TYPE_NOT_ALLOWED

        return True, ResponseEnums.ResponseStatus.FILE_TYPE_ALLOWED

    def validate_file_size(self, file: UploadFile):
        if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            return False, ResponseEnums.ResponseStatus.FILE_SIZE_EXCEEDED

        return True, ResponseEnums.ResponseStatus.FILE_SIZE_ALLOWED

    @staticmethod
    def _normalize_document_name(name: str) -> str:
        normalized_name = name.strip()

        if (
            not normalized_name
            or normalized_name in {".", ".."}
            or "\0" in normalized_name
            or "/" in normalized_name
            or "\\" in normalized_name
        ):
            raise ValueError("name must be a valid document name.")

        return normalized_name

    @staticmethod
    def _to_dict(document: Document) -> dict:
        return {
            "id": document.ID,
            "subject_id": document.SUBJECT_ID,
            "name": document.NAME,
            "filename": document.FILENAME,
        }

    def get_document_by_name(
        self, db: Session, subject_id: int, name: str
    ):
        normalized_name = self._normalize_document_name(name)

        documents = db.scalars(
            select(Document).where(
                Document.SUBJECT_ID == subject_id
            )
        ).all()

        document = next(
            (
                item for item in documents
                if item.NAME.casefold() == normalized_name.casefold()
            ),
            None,
        )

        return self._to_dict(document) if document else None

    def list_documents(self, db: Session, subject_id: int):
        documents = db.scalars(
            select(Document)
            .where(Document.SUBJECT_ID == subject_id)
            .order_by(Document.NAME)
        ).all()

        return [self._to_dict(document) for document in documents]

    def save_document(
        self,
        db: Session,
        file: UploadFile,
        subject_id: int,
        name: str,
    ):
        normalized_name = self._normalize_document_name(name)

        subject_path = self.subject_processor.get_subject_path(
            db, subject_id
        )

        if self.get_document_by_name(
            db, subject_id, normalized_name
        ) is not None:
            raise FileExistsError(
                f"A document named '{normalized_name}' already exists "
                f"under subject {subject_id}."
            )

        original_filename = os.path.basename(file.filename or "")
        extension = os.path.splitext(original_filename)[1]
        filename = f"{normalized_name}{extension}"

        os.makedirs(subject_path, exist_ok=True)
        file_path = os.path.join(subject_path, filename)
        file_created = False

        try:
            with open(file_path, "xb") as saved_file:
                file_created = True
                saved_file.write(file.file.read())

            document = Document(
                NAME=normalized_name,
                SUBJECT_ID=subject_id,
                FILENAME=filename,
            )

            db.add(document)
            db.commit()
            db.refresh(document)

            return self._to_dict(document), file_path

        except Exception:
            db.rollback()

            if file_created and os.path.exists(file_path):
                os.remove(file_path)

            raise
        
    def delete_document(
        self,
        db: Session,
        document_id: int,
    ):
        document = db.query(Document).filter(Document.ID == document_id).first()
        if not document:
            raise ValueError("Document not found.")

        subject_path = self.subject_processor.get_subject_path(
            db, document.SUBJECT_ID
        )
        file_path = os.path.join(subject_path, document.FILENAME)

        try:
            if os.path.exists(file_path):
                os.remove(file_path)

            db.delete(document)
            db.commit()

        except Exception:
            db.rollback()
            raise

    def get_document(self, db: Session, document_id: int):
        document = db.query(Document).filter(Document.ID == document_id).first()
        return self._to_dict(document) if document else None