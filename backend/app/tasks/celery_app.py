from celery import Celery
import subprocess
from pathlib import Path
from app.core.config import get_settings

celery_app = Celery("exam_platform", broker=get_settings().redis_url, backend=get_settings().redis_url)
celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"], timezone="Asia/Kolkata")

@celery_app.task
def refresh_leaderboards() -> None:
    """Schedule this task after attempt submission; aggregation is intentionally idempotent."""


@celery_app.task(bind=True, autoretry_for=(OSError, subprocess.CalledProcessError), retry_backoff=True, max_retries=3)
def transcode_video_to_hls(self, source_path: str, output_directory: str) -> str:
    """Convert a locally staged MP4 into adaptive HLS segments.

    Cloud uploads should be staged by the worker before this task runs; the
    task deliberately never runs FFmpeg in the API request process.
    """
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    playlist = output / "index.m3u8"
    subprocess.run([
        get_settings().ffmpeg_binary, "-y", "-i", source_path,
        "-codec:v", "h264", "-codec:a", "aac", "-preset", "veryfast",
        "-hls_time", "6", "-hls_playlist_type", "vod",
        "-hls_segment_filename", str(output / "segment_%03d.ts"), str(playlist),
    ], check=True, capture_output=True)
    return str(playlist)
