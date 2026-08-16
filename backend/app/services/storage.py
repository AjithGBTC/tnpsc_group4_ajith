"""Storage abstraction for course assets.

Use local files in development.  When `S3_BUCKET` is configured, objects are
uploaded to S3-compatible cloud storage and a public object URL is returned.
"""
import asyncio
import shutil
import uuid
from pathlib import Path
from fastapi import UploadFile
from app.core.config import get_settings


def _copy_to_path(source, destination: Path) -> None:
    with destination.open("wb") as target:
        shutil.copyfileobj(source, target)


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def upload(self, file: UploadFile, prefix: str = "course") -> str:
        name = f"{prefix}/{uuid.uuid4()}-{Path(file.filename or 'upload').name}"
        if self.settings.s3_bucket:
            try:
                import boto3
                client = boto3.client("s3", region_name=self.settings.aws_region)
                await file.seek(0)
                await asyncio.to_thread(
                    client.upload_fileobj,
                    file.file,
                    self.settings.s3_bucket,
                    name,
                    ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
                )
                base_url = self.settings.s3_public_base_url.rstrip("/")
                return f"{base_url}/{name}" if base_url else f"https://{self.settings.s3_bucket}.s3.{self.settings.aws_region}.amazonaws.com/{name}"
            except ImportError as exc:
                raise RuntimeError("boto3 is required when S3_BUCKET is configured") from exc
        path = Path("uploads") / name
        path.parent.mkdir(parents=True, exist_ok=True)
        await file.seek(0)
        # UploadFile is spooled to disk by Starlette for larger requests.  Copy
        # the stream directly so a video is never materialised in application RAM.
        await asyncio.to_thread(_copy_to_path, file.file, path)
        return f"/uploads/{name}"
