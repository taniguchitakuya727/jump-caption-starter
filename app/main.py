from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.services.ffmpeg import detect_ffmpeg
from app.services.subtitles import (
    SubtitleEditError,
    SubtitleFormatSettings,
    SubtitleGenerationError,
    SubtitleSettings,
    faster_whisper_available,
    format_subtitle_metadata,
    generate_subtitles,
    load_subtitle_metadata,
    save_subtitle_edit,
)
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


@app.get("/api/whisper")
def whisper_status() -> dict[str, object]:
    return {
        "available": faster_whisper_available(),
        "default_model": "small",
        "default_language": "ja",
        "device": "cpu",
        "compute_type": "int8",
        "note": "初回の字幕生成時にWhisperモデルのダウンロードが必要になる場合があります。",
    }


@app.get("/api/outputs")
def list_outputs() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    videos = []
    subtitle_projects = []

    for path in sorted(OUTPUT_DIR.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_file():
            continue

        if path.suffix.lower() == ".mp4":
            videos.append(
                {
                    "file": path.name,
                    "url": f"/outputs/{path.name}",
                    "modified": path.stat().st_mtime,
                }
            )
        elif path.name.endswith("_subtitles.json"):
            try:
                metadata = load_subtitle_metadata(path)
            except SubtitleEditError:
                continue

            source = str(metadata.get("source", ""))
            subtitle_projects.append(
                {
                    "file": path.name,
                    "url": f"/outputs/{path.name}",
                    "source": source,
                    "video_url": f"/outputs/{source}" if source else None,
                    "segments": len(metadata.get("segments", [])),
                    "modified": path.stat().st_mtime,
                }
            )

    return {"videos": videos, "subtitle_projects": subtitle_projects}


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


@app.post("/api/subtitles")
def subtitles(
    filename: str = Form(...),
    model_size: str = Form("small"),
    language: str = Form("ja"),
) -> dict[str, object]:
    media_path = safe_output_path(filename)
    if not media_path.is_file():
        raise HTTPException(status_code=404, detail="動画ファイルが見つかりません。")

    try:
        result = generate_subtitles(
            media_path=media_path,
            output_dir=OUTPUT_DIR,
            settings=SubtitleSettings(
                model_size=model_size,
                language=None if language in {"", "auto"} else language,
                device="cpu",
                compute_type="int8",
            ),
        )
    except SubtitleGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "srt_file": result.srt_path.name,
        "srt_url": f"/outputs/{result.srt_path.name}",
        "txt_file": result.txt_path.name,
        "txt_url": f"/outputs/{result.txt_path.name}",
        "metadata_file": result.metadata_path.name,
        "metadata_url": f"/outputs/{result.metadata_path.name}",
        "segments": [segment.to_dict() for segment in result.segments],
        "logs": result.logs,
    }


@app.get("/api/subtitles/{filename}")
def get_subtitle_metadata(filename: str) -> dict[str, object]:
    metadata_path = safe_output_path(filename)
    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="字幕メタデータが見つかりません。")

    try:
        metadata = load_subtitle_metadata(metadata_path)
    except SubtitleEditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    source = str(metadata.get("source", ""))
    return {
        **metadata,
        "video_url": f"/outputs/{source}" if source else None,
        "metadata_file": metadata_path.name,
    }


@app.post("/api/subtitles/{filename}/save")
def save_subtitles(filename: str, payload: dict[str, object]) -> dict[str, object]:
    metadata_path = safe_output_path(filename)
    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="字幕メタデータが見つかりません。")

    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        raise HTTPException(status_code=400, detail="字幕セグメントがありません。")

    try:
        result = save_subtitle_edit(
            metadata_path=metadata_path,
            output_dir=OUTPUT_DIR,
            payload_segments=raw_segments,
        )
    except SubtitleEditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "srt_file": result.srt_path.name,
        "srt_url": f"/outputs/{result.srt_path.name}",
        "txt_file": result.txt_path.name,
        "txt_url": f"/outputs/{result.txt_path.name}",
        "metadata_file": result.metadata_path.name,
        "metadata_url": f"/outputs/{result.metadata_path.name}",
        "segments": [segment.to_dict() for segment in result.segments],
        "logs": result.logs,
    }


@app.post("/api/subtitles/{filename}/format")
def format_subtitles(filename: str, payload: dict[str, object]) -> dict[str, object]:
    metadata_path = safe_output_path(filename)
    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="字幕メタデータが見つかりません。")

    try:
        result = format_subtitle_metadata(
            metadata_path=metadata_path,
            output_dir=OUTPUT_DIR,
            settings=SubtitleFormatSettings(
                max_chars_per_line=int(payload.get("max_chars_per_line", 18)),
                max_lines=int(payload.get("max_lines", 2)),
                min_duration=float(payload.get("min_duration", 0.8)),
                max_duration=float(payload.get("max_duration", 7.0)),
            ),
        )
    except (SubtitleEditError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "srt_file": result.srt_path.name,
        "srt_url": f"/outputs/{result.srt_path.name}",
        "txt_file": result.txt_path.name,
        "txt_url": f"/outputs/{result.txt_path.name}",
        "metadata_file": result.metadata_path.name,
        "metadata_url": f"/outputs/{result.metadata_path.name}",
        "segments": [segment.to_dict() for segment in result.segments],
        "logs": result.logs,
    }


@app.get("/outputs/{filename}", include_in_schema=False)
def output_file(filename: str) -> FileResponse:
    path = safe_output_path(filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Output file not found.")
    return FileResponse(path)


def safe_output_path(filename: str) -> Path:
    path = (OUTPUT_DIR / Path(filename).name).resolve()
    if path.parent != OUTPUT_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid output filename.")
    return path
