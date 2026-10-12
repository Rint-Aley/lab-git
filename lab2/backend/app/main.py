"""FastAPI endpoints for the People Management application."""

from __future__ import annotations

import logging
import re
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncIterator

from fastapi import FastAPI, HTTPException, Path as PathParameter, Response, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .database import get_connection, init_db

logger = logging.getLogger(__name__)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize persistent storage before accepting requests."""
    init_db()
    yield


app = FastAPI(
    title="People Management API",
    description="A small CRUD API backed by SQLite.",
    version="1.0.0",
    lifespan=lifespan,
)


class PersonInput(BaseModel):
    """Validated request payload used for creates and full updates."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100, description="Person's name")
    email: str = Field(min_length=3, max_length=254, description="Person's email address")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address")
        return value


class Person(PersonInput):
    id: int
    created_at: str


def _person_from_row(row: sqlite3.Row) -> dict[str, object]:
    return dict(row)


@app.exception_handler(sqlite3.Error)
async def handle_database_error(_request, exc: sqlite3.Error) -> JSONResponse:
    logger.exception("Database operation failed: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database operation failed. Please try again."},
    )


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Simple process health endpoint."""
    return {"status": "ok"}


@app.get("/api/people", response_model=list[Person], tags=["people"])
def list_people() -> list[dict[str, object]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, email, created_at FROM people ORDER BY id DESC"
        ).fetchall()
    return [_person_from_row(row) for row in rows]


@app.get("/api/people/{person_id}", response_model=Person, tags=["people"])
def get_person(
    person_id: Annotated[int, PathParameter(gt=0, description="Person ID")],
) -> dict[str, object]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, name, email, created_at FROM people WHERE id = ?",
            (person_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return _person_from_row(row)


@app.post(
    "/api/people",
    response_model=Person,
    status_code=status.HTTP_201_CREATED,
    tags=["people"],
)
def create_person(person: PersonInput) -> dict[str, object]:
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO people (name, email) VALUES (?, ?)",
            (person.name, person.email),
        )
        row = connection.execute(
            "SELECT id, name, email, created_at FROM people WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    if row is None:  # Defensive: SQLite should return the row after an insert.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The person could not be created.",
        )
    return _person_from_row(row)


@app.put("/api/people/{person_id}", response_model=Person, tags=["people"])
def update_person(
    person: PersonInput,
    person_id: Annotated[int, PathParameter(gt=0, description="Person ID")],
) -> dict[str, object]:
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE people SET name = ?, email = ? WHERE id = ?",
            (person.name, person.email, person_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
        row = connection.execute(
            "SELECT id, name, email, created_at FROM people WHERE id = ?",
            (person_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return _person_from_row(row)


@app.delete(
    "/api/people/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    tags=["people"],
)
def delete_person(
    person_id: Annotated[int, PathParameter(gt=0, description="Person ID")],
) -> Response:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM people WHERE id = ?", (person_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Local development is intentionally same-origin: FastAPI serves the static
# frontend when this source checkout contains ../frontend. In a later container
# deployment, the backend image can contain only backend/ and Nginx will serve
# frontend/ and proxy /api/ to this service instead.
_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if _FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
