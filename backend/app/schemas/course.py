import uuid
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class LocalizedTitleIn(BaseModel):
    """Accept Flutter's title_ta/title_en while retaining current DB columns."""
    model_config = ConfigDict(populate_by_name=True)
    title_tamil: str = Field(min_length=1, max_length=240, validation_alias="title_ta")
    title_english: str = Field(min_length=1, max_length=240, validation_alias="title_en")

class SubjectIn(LocalizedTitleIn):
    category: str = Field(pattern="^(Tamil|GS|Aptitude)$")
class UnitIn(LocalizedTitleIn):
    subject_id: uuid.UUID; unit_number: int = Field(ge=1)
class ChapterIn(LocalizedTitleIn):
    unit_id: uuid.UUID; chapter_number: int = Field(ge=1)
    standard: int = Field(ge=6, le=12)
class VideoIn(LocalizedTitleIn):
    chapter_id: uuid.UUID; subject_id: uuid.UUID; unit_id: uuid.UUID
    faculty_name: str | None = Field(default=None, validation_alias=AliasChoices("faculty", "faculty_name"))
    description: str | None = None
    duration: str | None = Field(default=None, max_length=80)
    video_url: str; thumbnail_url: str | None = None; notes_url: str | None = None
    is_published: bool = True
    quiz_questions: list = Field(default_factory=list)
class PdfIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    chapter_id: uuid.UUID; subject_id: uuid.UUID; unit_id: uuid.UUID
    title: str = Field(min_length=1, max_length=240, validation_alias=AliasChoices("title_en", "title"))
    title_tamil: str | None = Field(default=None, max_length=240, validation_alias="title_ta")
    title_english: str | None = Field(default=None, max_length=240, validation_alias="title_en")
    category: str | None = Field(default=None, max_length=120)
    description: str | None = None; author: str | None = Field(default=None, max_length=160)
    file_url: str = Field(validation_alias=AliasChoices("pdf_url", "file_url"))
    file_size: int | None = Field(default=None, ge=0)
    offline_allowed: bool = Field(default=False, validation_alias=AliasChoices("is_downloadable", "offline_allowed"))
    is_priority: bool = False
    is_published: bool = True
class TestIn(BaseModel):
    chapter_id: uuid.UUID | None = None; title: str
    type: str = Field(pattern="^(subjectWise|pyq|fullTest)$")
    duration: int = Field(gt=0); total_questions: int = Field(default=0, ge=0)
class OptionIn(BaseModel):
    text: str = Field(min_length=1); is_correct: bool = False
class QuestionIn(BaseModel):
    test_id: uuid.UUID; chapter_id: uuid.UUID; text: str = Field(min_length=1); explanation: str | None = None
    type: str = Field(default="single_choice", pattern="^(single_choice|multiple_choice)$")
    image_url: str | None = None; options: list[OptionIn] = Field(min_length=2)
    @model_validator(mode="after")
    def valid_correct_answers(self):
        correct = sum(item.is_correct for item in self.options)
        if not correct or (self.type == "single_choice" and correct != 1):
            raise ValueError("Questions need one correct option; multiple choice may have several")
        return self
class AnswerIn(BaseModel):
    question_id: uuid.UUID; option_ids: list[uuid.UUID] = Field(min_length=1)
class SubmitIn(BaseModel):
    answers: list[AnswerIn] = Field(default_factory=list)
