import os
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine


DEFAULT_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://myuser:mypassword@localhost:5432/mydatabase",
)


def build_engine(database_url: Optional[str] = None) -> Engine:
    url = database_url or DEFAULT_DATABASE_URL
    return create_engine(url, echo=False)


def get_sessionmaker(engine: Optional[Engine] = None):
    if engine is None:
        engine = build_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_students_table(engine: Optional[Engine] = None) -> None:
    engine = engine or build_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS students (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    age INTEGER NOT NULL,
                    major VARCHAR(100) NOT NULL
                )
                """
            )
        )


def drop_students_table(engine: Optional[Engine] = None) -> None:
    engine = engine or build_engine()
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS students"))


def insert_student(session: Session, *, name: str, age: int, major: str):
    stmt = text(
        "INSERT INTO students (name, age, major) VALUES (:name, :age, :major) RETURNING id"
    )
    result = session.execute(stmt, {"name": name, "age": age, "major": major})
    inserted_id = result.scalar_one()
    session.commit()
    return type("Student", (), {"id": inserted_id, "name": name, "age": age, "major": major})()


def update_student(session: Session, student_id: int, *, name: str, age: int, major: str):
    stmt = text(
        "UPDATE students SET name = :name, age = :age, major = :major WHERE id = :student_id"
    )
    session.execute(stmt, {"name": name, "age": age, "major": major, "student_id": student_id})
    session.commit()
    return type("Student", (), {"id": student_id, "name": name, "age": age, "major": major})()


def delete_student(session: Session, student_id: int) -> None:
    stmt = text("DELETE FROM students WHERE id = :student_id")
    session.execute(stmt, {"student_id": student_id})
    session.commit()
