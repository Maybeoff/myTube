import os
import shutil
import ffmpeg
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from databaser import Databaser

app = FastAPI()
db = Databaser()

# Создаем необходимые папки
Path("static/videos").mkdir(parents=True, exist_ok=True)
Path("static/previews").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def convert_to_webm(input_path: str, output_path: str):
    """Конвертация видео в webm через ffmpeg"""
    try:
        (
            ffmpeg
            .input(input_path)
            .output(output_path, vcodec='libvpx-vp9', acodec='libopus', crf=30, b_v='1M')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return True
    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e.stderr.decode()}")
        return False


def generate_thumbnail(video_path: str, thumbnail_path: str):
    """Генерация превью из видео"""
    try:
        (
            ffmpeg
            .input(video_path, ss=1)
            .filter('scale', 320, -1)
            .output(thumbnail_path, vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return True
    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e.stderr.decode()}")
        return False


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    videos = db.get_videos()
    return templates.TemplateResponse("index.html", {"request": request, "videos": videos})


@app.get("/{video_id}", response_class=HTMLResponse)
async def video_page(request: Request, video_id: int):
    video = db.get_video(video_id)
    if video is None:
        return HTMLResponse(content="Видео не найдено", status_code=404)
    return templates.TemplateResponse("video_page.html", {"request": request, "video": video})


@app.post("/{video_id}/like")
async def like_video(video_id: int):
    db.like_video(video_id)
    return JSONResponse(content={"status": "ok"})


@app.post("/{video_id}/dislike")
async def dislike_video(video_id: int):
    db.dislike_video(video_id)
    return JSONResponse(content={"status": "ok"})


@app.post("/upload")
async def upload_video(
    video: UploadFile = File(...),
    name: str = Form(...),
    desc: str = Form(...),
    author_name: str = Form(...)
):
    """Загрузка и конвертация видео"""
    try:
        # Добавляем запись в БД
        video_id = db.add_video(name, desc, author_name)
        
        # Сохраняем временный файл
        temp_path = f"static/videos/temp_{video_id}{Path(video.filename).suffix}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        
        # Конвертируем в webm
        output_path = f"static/videos/{video_id}.webm"
        if not convert_to_webm(temp_path, output_path):
            os.remove(temp_path)
            return JSONResponse(content={"error": "Ошибка конвертации видео"}, status_code=500)
        
        # Генерируем превью
        thumbnail_path = f"static/previews/{video_id}.png"
        generate_thumbnail(output_path, thumbnail_path)
        
        # Удаляем временный файл
        os.remove(temp_path)
        
        return JSONResponse(content={"status": "ok", "video_id": video_id})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)