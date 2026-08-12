"""Storage abstraction for course assets.

Use local files in development.  When `S3_BUCKET` is configured, objects are
uploaded to S3-compatible cloud storage and a public object URL is returned.
"""
import uuid
from pathlib import Path
from fastapi import UploadFile
from app.core.config import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def upload(self, file: UploadFile, prefix: str = "course") -> str:
        name = f"{prefix}/{uuid.uuid4()}-{Path(file.filename or 'upload').name}"
        contents = await file.read()
        if self.settings.s3_bucket:
            try:
                import boto3
                client = boto3.client("s3", region_name=self.settings.aws_region)
                client.put_object(Bucket=self.settings.s3_bucket, Key=name, Body=contents, ContentType=file.content_type or "application/octet-stream")
                return f"https://{self.settings.s3_bucket}.s3.{self.settings.aws_region}.amazonaws.com/{name}"
            except ImportError as exc:
                raise RuntimeError("boto3 is required when S3_BUCKET is configured") from exc
        path = Path("uploads") / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
        return f"/uploads/{name}"
