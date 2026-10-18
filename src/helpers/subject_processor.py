
import os

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from helpers.config import get_files_path
from models import Subject


class SubjectProcessor:
    def __init__(self):
        self.files_path = get_files_path()

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized_name = name.strip()

        if (
            not normalized_name
            or normalized_name in {".", ".."}
            or "\0" in normalized_name
            or "/" in normalized_name
            or "\\" in normalized_name
        ):
            raise ValueError("name must be a valid subject name.")

        return normalized_name

    @staticmethod
    def _to_dict(subject: Subject) -> dict:
        return {
            "id": subject.ID,
            "name": subject.NAME,
        }

    def create_subject(self, db: Session, name: str):
        normalized_name = self._normalize_name(name)

        existing = db.scalars(
            select(Subject).where(
                Subject.NAME == normalized_name
            )
        ).first()

        if existing is not None:
            return None

        subject = Subject(NAME=normalized_name)
        db.add(subject)

        try:
            db.commit()
            db.refresh(subject)
            return self._to_dict(subject)
        except IntegrityError:
            db.rollback()
            return None

    def list_subjects(self, db: Session):
        subjects = db.scalars(
            select(Subject).order_by(Subject.NAME)
        ).all()

        return [self._to_dict(subject) for subject in subjects]

    def get_subject(self, db: Session, subject_id: int):
        subject = db.get(Subject, subject_id)
        return self._to_dict(subject) if subject else None

    def get_subject_by_name(self, db: Session, name: str):
        normalized_name = self._normalize_name(name)

        subjects = db.scalars(select(Subject)).all()

        subject = next(
            (
                item
                for item in subjects
                if item.NAME.casefold() == normalized_name.casefold()
            ),
            None,
        )

        return self._to_dict(subject) if subject else None

    def get_subject_path(self, db: Session, subject_id: int) -> str:
        subject = db.get(Subject, subject_id)

        if subject is None:
            raise FileNotFoundError(
                f"Subject {subject_id} does not exist."
            )

        subject_name = subject.NAME

        if (
            not subject_name
            or subject_name in {".", ".."}
            or "\0" in subject_name
            or "/" in subject_name
            or "\\" in subject_name
            or os.path.basename(subject_name) != subject_name
        ):
            raise ValueError("subject_name must be a valid path segment.")

        return os.path.join(self.files_path, subject_name)
