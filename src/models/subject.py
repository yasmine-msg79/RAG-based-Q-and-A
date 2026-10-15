
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base



class Subject(Base):
    __tablename__ = "SUBJECT"

    ID: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    NAME: Mapped[str] = mapped_column(String(255), nullable=False)

    documents: Mapped[list["Document"]] = relationship(
        back_populates="subject"
    )