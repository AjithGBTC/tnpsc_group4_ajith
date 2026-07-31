import uuid
from pydantic import BaseModel, Field


class TaxonomyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    parent_id: uuid.UUID | None = None
    sequence: int = 0


class QuestionCreate(BaseModel):
    exam_id: uuid.UUID
    subject_id: uuid.UUID | None = None
    topic_id: uuid.UUID | None = None
    body: str = Field(min_length=1)
    options: list[dict] = Field(min_length=2)
    answer: list[str] = Field(min_length=1)
    explanation: str | None = None
    difficulty: str = "medium"
    question_type: str = "single_choice"
    marks: int = Field(default=1, ge=0, le=100)
    negative_marks: int = Field(default=0, ge=0, le=100)
