
from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Answer(Base):
    __tablename__ = "ANSWERS"

    ID: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    CODE: Mapped[str] = mapped_column(String(10), nullable=False)
    HEADER: Mapped[str] = mapped_column(Text, nullable=False)
    IS_CORRECT: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    QUESTION_ID: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("QUESTION.ID"), nullable=False
    )

    question: Mapped["Question"] = relationship(back_populates="answers")
    
    
    def to_dict(self):
        return {
            "id": self.ID,
            "code": self.CODE,
            "header": self.HEADER,
            "is_correct": self.IS_CORRECT,
        }
