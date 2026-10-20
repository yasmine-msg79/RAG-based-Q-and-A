
from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Question(Base):
    __tablename__ = "QUESTION"

    ID: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    HEADER: Mapped[str] = mapped_column(Text, nullable=False)
    QUESTION_TYPE: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MCQ"
    )
    DOC_ID: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("DOC.ID", ondelete="CASCADE"), nullable=False
    )
    DIFFICULTY: Mapped[str] = mapped_column(
        String(10), nullable=False, default="MEDIUM"
    )

    document: Mapped["Document"] = relationship(back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="question"
    )
    
    
    def to_dict(self):
        return {
            "id": self.ID,
            "header": self.HEADER,
            "question_type": self.QUESTION_TYPE,
            "document_id": self.DOC_ID,
            "difficulty": self.DIFFICULTY,
            "answers": [answer.to_dict() for answer in self.answers],
        }
