
from sqlalchemy.orm import Session, selectinload

from models.question import Question
from models.answer import Answer


class QuestionProcessor:
    VALID_TYPES = {"MCQ", "TRUE_FALSE"}

    def save_generated_questions(
        self,
        db: Session,
        document_id: int,
        generated_data: dict,
        question_type: str,
    ) -> list[int]:
        question_type = question_type.upper()

        if question_type not in self.VALID_TYPES:
            raise ValueError("Unsupported question type.")

        if not isinstance(generated_data.get("questions"), list):
            raise ValueError("Generated data must contain a questions list.")

        saved_ids = []

        try:
            for item in generated_data["questions"]:
                if question_type == "MCQ":
                    header = item["question"]
                    options = item["options"]
                    correct_code = item["correct_answer"]

                    if not isinstance(options, dict) or not options:
                        raise ValueError("MCQ options must be a non-empty object.")

                    if correct_code not in options:
                        raise ValueError("Invalid correct answer code.")

                    answers = [
                        Answer(
                            CODE=code,
                            HEADER=text,
                            IS_CORRECT=(code == correct_code),
                        )
                        for code, text in options.items()
                    ]
                else:
                    header = item["statement"]
                    correct_value = item["answer"]

                    if not isinstance(correct_value, bool):
                        raise ValueError(
                            "True/false answer must be a boolean."
                        )

                    answers = [
                        Answer(
                            CODE="TRUE",
                            HEADER="True",
                            IS_CORRECT=correct_value,
                        ),
                        Answer(
                            CODE="FALSE",
                            HEADER="False",
                            IS_CORRECT=not correct_value,
                        ),
                    ]

                question = Question(
                    HEADER=header,
                    QUESTION_TYPE=question_type,
                    DOC_ID=document_id,
                    answers=answers,
                )

                db.add(question)
                db.flush()
                saved_ids.append(question.ID)

            db.commit()
            return saved_ids

        except Exception:
            db.rollback()
            raise

    def delete_question(
        self,
        db: Session,
        question_id: int,
    ) -> None:
        question = (
            db.query(Question)
            .filter(Question.ID == question_id)
            .first()
        )

        if question is None:
            raise ValueError("Question not found.")

        db.delete(question)
        db.commit()

    def get_questions_by_document(
        self,
        db: Session,
        document_id: int,
    ) -> list[Question]:
        return (
            db.query(Question)
            .options(selectinload(Question.answers))
            .filter(Question.DOC_ID == document_id)
            .order_by(Question.ID)
            .all()
        )

    def get_questions_by_subject(
        self,
        db: Session,
        subject_id: int,
    ) -> list[Question]:
        return (
            db.query(Question)
            .options(selectinload(Question.answers))
            .filter(Question.document.has(SUBJECT_ID=subject_id))
            .order_by(Question.ID)
            .all()
        )

    def get_question_by_type(
        self,
        db: Session,
        document_id: int,
        question_type: str,
    ) -> list[Question]:
        question_type = question_type.upper()

        if question_type not in self.VALID_TYPES:
            raise ValueError(
                "Unsupported question type. Use MCQ or TRUE_FALSE."
            )

        return (
            db.query(Question)
            .options(selectinload(Question.answers))
            .filter(
                Question.DOC_ID == document_id,
                Question.QUESTION_TYPE == question_type,
            )
            .order_by(Question.ID)
            .all()
        )

    def get_all_questions(self, db: Session) -> list[Question]:
        return (
            db.query(Question)
            .options(selectinload(Question.answers))
            .order_by(Question.ID)
            .all()
        )

    def save_questions_to_pdf(
        self,
        db: Session,
        document_id: int,
        file_path: str,
    ) -> None:
        from fpdf import FPDF

        questions = self.get_questions_by_document(db, document_id)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        for idx, question in enumerate(questions, start=1):
            pdf.multi_cell(0, 10, f"{idx}. {question.HEADER}")

            for answer in question.answers:
                pdf.multi_cell(
                    0,
                    10,
                    f"   - {answer.CODE}: {answer.HEADER}",
                )

            pdf.ln(5)

        pdf.output(file_path)
