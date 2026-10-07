from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str]
    password_hash: Mapped[str]
    full_name: Mapped[str]


class Reader(Base):
    __tablename__ = "readers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str]
    email: Mapped[str]
    phone: Mapped[str]
    registered_on: Mapped[date]


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    author: Mapped[str]
    isbn: Mapped[str]
    published_year: Mapped[int]
    genre: Mapped[str]


class Copy(Base):
    __tablename__ = "copies"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    inventory_no: Mapped[str]
    shelf: Mapped[str]
    acquired_on: Mapped[date]

    book: Mapped[Book] = relationship()


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    copy_id: Mapped[int] = mapped_column(ForeignKey("copies.id"))
    reader_id: Mapped[int] = mapped_column(ForeignKey("readers.id"))
    issued_on: Mapped[date]
    due_on: Mapped[date]
    returned_on: Mapped[date | None]

    copy: Mapped[Copy] = relationship()
    reader: Mapped[Reader] = relationship()
