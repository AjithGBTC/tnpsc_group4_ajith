import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class TestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = None
    test_type: str = Field(pattern="^(practice|smart_quiz|live)$")
    quiz_type: str | None = Field(default=None, max_length=80)
    duration_minutes: int = Field(ge=1, le=300)
    max_attempts: int = Field(default=2, ge=1, le=2)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    question_ids: list[uuid.UUID] = Field(min_length=1)


class SaveAnswer(BaseModel):
    question_id: uuid.UUID
    selected: list[str] = Field(default_factory=list)
