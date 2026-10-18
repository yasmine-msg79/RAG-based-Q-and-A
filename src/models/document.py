
from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Document(Base):
    __tablename__ = "DOC"

    ID: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    NAME: Mapped[str] = mapped_column(String(255), nullable=False)
    SUBJECT_ID: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("SUBJECT.ID"), nullable=False
    )
    FILENAME: Mapped[str] = mapped_column(String(255), nullable=False)

    subject: Mapped["Subject"] = relationship(back_populates="documents")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="document"
    )