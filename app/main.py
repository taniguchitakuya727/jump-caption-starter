from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.services.ffmpeg import detect_ffmpeg
from app.services.video_processing import (
    JumpCutSettings,
    VideoProcessingError,
    run_jump_cut,
)


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = PROJECT_DIR / "uploads"
OUTPUT_DIR = PROJECT_DIR / "outputs"

app = FastAPI(
    title="Jump Caption",
    summary="Local web app starter for jump cuts and subtitles.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/ffmpeg")
def ffmpeg_status() -> dict[str, object]:
    return detect_ffmpeg().to_dict()


@app.post("/api/jump-cut")
def jump_cut(
    file: UploadFile = File(...),
    silence_threshold_db: float = Form(-35.0),
    min_silence_duration: float = Form(0.5),
    retained_margin: float = Form(0.15),
) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="ファイル名がありません。")

    request_upload_dir = UPLOAD_DIR / uuid.uuid4().hex
    request_upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    upload_path = request_upload_dir / safe_name

    try:
        with upload_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)

        result = run_jump_cut(
            input_path=upload_path,
            output_dir=OUTPUT_DIR,
            settings=JumpCutSettings(
                silence_threshold_db=silence_threshold_db,
                min_silence_duration=min_silence_duration,
                retained_margin=retained_margin,
            ),
        )
    except VideoProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        file.file.close()

    return {
        "output_file": result.output_path.name,
        "output_url": f"/outputs/{result.output_path.name}",
        "silence_json_file": result.silence_json_path.name,
        "silence_json_url": f"/outputs/{result.silence_json_path.name}",
        "duration": result.duration,
        "silences": [silence.to_dict() for silence in result.silences],
        "logs": result.logs,
    }


@app.get("/outputs/{filename}", include_in_schema=False)
def output_file(filename: str) -> FileResponse:
    path = (OUTPUT_DIR / filename).resolve()
    if path.parent != OUTPUT_DIR.resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="Output file not found.")
    return FileResponse(path)
