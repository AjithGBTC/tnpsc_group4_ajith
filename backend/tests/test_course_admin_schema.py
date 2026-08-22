import uuid

from app.schemas.course import PdfIn, VideoIn


def test_video_dashboard_payload_uses_expected_field_names() -> None:
    item = VideoIn.model_validate({
        "title_ta": "தமிழ் பாடம்", "title_en": "Tamil lesson", "faculty": "Teacher",
        "description": "Overview", "duration": "45 minutes", "video_url": "https://cdn.example/video.mp4",
        "thumbnail_url": "https://cdn.example/thumb.jpg", "notes_url": "https://cdn.example/notes.pdf",
        "chapter_id": str(uuid.uuid4()), "subject_id": str(uuid.uuid4()), "unit_id": str(uuid.uuid4()),
        "is_published": False, "quiz_questions": [],
    })
    assert item.faculty_name == "Teacher"
    assert item.duration == "45 minutes"
    assert item.is_published is False


def test_pdf_dashboard_payload_maps_to_storage_field_names() -> None:
    item = PdfIn.model_validate({
        "title_ta": "குறிப்புகள்", "title_en": "Notes", "category": "Study material",
        "description": "Overview", "author": "Teacher", "pdf_url": "https://cdn.example/notes.pdf",
        "file_size": 1024, "chapter_id": str(uuid.uuid4()), "subject_id": str(uuid.uuid4()),
        "unit_id": str(uuid.uuid4()), "is_published": True, "is_downloadable": True, "is_priority": False,
    })
    assert item.file_url == "https://cdn.example/notes.pdf"
    assert item.offline_allowed is True
    assert item.title == "Notes"
